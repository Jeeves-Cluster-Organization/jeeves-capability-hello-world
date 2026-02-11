"""ChatbotService - Kernel-driven pipeline execution for general chatbot.

Provides a clean interface for running the 3-agent chatbot pipeline
(Understand -> Think -> Respond) with SQLite-backed in-dialogue memory.

Memory is fail-forward: if SQLite is unavailable, the pipeline runs
without persistence (conversation context from Gradio frontend only).
"""

from typing import Any, Dict, List, Optional, AsyncIterator, TYPE_CHECKING
from uuid import uuid4
from datetime import datetime, timezone
from dataclasses import dataclass
import asyncio

from jeeves_infra.protocols import (
    PipelineRunner,
    create_pipeline_runner,
    create_envelope,
    Envelope,
    TerminalReason,
    LoggerProtocol,
    ToolExecutorProtocol,
    PipelineConfig,
)
from jeeves_infra.protocols import RequestContext
from jeeves_infra.pipeline_worker import PipelineWorker, WorkerResult

if TYPE_CHECKING:
    from jeeves_infra.kernel_client import KernelClient


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
    Service wrapper for PipelineRunner executing general chatbot pipeline.

    Features:
    - 3-agent pipeline (Understand -> Think -> Respond)
    - SQLite-backed session state and message persistence
    - Streaming support (token-level)
    - Fail-forward memory: pipeline works without DB
    """

    def __init__(
        self,
        *,
        llm_provider_factory,
        tool_executor: ToolExecutorProtocol,
        logger: LoggerProtocol,
        pipeline_config: PipelineConfig,
        kernel_client: Optional["KernelClient"] = None,
        use_mock: bool = False,
        db=None,
    ):
        from jeeves_capability_hello_world.prompts.registry import PromptRegistry
        prompt_registry = PromptRegistry.get_instance()

        self._runtime = create_pipeline_runner(
            config=pipeline_config,
            llm_provider_factory=llm_provider_factory,
            tool_executor=tool_executor,
            logger=logger,
            persistence=None,
            prompt_registry=prompt_registry,
            use_mock=use_mock,
        )
        self._logger = logger
        self._kernel_client = kernel_client
        self._pipeline_config = pipeline_config

        # Memory (lazy init, fail-forward)
        self._db = db
        self._session_state = None
        self._memory_ready = False

        if kernel_client:
            self._worker = PipelineWorker(
                kernel_client=kernel_client,
                agents=self._runtime.agents,
                logger=logger,
                persistence=None,
            )
        else:
            self._worker = None

    async def _ensure_memory(self):
        """Lazily initialize SQLite memory. Fail-forward: errors are logged, not raised."""
        if self._memory_ready:
            return
        self._memory_ready = True
        if self._db is None:
            return
        try:
            from jeeves_capability_hello_world.database.schema import SESSION_STATE_DDL, MESSAGES_DDL
            from jeeves_capability_hello_world.memory.services.session_state_service import SessionStateService

            await self._db.connect()
            # executescript doesn't work with multiple statements via execute(),
            # so split and run each statement
            for ddl in [SESSION_STATE_DDL, MESSAGES_DDL]:
                for stmt in ddl.strip().split(";"):
                    stmt = stmt.strip()
                    if stmt:
                        await self._db.execute(stmt)
            self._session_state = SessionStateService(db=self._db)
            self._logger.info("memory_initialized", backend="sqlite")
        except Exception as e:
            self._logger.warning("memory_init_failed", error=str(e))
            self._db = None

    async def _load_session_context(self, session_id: str, user_id: str, message: str) -> Dict[str, Any]:
        """Load session context from memory. Returns empty dict on failure."""
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
        """Persist user and assistant messages. Fail-forward."""
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
        except Exception:
            pass  # fail forward

    async def _run_with_resource_tracking(
        self,
        envelope: Envelope,
        thread_id: str,
    ) -> Envelope:
        """Run pipeline with kernel-driven orchestration."""
        pid = envelope.envelope_id

        if self._worker and self._kernel_client:
            pipeline_config_dict = {
                "name": self._pipeline_config.name,
                "max_iterations": self._pipeline_config.max_iterations,
                "max_llm_calls": self._pipeline_config.max_llm_calls,
                "max_agent_hops": self._pipeline_config.max_agent_hops,
                "agents": [
                    {
                        "name": agent.name,
                        "stage_order": agent.stage_order,
                        "default_next": agent.default_next,
                        "error_next": agent.error_next,
                        "output_key": agent.output_key,
                        "routing_rules": [
                            {
                                "condition": rule.condition,
                                "value": rule.value,
                                "target": rule.target,
                            }
                            for rule in agent.routing_rules
                        ] if agent.routing_rules else [],
                    }
                    for agent in self._pipeline_config.agents
                ],
                "edge_limits": dict(self._pipeline_config.edge_limits) if self._pipeline_config.edge_limits else {},
            }

            result = await self._worker.execute(
                process_id=pid,
                pipeline_config=pipeline_config_dict,
                envelope=envelope,
                thread_id=thread_id,
            )

            result_envelope = result.envelope

            if result.terminated:
                reason_map = {
                    "TERMINAL_REASON_COMPLETED": TerminalReason.COMPLETED,
                    "TERMINAL_REASON_MAX_ITERATIONS_EXCEEDED": TerminalReason.MAX_ITERATIONS_EXCEEDED,
                    "TERMINAL_REASON_MAX_LLM_CALLS_EXCEEDED": TerminalReason.MAX_LLM_CALLS_EXCEEDED,
                    "TERMINAL_REASON_MAX_AGENT_HOPS_EXCEEDED": TerminalReason.MAX_AGENT_HOPS_EXCEEDED,
                    "TERMINAL_REASON_MAX_LOOP_EXCEEDED": TerminalReason.MAX_LOOP_EXCEEDED,
                    "TERMINAL_REASON_TOOL_FAILED_FATALLY": TerminalReason.TOOL_FAILED_FATALLY,
                }
                result_envelope.terminal_reason = reason_map.get(
                    result.terminal_reason,
                    TerminalReason.COMPLETED if result.terminal_reason == "" else TerminalReason.TOOL_FAILED_FATALLY
                )
                result_envelope.terminated = True
                result_envelope.termination_reason = result.terminal_reason

            return result_envelope

        # Fallback: No kernel client
        self._logger.error("no_kernel_client", envelope_id=pid)
        envelope.terminated = True
        envelope.termination_reason = "KernelClient required for orchestration"
        envelope.terminal_reason = TerminalReason.TOOL_FAILED_FATALLY
        return envelope

    async def process_message(
        self,
        *,
        user_id: str,
        session_id: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatbotResult:
        """Process a user message through the 3-agent chatbot pipeline."""
        request_id = f"req_{uuid4().hex[:16]}"
        request_context = RequestContext(
            request_id=request_id,
            capability="general_chatbot",
            session_id=session_id,
            user_id=user_id,
        )

        await self._ensure_memory()
        session_context = await self._load_session_context(session_id, user_id, message)

        meta = metadata or {}
        meta["session_context"] = session_context

        envelope = create_envelope(
            raw_input=message,
            request_context=request_context,
            metadata=meta,
        )

        try:
            result_envelope = await self._run_with_resource_tracking(
                envelope, thread_id=session_id
            )

            result = self._envelope_to_result(result_envelope, request_id)

            # Persist messages
            await self._persist_messages(session_id, message, result.response or "")

            return result

        except Exception as e:
            self._logger.error("chatbot_processing_error", request_id=request_id, error=str(e))
            return ChatbotResult(status="error", error=f"Processing failed: {str(e)}", request_id=request_id)

    async def process_message_stream(
        self,
        *,
        user_id: str,
        session_id: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator:
        """Process message with token-level streaming from Respond agent.

        Pipeline flow:
        1. Understand agent: Buffered (JSON output needed)
        2. Think agent: Buffered (tool execution)
        3. Respond agent: TRUE STREAMING (yields tokens as generated)
        """
        from jeeves_infra.protocols import PipelineEvent

        request_id = f"req_{uuid4().hex[:16]}"
        request_context = RequestContext(
            request_id=request_id,
            capability="general_chatbot",
            session_id=session_id,
            user_id=user_id,
        )

        # Initialize memory and load session context
        await self._ensure_memory()
        session_context = await self._load_session_context(session_id, user_id, message)

        meta = metadata or {}
        meta["session_context"] = session_context

        envelope = create_envelope(
            raw_input=message,
            request_context=request_context,
            metadata=meta,
        )

        pid = envelope.envelope_id

        self._logger.info(
            "chatbot_streaming_started",
            request_id=request_id,
            user_id=user_id,
            session_id=session_id,
        )

        # Register process with kernel before tracking usage
        if self._kernel_client:
            await self._kernel_client.create_process(
                pid=pid,
                request_id=request_id,
                user_id=user_id,
                session_id=session_id,
            )
            await self._kernel_client.record_usage(pid=pid, agent_hops=1)
            quota_result = await self._kernel_client.check_quota(pid)
            if not quota_result.within_bounds:
                yield PipelineEvent(
                    "error", "__end__",
                    {"error": f"Quota exceeded: {quota_result.exceeded_reason}", "request_id": request_id}
                )
                return

        try:
            # Stage 1: Understand (buffered)
            yield PipelineEvent("stage", "understand", {"status": "started"})
            understand_agent = self._runtime.agents.get("understand")
            if understand_agent:
                envelope = await understand_agent.process(envelope)
                yield PipelineEvent("stage", "understand", {"status": "completed"})

            # Stage 2: Think (buffered)
            yield PipelineEvent("stage", "think", {"status": "started"})
            think_agent = self._runtime.agents.get("think")
            if think_agent:
                envelope = await think_agent.process(envelope)
                yield PipelineEvent("stage", "think", {"status": "completed"})

            # Stage 3: Respond (STREAMING)
            yield PipelineEvent("stage", "respond", {"status": "started"})
            respond_agent = self._runtime.agents.get("respond")
            if respond_agent:
                from jeeves_infra.protocols import TokenStreamMode

                if respond_agent.config.token_stream == TokenStreamMode.AUTHORITATIVE:
                    async for event_type, event in respond_agent.stream(envelope):
                        yield event
                else:
                    envelope = await respond_agent.process(envelope)
                    response = envelope.outputs.get("final_response", {}).get("response", "")
                    chunk_size = 10
                    for i in range(0, len(response), chunk_size):
                        yield PipelineEvent(
                            "token", "respond",
                            {"token": response[i:i+chunk_size]},
                            debug=False
                        )

                yield PipelineEvent("stage", "respond", {"status": "completed"})

            # Record resource usage
            if self._kernel_client:
                runtime_hops = envelope.metadata.get("agent_hops", 0)
                runtime_llm_calls = envelope.metadata.get("llm_call_count", 0)
                runtime_tool_calls = envelope.metadata.get("tool_call_count", 0)
                tokens_in = envelope.metadata.get("total_tokens_in", 0)
                tokens_out = envelope.metadata.get("total_tokens_out", 0)
                await self._kernel_client.record_usage(
                    pid=pid,
                    agent_hops=max(0, runtime_hops - 1),
                    llm_calls=runtime_llm_calls,
                    tool_calls=runtime_tool_calls,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                )

            # Persist messages (fail-forward)
            response_text = envelope.outputs.get("final_response", {}).get("response", "")
            await self._persist_messages(session_id, message, response_text)

            # Terminal event: done
            yield PipelineEvent(
                "done", "__end__",
                {"final_output": envelope.outputs.get("final_response", {}), "request_id": request_id}
            )

        except asyncio.CancelledError:
            self._logger.info("chatbot_streaming_cancelled", request_id=request_id)
            raise
        except Exception as e:
            self._logger.error("chatbot_streaming_error", request_id=request_id, error=str(e), exc_info=True)
            yield PipelineEvent("error", "__end__", {"error": str(e), "request_id": request_id})

    def _envelope_to_result(self, envelope: Envelope, request_id: str) -> ChatbotResult:
        """Convert Envelope to ChatbotResult."""
        final_response_output = envelope.outputs.get("final_response", {})

        if envelope.terminal_reason == TerminalReason.COMPLETED:
            response = final_response_output.get("response")
            citations = final_response_output.get("citations", [])
            confidence = final_response_output.get("confidence", "medium")

            if not response:
                return ChatbotResult(
                    status="error",
                    error="Pipeline completed but no response generated",
                    request_id=request_id,
                )

            return ChatbotResult(
                status="success",
                response=response,
                citations=citations if citations else None,
                confidence=confidence,
                request_id=request_id,
            )

        error_msg = envelope.termination_reason or "Pipeline failed"
        return ChatbotResult(status="error", error=error_msg, request_id=request_id)

    async def handle_dispatch(self, envelope: Envelope) -> Envelope:
        """Control Tower dispatch handler."""
        await self._ensure_memory()
        return await self._run_with_resource_tracking(envelope, thread_id=envelope.session_id)

    def get_dispatch_handler(self):
        """Get dispatch handler for Control Tower registration."""
        return self.handle_dispatch


__all__ = ["ChatbotService", "ChatbotResult"]
