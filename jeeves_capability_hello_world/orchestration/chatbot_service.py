"""ChatbotService - Kernel-driven pipeline execution for general chatbot.

Both process_message() and process_message_stream() use PipelineWorker,
which delegates all orchestration decisions to the Rust kernel:
routing rules, bounds enforcement, error_next, interrupts.

Memory is fail-forward: if SQLite is unavailable, the pipeline runs
without persistence (conversation context from Gradio frontend only).
"""

from typing import Any, Dict, List, Optional, AsyncIterator, TYPE_CHECKING
from uuid import uuid4
from datetime import datetime, timezone
from dataclasses import dataclass
import asyncio

from jeeves_core.protocols import (
    PipelineRunner,
    create_pipeline_runner,
    create_envelope,
    Envelope,
    LoggerProtocol,
    ToolExecutorProtocol,
    PipelineConfig,
    PipelineEvent,
    RequestContext,
)
from jeeves_core.pipeline_worker import PipelineWorker, WorkerResult

if TYPE_CHECKING:
    from jeeves_core.kernel_client import KernelClient


@dataclass
class ChatbotResult:
    """Result from chatbot processing."""
    status: str  # "success" or "error"
    response: Optional[str] = None
    citations: Optional[List[str]] = None
    confidence: Optional[str] = None
    error: Optional[str] = None
    request_id: Optional[str] = None


class ChatbotService:
    """
    Service wrapper for kernel-driven pipeline execution.

    Features:
    - 4-agent pipeline with conditional routing (kernel-driven)
    - SQLite-backed session state and message persistence
    - Streaming support via PipelineWorker.execute_streaming()
    - Fail-forward memory: pipeline works without DB
    """

    def __init__(
        self,
        *,
        llm_provider_factory,
        tool_executor: ToolExecutorProtocol,
        logger: LoggerProtocol,
        pipeline_config: PipelineConfig,
        kernel_client: "KernelClient",
        use_mock: bool = False,
        db=None,
        persistence=None,
        enable_persistence: bool = True,
    ):
        from jeeves_capability_hello_world.prompts.registry import PromptRegistry
        prompt_registry = PromptRegistry.get_instance()

        if persistence is not None:
            self._persistence = persistence
        elif enable_persistence and db is not None:
            import json
            from jeeves_core.runtime.persistence import DatabasePersistence
            self._persistence = DatabasePersistence(db, encode=json.dumps, decode=json.loads)
        else:
            self._persistence = None

        self._runtime = create_pipeline_runner(
            config=pipeline_config,
            llm_provider_factory=llm_provider_factory,
            tool_executor=tool_executor,
            logger=logger,
            persistence=self._persistence,
            prompt_registry=prompt_registry,
            use_mock=use_mock,
        )
        self._logger = logger
        self._kernel_client = kernel_client
        self._pipeline_config = pipeline_config

        self._db = db
        self._session_state = None
        self._memory_ready = False

        self._worker = PipelineWorker(
            kernel_client=kernel_client,
            agents=self._runtime.agents,
            logger=logger,
            persistence=self._persistence,
        )

    # =========================================================================
    # Memory (fail-forward)
    # =========================================================================

    async def _ensure_memory(self):
        if self._memory_ready:
            return
        self._memory_ready = True
        if self._db is None:
            return
        try:
            from jeeves_capability_hello_world.database.schema import SESSION_STATE_DDL, MESSAGES_DDL
            from jeeves_capability_hello_world.memory.services.session_state_service import SessionStateService

            await self._db.connect()
            for ddl in [SESSION_STATE_DDL, MESSAGES_DDL]:
                for stmt in ddl.strip().split(";"):
                    stmt = stmt.strip()
                    if stmt:
                        await self._db.execute(stmt)
            self._session_state = SessionStateService(db=self._db)
            self._logger.info("memory_initialized", backend="sqlite")
        except Exception as e:
            self._logger.error("memory_init_failed", error=str(e))
            self._db = None

    async def _load_session_context(self, session_id: str, user_id: str, message: str) -> Dict[str, Any]:
        if not self._session_state:
            return {}
        try:
            await self._session_state.get_or_create(session_id, user_id)
            await self._session_state.on_user_turn(session_id, message)
            return await self._session_state.get_context_for_prompt(session_id)
        except Exception as e:
            self._logger.warning("session_state_load_failed", error=str(e))
            return {}

    async def _persist_messages(self, session_id: str, user_message: str, assistant_response: str):
        if not self._db:
            return
        try:
            now = datetime.now(timezone.utc).isoformat()
            await self._db.insert("messages", {
                "message_id": f"msg_{uuid4().hex[:12]}",
                "session_id": session_id,
                "role": "user",
                "content": user_message,
                "created_at": now,
            })
            if assistant_response:
                await self._db.insert("messages", {
                    "message_id": f"msg_{uuid4().hex[:12]}",
                    "session_id": session_id,
                    "role": "assistant",
                    "content": assistant_response,
                    "created_at": now,
                })
        except Exception as e:
            self._logger.error("message_persist_failed", session_id=session_id, error=str(e))

    # =========================================================================
    # Envelope Building
    # =========================================================================

    def _build_envelope(
        self,
        message: str,
        user_id: str,
        session_id: str,
        session_context: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Envelope:
        request_id = f"req_{uuid4().hex[:16]}"
        request_context = RequestContext(
            request_id=request_id,
            capability="general_chatbot",
            session_id=session_id,
            user_id=user_id,
        )
        meta = metadata or {}
        meta["session_context"] = session_context
        return create_envelope(
            raw_input=message,
            request_context=request_context,
            metadata=meta,
        )

    # =========================================================================
    # Kernel-Driven Execution (non-streaming)
    # =========================================================================

    async def _run_pipeline(self, envelope: Envelope, thread_id: str) -> WorkerResult:
        """Execute pipeline under kernel control."""
        pipeline_config_dict = self._pipeline_config.to_kernel_dict()
        return await self._worker.execute(
            process_id=envelope.envelope_id,
            pipeline_config=pipeline_config_dict,
            envelope=envelope,
            thread_id=thread_id,
        )

    async def process_message(
        self,
        *,
        user_id: str,
        session_id: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatbotResult:
        """Process a user message through the kernel-driven pipeline."""
        await self._ensure_memory()
        session_context = await self._load_session_context(session_id, user_id, message)

        envelope = self._build_envelope(message, user_id, session_id, session_context, metadata)
        request_id = envelope.request_id

        try:
            result = await self._run_pipeline(envelope, thread_id=session_id)

            chatbot_result = self._build_result(result, request_id)
            await self._persist_messages(session_id, message, chatbot_result.response or "")
            return chatbot_result

        except Exception as e:
            self._logger.error("chatbot_processing_error", request_id=request_id, error=str(e))
            return ChatbotResult(status="error", error=f"Processing failed: {str(e)}", request_id=request_id)

    # =========================================================================
    # Kernel-Driven Streaming
    # =========================================================================

    async def process_message_stream(
        self,
        *,
        user_id: str,
        session_id: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator:
        """Process message with kernel-driven streaming.

        Uses PipelineWorker.execute_streaming() — the kernel controls
        routing, bounds, and interrupts. Yields PipelineEvents.
        """
        await self._ensure_memory()
        session_context = await self._load_session_context(session_id, user_id, message)

        envelope = self._build_envelope(message, user_id, session_id, session_context, metadata)
        request_id = envelope.request_id
        pipeline_config_dict = self._pipeline_config.to_kernel_dict()

        self._logger.info(
            "chatbot_streaming_started",
            request_id=request_id,
            session_id=session_id,
        )

        try:
            async for agent_name, output in self._worker.execute_streaming(
                process_id=envelope.envelope_id,
                pipeline_config=pipeline_config_dict,
                envelope=envelope,
                thread_id=session_id,
                force=True,
            ):
                if agent_name == "__end__":
                    yield PipelineEvent("done", "__end__", {
                        "final_output": envelope.outputs.get("final_response", {}),
                        "request_id": request_id,
                        **output,
                    })
                elif agent_name == "__interrupt__":
                    yield PipelineEvent("interrupt", "__interrupt__", output)
                elif agent_name == "__error__":
                    yield PipelineEvent("error", "__error__", output)
                elif agent_name == "__token__":
                    yield PipelineEvent(
                        "token",
                        output.get("agent", "respond"),
                        output.get("event", {}).data if hasattr(output.get("event", {}), "data") else output,
                        debug=False,
                    )
                else:
                    yield PipelineEvent("stage", agent_name, {"status": "completed", **(output or {})})

            # Persist messages
            response_text = envelope.outputs.get("final_response", {}).get("response", "")
            await self._persist_messages(session_id, message, response_text)

        except asyncio.CancelledError:
            self._logger.info("chatbot_streaming_cancelled", request_id=request_id)
            raise
        except Exception as e:
            self._logger.error("chatbot_streaming_error", request_id=request_id, error=str(e))
            yield PipelineEvent("error", "__end__", {"error": str(e), "request_id": request_id})

    # =========================================================================
    # Result Mapping
    # =========================================================================

    def _build_result(self, worker_result: WorkerResult, request_id: str) -> ChatbotResult:
        """Convert WorkerResult to ChatbotResult.

        Reads termination status from WorkerResult (kernel is sole authority).
        """
        final = worker_result.envelope.outputs.get("final_response", {})
        reason = worker_result.terminal_reason

        # Completed or not terminated — look for response
        if not worker_result.terminated or reason in ("", "COMPLETED"):
            response = final.get("response")
            if not response:
                return ChatbotResult(
                    status="error",
                    error="Pipeline completed but no response generated",
                    request_id=request_id,
                )
            return ChatbotResult(
                status="success",
                response=response,
                citations=final.get("citations") or None,
                confidence=final.get("confidence", "medium"),
                request_id=request_id,
            )

        # Bounds exits — return partial response if available
        bounds_reasons = {
            "MAX_ITERATIONS_EXCEEDED",
            "MAX_LLM_CALLS_EXCEEDED",
            "MAX_AGENT_HOPS_EXCEEDED",
            "MAX_STAGE_VISITS_EXCEEDED",
        }
        if reason in bounds_reasons:
            partial = final.get("response")
            if partial:
                return ChatbotResult(
                    status="success",
                    response=partial,
                    confidence="low",
                    request_id=request_id,
                )
            return ChatbotResult(
                status="error",
                error=f"Pipeline stopped: {reason}",
                request_id=request_id,
            )

        if reason == "TOOL_FAILED_FATALLY":
            return ChatbotResult(status="error", error="A tool failed during processing", request_id=request_id)

        return ChatbotResult(status="error", error=reason or "Pipeline failed", request_id=request_id)

    # =========================================================================
    # Control Tower Dispatch
    # =========================================================================

    async def handle_dispatch(self, envelope: Envelope) -> Envelope:
        await self._ensure_memory()
        result = await self._run_pipeline(envelope, thread_id=envelope.session_id)
        return result.envelope

    def get_dispatch_handler(self):
        return self.handle_dispatch


__all__ = ["ChatbotService", "ChatbotResult"]
