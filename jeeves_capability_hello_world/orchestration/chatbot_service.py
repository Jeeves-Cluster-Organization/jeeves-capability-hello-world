"""
ChatbotService - Kernel-driven pipeline execution for general chatbot.

Provides a clean interface for running the 3-agent chatbot pipeline
(Understand → Think → Respond) using kernel-driven orchestration.

The Rust kernel controls:
- Pipeline loop
- Routing decisions
- Bounds checking
- State management

Python workers just execute agents as instructed.
"""

from typing import Any, Dict, List, Optional, AsyncIterator, TYPE_CHECKING
from uuid import uuid4
from dataclasses import dataclass
import asyncio

from mission_system.contracts_core import (
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
    - 3-agent pipeline (Understand → Think → Respond)
    - Real LLM inference (no mocks by default)
    - Streaming support (token-level)
    - KernelClient integration for resource tracking and quota enforcement
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
    ):
        """
        Initialize ChatbotService.

        Args:
            llm_provider_factory: Factory to create LLM providers per role
            tool_executor: Tool executor for agent tool calls
            logger: Logger instance
            pipeline_config: Pipeline configuration (GENERAL_CHATBOT_PIPELINE)
            kernel_client: KernelClient for kernel-driven orchestration
            use_mock: Use mock handlers for testing (default: False - use real LLM)
        """
        # Get the global prompt registry
        from jeeves_capability_hello_world.prompts.registry import PromptRegistry
        prompt_registry = PromptRegistry.get_instance()

        # PipelineRunner still used for agent construction and access
        self._runtime = create_pipeline_runner(
            config=pipeline_config,
            llm_provider_factory=llm_provider_factory,
            tool_executor=tool_executor,
            logger=logger,
            persistence=None,  # No persistence for hello-world
            prompt_registry=prompt_registry,
            use_mock=use_mock,
        )
        self._logger = logger
        self._kernel_client = kernel_client
        self._pipeline_config = pipeline_config

        # Create PipelineWorker for kernel-driven orchestration
        if kernel_client:
            self._worker = PipelineWorker(
                kernel_client=kernel_client,
                agents=self._runtime.agents,
                logger=logger,
                persistence=None,
            )
        else:
            self._worker = None

    async def _run_with_resource_tracking(
        self,
        envelope: Envelope,
        thread_id: str,
    ) -> Envelope:
        """
        Run pipeline with kernel-driven orchestration.

        The kernel controls the pipeline loop, routing, and bounds checking.
        Python just executes agents as instructed.

        Args:
            envelope: Request envelope
            thread_id: Thread/session ID

        Returns:
            Result envelope (may be terminated if quota exceeded)
        """
        pid = envelope.envelope_id

        # Use kernel-driven orchestration if available
        if self._worker and self._kernel_client:
            # Convert pipeline config to dict for kernel
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

            # Execute using PipelineWorker (kernel-driven)
            result = await self._worker.execute(
                process_id=pid,
                pipeline_config=pipeline_config_dict,
                envelope=envelope,
                thread_id=thread_id,
            )

            result_envelope = result.envelope

            # Map terminal reason from kernel to Python enum
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

            self._logger.info(
                "kernel_orchestration_completed",
                envelope_id=pid,
                terminated=result.terminated,
                terminal_reason=result.terminal_reason,
            )

            return result_envelope

        # Fallback: No kernel client - cannot run without orchestration
        self._logger.error(
            "no_kernel_client",
            envelope_id=pid,
            error="KernelClient required for orchestration",
        )
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
        """
        Process a user message through the 3-agent chatbot pipeline.

        Args:
            user_id: User identifier
            session_id: Session identifier for conversation context
            message: User's message text
            metadata: Optional metadata dict (e.g., conversation history)

        Returns:
            ChatbotResult with response or error
        """
        request_id = f"req_{uuid4().hex[:16]}"
        request_context = RequestContext(
            request_id=request_id,
            capability="general_chatbot",
            session_id=session_id,
            user_id=user_id,
        )

        envelope = create_envelope(
            raw_input=message,
            request_context=request_context,
            metadata=metadata or {},
        )

        self._logger.info(
            "chatbot_processing_started",
            request_id=request_id,
            user_id=user_id,
            session_id=session_id,
            message_length=len(message),
        )

        try:
            # Run the 3-agent pipeline with resource tracking
            result_envelope = await self._run_with_resource_tracking(
                envelope, thread_id=session_id
            )

            # Log resource usage
            pid = envelope.envelope_id
            if self._kernel_client:
                process_info = await self._kernel_client.get_process(pid)
                if process_info:
                    self._logger.info(
                        "chatbot_resource_usage",
                        request_id=request_id,
                        llm_calls=process_info.llm_calls,
                        tool_calls=process_info.tool_calls,
                        agent_hops=process_info.agent_hops,
                        tokens_in=process_info.tokens_in,
                        tokens_out=process_info.tokens_out,
                    )

            # Convert envelope to result
            result = self._envelope_to_result(result_envelope, request_id)

            self._logger.info(
                "chatbot_processing_completed",
                request_id=request_id,
                status=result.status,
                has_citations=bool(result.citations),
            )

            return result

        except Exception as e:
            self._logger.error(
                "chatbot_processing_error",
                request_id=request_id,
                error=str(e),
                exc_info=True,
            )
            return ChatbotResult(
                status="error",
                error=f"Processing failed: {str(e)}",
                request_id=request_id,
            )

    async def process_message_stream(
        self,
        *,
        user_id: str,
        session_id: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator:
        """
        Process message with token-level streaming from Respond agent.

        Pipeline flow:
        1. Understand agent: Buffered (JSON output needed)
        2. Think agent: Buffered (tool execution)
        3. Respond agent: TRUE STREAMING (yields tokens as generated)

        Yields:
            PipelineEvent objects (type: token, stage, error, done)

        Terminal semantics:
        - Exactly one terminal event (done OR error)
        - No further events after terminal
        - Cancellation propagates (no synthetic error by default)
        """
        from jeeves_infra.protocols import PipelineEvent

        request_id = f"req_{uuid4().hex[:16]}"
        request_context = RequestContext(
            request_id=request_id,
            capability="general_chatbot",
            session_id=session_id,
            user_id=user_id,
        )

        envelope = create_envelope(
            raw_input=message,
            request_context=request_context,
            metadata=metadata or {},
        )

        pid = envelope.envelope_id

        self._logger.info(
            "chatbot_streaming_started",
            request_id=request_id,
            user_id=user_id,
            session_id=session_id,
        )

        # Track initial agent hop (entering pipeline) via kernel_client
        if self._kernel_client:
            await self._kernel_client.record_usage(pid=pid, agent_hops=1)
            quota_result = await self._kernel_client.check_quota(pid)
            if not quota_result.within_bounds:
                self._logger.warning(
                    "quota_exceeded_before_stream",
                    envelope_id=pid,
                    reason=quota_result.exceeded_reason,
                )
                yield PipelineEvent(
                    "error",
                    "__end__",
                    {"error": f"Quota exceeded: {quota_result.exceeded_reason}", "request_id": request_id}
                )
                return

        try:
            # Stage 1: Understand (buffered - internal JSON needed)
            yield PipelineEvent("stage", "understand", {"status": "started"})
            understand_agent = self._runtime.agents.get("understand")
            if understand_agent:
                envelope = await understand_agent.process(envelope)
                yield PipelineEvent("stage", "understand", {"status": "completed"})

            # Stage 2: Think (buffered - tool execution)
            yield PipelineEvent("stage", "think", {"status": "started"})
            think_agent = self._runtime.agents.get("think")
            if think_agent:
                envelope = await think_agent.process(envelope)
                yield PipelineEvent("stage", "think", {"status": "completed"})

            # Stage 3: Respond (STREAMING)
            yield PipelineEvent("stage", "respond", {"status": "started"})
            respond_agent = self._runtime.agents.get("respond")
            if respond_agent:
                # Check if agent supports streaming
                from jeeves_infra.protocols import TokenStreamMode

                if respond_agent.config.token_stream == TokenStreamMode.AUTHORITATIVE:
                    # TRUE STREAMING: Yield tokens as they arrive
                    async for event_type, event in respond_agent.stream(envelope):
                        yield event
                else:
                    # Fallback: Buffer complete response
                    envelope = await respond_agent.process(envelope)
                    response = envelope.outputs.get("final_response", {}).get("response", "")
                    # Simulate streaming by yielding in chunks
                    chunk_size = 10
                    for i in range(0, len(response), chunk_size):
                        yield PipelineEvent(
                            "token",
                            "respond",
                            {"token": response[i:i+chunk_size]},
                            debug=False
                        )

                yield PipelineEvent("stage", "respond", {"status": "completed"})

            # Record final resource usage via kernel_client
            runtime_hops = envelope.metadata.get("agent_hops", 0)
            runtime_llm_calls = envelope.metadata.get("llm_call_count", 0)
            runtime_tool_calls = envelope.metadata.get("tool_call_count", 0)
            tokens_in = envelope.metadata.get("total_tokens_in", 0)
            tokens_out = envelope.metadata.get("total_tokens_out", 0)

            if self._kernel_client:
                await self._kernel_client.record_usage(
                    pid=pid,
                    agent_hops=max(0, runtime_hops - 1),  # Subtract initial hop
                    llm_calls=runtime_llm_calls,
                    tool_calls=runtime_tool_calls,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                )

                # Log resource usage
                process_info = await self._kernel_client.get_process(pid)
                if process_info:
                    self._logger.info(
                        "chatbot_streaming_resource_usage",
                        request_id=request_id,
                        llm_calls=process_info.llm_calls,
                        tool_calls=process_info.tool_calls,
                        agent_hops=process_info.agent_hops,
                        tokens_in=process_info.tokens_in,
                        tokens_out=process_info.tokens_out,
                    )

            # Terminal event: done
            yield PipelineEvent(
                "done",
                "__end__",
                {
                    "final_output": envelope.outputs.get("final_response", {}),
                    "request_id": request_id
                }
            )

            self._logger.info(
                "chatbot_streaming_completed",
                request_id=request_id,
            )

        except asyncio.CancelledError:
            # Cancellation propagates (no synthetic error event)
            self._logger.info(
                "chatbot_streaming_cancelled",
                request_id=request_id,
            )
            raise
        except Exception as e:
            # Terminal event: error
            self._logger.error(
                "chatbot_streaming_error",
                request_id=request_id,
                error=str(e),
                exc_info=True,
            )
            yield PipelineEvent(
                "error",
                "__end__",
                {
                    "error": str(e),
                    "request_id": request_id
                }
            )

    def _envelope_to_result(
        self,
        envelope: Envelope,
        request_id: str,
    ) -> ChatbotResult:
        """Convert Envelope to ChatbotResult."""
        # Get the final response from the Respond agent
        final_response_output = envelope.outputs.get("final_response", {})

        # Success
        if envelope.terminal_reason == TerminalReason.COMPLETED:
            # Extract response, citations, confidence from Respond agent output
            response = final_response_output.get("response")
            citations = final_response_output.get("citations", [])
            confidence = final_response_output.get("confidence", "medium")

            if not response:
                self._logger.warning(
                    "chatbot_missing_response",
                    envelope_id=envelope.envelope_id,
                    final_response_keys=list(final_response_output.keys()) if isinstance(final_response_output, dict) else [],
                )
                return ChatbotResult(
                    status="error",
                    error="Pipeline completed but no response generated",
                    request_id=request_id,
                )

            self._logger.debug(
                "chatbot_response_extracted",
                envelope_id=envelope.envelope_id,
                response_length=len(response),
                citations_count=len(citations),
                confidence=confidence,
            )

            return ChatbotResult(
                status="success",
                response=response,
                citations=citations if citations else None,
                confidence=confidence,
                request_id=request_id,
            )

        # Error/failure
        self._logger.warning(
            "chatbot_pipeline_failed",
            envelope_id=envelope.envelope_id,
            terminal_reason=envelope.terminal_reason,
            termination_reason=envelope.termination_reason,
        )

        # Provide user-friendly error messages for common cases
        error_msg = envelope.termination_reason or "Pipeline failed"
        if "already exists" in error_msg.lower():
            error_msg = "A session for this request already exists. Please retry with a new request."
        elif "deadline" in error_msg.lower():
            error_msg = "Request timed out. Please try again."

        return ChatbotResult(
            status="error",
            error=error_msg,
            request_id=request_id,
        )

    async def handle_dispatch(self, envelope: Envelope) -> Envelope:
        """
        Control Tower dispatch handler.

        Called by Control Tower's CommBusCoordinator when routing
        requests to the hello_world service.

        Args:
            envelope: Request envelope from Control Tower

        Returns:
            Result envelope with processing results
        """
        self._logger.info(
            "dispatch_handler_invoked",
            envelope_id=envelope.envelope_id,
            request_id=envelope.request_id,
            user_id=envelope.user_id,
        )

        result_envelope = await self._run_with_resource_tracking(
            envelope,
            thread_id=envelope.session_id,
        )

        # Log final resource usage
        pid = envelope.envelope_id
        if self._kernel_client:
            process_info = await self._kernel_client.get_process(pid)
            if process_info:
                self._logger.info(
                    "dispatch_resource_usage",
                    envelope_id=pid,
                    llm_calls=process_info.llm_calls,
                    tool_calls=process_info.tool_calls,
                    agent_hops=process_info.agent_hops,
                    tokens_in=process_info.tokens_in,
                    tokens_out=process_info.tokens_out,
                )

        return result_envelope

    def get_dispatch_handler(self):
        """
        Get dispatch handler for Control Tower registration.

        Returns:
            Async callable suitable for CommBusCoordinator.register_handler()
        """
        return self.handle_dispatch


__all__ = ["ChatbotService", "ChatbotResult"]
