"""
CodeAnalysisService - Clean wrapper for UnifiedRuntime.

Provides the same interface as the old CodeAnalysisFlowService but uses
the centralized architecture (v4.0) with UnifiedRuntime + PipelineConfig.

Includes Control Tower dispatch handler for kernel-level orchestration.

Resource Tracking Integration:
- Records LLM calls, tool calls, and agent hops via Control Tower
- Checks quotas before and during execution
- Terminates processing if quota exceeded
"""

import time
from typing import Any, AsyncIterator, Callable, Dict, Optional, TYPE_CHECKING
from uuid import uuid4

from jeeves_mission_system.contracts_core import (
    UnifiedRuntime,
    create_runtime_from_config,
    create_generic_envelope,
    GenericEnvelope,
    TerminalReason,
    LoggerProtocol,
    PersistenceProtocol,
    ToolExecutorProtocol,
    LLMProviderProtocol,
)
from jeeves_mission_system.orchestrator.agent_events import AgentEvent, AgentEventType
from pipeline_config import CODE_ANALYSIS_PIPELINE
from orchestration.types import CodeAnalysisResult

if TYPE_CHECKING:
    from jeeves_control_tower.protocols import ControlTowerProtocol

# Type alias for Control Tower dispatch handler
DispatchHandler = Callable[[GenericEnvelope], "asyncio.Future[GenericEnvelope]"]


class CodeAnalysisService:
    """
    Service wrapper for UnifiedRuntime executing code analysis pipeline.

    This replaces the old CodeAnalysisFlowService which used concrete agent
    classes. Now uses configuration-driven UnifiedRuntime.

    Resource Tracking:
    - When control_tower is provided, records all resource usage
    - LLM calls, tool calls, agent hops tracked per-request
    - Quota enforcement terminates over-limit requests
    """

    def __init__(
        self,
        *,
        llm_provider_factory,
        tool_executor: ToolExecutorProtocol,
        logger: LoggerProtocol,
        persistence: Optional[PersistenceProtocol] = None,
        control_tower: Optional["ControlTowerProtocol"] = None,
        use_mock: bool = False,
    ):
        """
        Initialize CodeAnalysisService.

        Args:
            llm_provider_factory: Factory to create LLM providers per role
            tool_executor: Tool executor for agent tool calls
            logger: Logger instance
            persistence: Optional persistence for state storage
            control_tower: Optional Control Tower for resource tracking
            use_mock: Use mock handlers for testing
        """
        # Get the global prompt registry
        from jeeves_mission_system.prompts.core.registry import PromptRegistry
        prompt_registry = PromptRegistry.get_instance()

        self._runtime = create_runtime_from_config(
            config=CODE_ANALYSIS_PIPELINE,
            llm_provider_factory=llm_provider_factory,
            tool_executor=tool_executor,
            logger=logger,
            persistence=persistence,
            prompt_registry=prompt_registry,
            use_mock=use_mock,
        )
        self._persistence = persistence
        self._logger = logger
        self._control_tower = control_tower

    async def process_query(
        self,
        *,
        user_id: str,
        session_id: str,
        query: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CodeAnalysisResult:
        """
        Process a code analysis query through the pipeline (non-streaming).

        This is a convenience wrapper around process_query_streaming that
        collects all events and returns only the final result.

        For real-time event visibility, use process_query_streaming instead.

        Args:
            user_id: User identifier
            session_id: Session identifier for state persistence
            query: User's query text
            metadata: Optional metadata dict

        Returns:
            CodeAnalysisResult with response or clarification request
        """
        result = None
        async for event in self.process_query_streaming(
            user_id=user_id,
            session_id=session_id,
            query=query,
            metadata=metadata,
        ):
            # Keep the last CodeAnalysisResult (final response)
            if isinstance(event, CodeAnalysisResult):
                result = event

        if result is None:
            return CodeAnalysisResult(
                status="error",
                error="Pipeline completed without producing a result",
            )
        return result

    async def process_query_streaming(
        self,
        *,
        user_id: str,
        session_id: str,
        query: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[Any]:
        """
        Process a code analysis query through the pipeline with event streaming.

        Args:
            user_id: User identifier
            session_id: Session identifier for state persistence
            query: User's query text
            metadata: Optional metadata dict

        Yields:
            AgentEvent or CodeAnalysisResult instances
        """
        request_id = f"req_{uuid4().hex[:16]}"

        envelope = create_generic_envelope(
            raw_input=query,
            user_id=user_id,
            session_id=session_id,
            request_id=request_id,
            metadata=metadata,
        )

        self._logger.info(
            "code_analysis_started_streaming",
            request_id=request_id,
            user_id=user_id,
            session_id=session_id,
        )

        # Constitutional EventOrchestrator pattern for event streaming
        # Events flow: Orchestrator → gRPC → Gateway → WebSocket
        # NO cross-process gateway injection (orchestrator and gateway are separate processes)
        import asyncio
        from jeeves_mission_system.orchestrator.events import create_event_orchestrator

        # Create event orchestrator for streaming (no gateway injection needed)
        orchestrator = create_event_orchestrator(
            session_id=session_id,
            request_id=request_id,
            user_id=user_id,
            enable_streaming=True,
            enable_persistence=False,
        )

        # Set event context on runtime so agents automatically emit events
        self._runtime.set_event_context(orchestrator.context)

        # Emit FLOW_STARTED event
        yield AgentEvent(
            event_type=AgentEventType.FLOW_STARTED,
            agent_name="orchestrator",
            request_id=request_id,
            session_id=session_id,
            timestamp_ms=int(time.time() * 1000),
            payload={"query": query},
        )

        # Run pipeline and close orchestrator when done
        # The close() puts a None sentinel in the queue to signal end of events
        async def run_pipeline_and_signal():
            try:
                result_envelope = await self._runtime.run(envelope, thread_id=session_id)
                return result_envelope
            finally:
                # Signal end of events AFTER pipeline completes
                # Events are FIFO - all emitted events will be consumed before this sentinel
                await orchestrator.close()

        pipeline_task = asyncio.create_task(run_pipeline_and_signal())

        # Yield control to let pipeline task start before we block on queue.get()
        # This ensures the pipeline has a chance to emit events
        await asyncio.sleep(0)

        # Stream events as they're emitted by agents (Constitutional pattern)
        # The event loop interleaves: pipeline emits → queue.put() → queue.get() → yield
        try:
            async for event in orchestrator.events():
                yield event

            # Pipeline has signaled completion (sentinel received)
            # Now wait for the task to get the result envelope
            envelope_result = await pipeline_task

            # Convert envelope to result and emit final response
            result = self._envelope_to_result(envelope_result, session_id)
            yield result

        except Exception as e:
            self._logger.error(
                "code_analysis_streaming_error",
                request_id=request_id,
                error=str(e),
            )
            # Cancel pipeline task if still running
            if not pipeline_task.done():
                pipeline_task.cancel()
                try:
                    await pipeline_task
                except asyncio.CancelledError:
                    pass
            # Emit error result
            yield CodeAnalysisResult(
                status="error",
                error=str(e),
                request_id=request_id,
            )

    async def resume_with_clarification(
        self,
        *,
        thread_id: str,
        clarification: str,
    ) -> CodeAnalysisResult:
        """
        Resume pipeline with user's clarification response.

        Args:
            thread_id: Thread/session ID from clarification request
            clarification: User's clarification text

        Returns:
            CodeAnalysisResult with response or further clarification

        Raises:
            ValueError: If thread not found or persistence unavailable
        """
        if not self._persistence:
            raise ValueError("Persistence required for clarification resume")

        # Load envelope state from persistence
        state = await self._persistence.load_state(thread_id)
        if not state:
            raise ValueError(f"Thread not found: {thread_id}")

        # Reconstruct envelope from state
        envelope_data = state.get("envelope")
        if not envelope_data:
            raise ValueError(f"Invalid thread state: missing envelope for {thread_id}")
        envelope = GenericEnvelope.model_validate(envelope_data)

        # Update with clarification
        envelope.interrupt_pending = False
        envelope.interrupt = None
        envelope.metadata["user_clarification"] = clarification

        # Store clarification in intent metadata for reprocessing
        if "intent" in envelope.outputs:
            envelope.outputs["intent"]["clarification_response"] = clarification

        # Resume from intent stage
        envelope.current_stage = "intent"

        self._logger.info(
            "code_analysis_resumed",
            thread_id=thread_id,
            clarification_length=len(clarification),
        )

        envelope = await self._runtime.run(envelope, thread_id=thread_id)

        return self._envelope_to_result(envelope, thread_id)

    async def handle_dispatch(self, envelope: GenericEnvelope) -> GenericEnvelope:
        """Control Tower dispatch handler.

        This method is called by Control Tower's CommBusCoordinator when
        routing requests to the code_analysis service.

        Resource Tracking:
        - Records agent hops during pipeline execution
        - Checks quotas and terminates if exceeded
        - LLM/tool call tracking integrated via callbacks

        Args:
            envelope: GenericEnvelope with request data

        Returns:
            GenericEnvelope with processing results
        """
        pid = envelope.envelope_id

        self._logger.info(
            "dispatch_handler_invoked",
            envelope_id=pid,
            request_id=envelope.request_id,
            user_id=envelope.user_id,
            has_control_tower=self._control_tower is not None,
        )

        # Check if this is a clarification resume
        if envelope.metadata.get("user_clarification"):
            # Resume from clarification
            self._logger.info(
                "dispatch_resuming_clarification",
                envelope_id=pid,
            )
            envelope.interrupt_pending = False
            envelope.current_stage = "intent"

        # Run through pipeline with resource tracking
        result_envelope = await self._run_with_resource_tracking(
            envelope,
            thread_id=envelope.session_id,
        )

        # Mark as terminated if completed successfully or errored
        if result_envelope.terminal_reason == TerminalReason.COMPLETED:
            result_envelope.terminated = True
        elif result_envelope.terminal_reason and result_envelope.terminal_reason != TerminalReason.COMPLETED:
            result_envelope.terminated = True

        # If clarification needed, don't mark as terminated
        if result_envelope.interrupt_pending and result_envelope.interrupt and result_envelope.interrupt.get("type") == "clarification":
            result_envelope.terminated = False

        # Log final resource usage
        if self._control_tower:
            usage = self._control_tower.resources.get_usage(pid)
            if usage:
                self._logger.info(
                    "dispatch_resource_usage",
                    envelope_id=pid,
                    llm_calls=usage.llm_calls,
                    tool_calls=usage.tool_calls,
                    agent_hops=usage.agent_hops,
                    tokens_in=usage.tokens_in,
                    tokens_out=usage.tokens_out,
                )

        return result_envelope

    async def _run_with_resource_tracking(
        self,
        envelope: GenericEnvelope,
        thread_id: str,
    ) -> GenericEnvelope:
        """Run pipeline with Control Tower resource tracking.

        Wraps runtime execution to track:
        - Agent hops (each agent transition)
        - LLM calls (via envelope metadata)
        - Tool calls (via envelope metadata)

        Args:
            envelope: Request envelope
            thread_id: Thread/session ID

        Returns:
            Result envelope (may be terminated if quota exceeded)
        """
        pid = envelope.envelope_id

        # Track initial agent hop (entering pipeline)
        if self._control_tower:
            quota_exceeded = self._control_tower.resources.record_usage(
                pid=pid,
                agent_hops=1,  # Entry to pipeline
            )
            if quota_exceeded := self._control_tower.resources.check_quota(pid):
                self._logger.warning(
                    "quota_exceeded_before_run",
                    envelope_id=pid,
                    reason=quota_exceeded,
                )
                envelope.terminated = True
                envelope.termination_reason = quota_exceeded
                envelope.terminal_reason = TerminalReason.MAX_ITERATIONS_EXCEEDED
                return envelope

        # Run the pipeline
        result_envelope = await self._runtime.run(
            envelope,
            thread_id=thread_id,
        )

        # Extract resource usage from envelope metadata (if tracked by runtime)
        # The runtime may track agent_hops, llm_calls in metadata
        # Log warning if expected metrics are missing to catch tracking failures
        expected_metrics = ["agent_hops", "llm_call_count", "tool_call_count"]
        missing_metrics = [m for m in expected_metrics if m not in result_envelope.metadata]
        if missing_metrics:
            self._logger.warning(
                "runtime_metrics_missing",
                envelope_id=pid,
                missing=missing_metrics,
            )
        runtime_hops = result_envelope.metadata.get("agent_hops", 0)
        runtime_llm_calls = result_envelope.metadata.get("llm_call_count", 0)
        runtime_tool_calls = result_envelope.metadata.get("tool_call_count", 0)
        tokens_in = result_envelope.metadata.get("total_tokens_in", 0)
        tokens_out = result_envelope.metadata.get("total_tokens_out", 0)

        # Record final resource usage
        if self._control_tower:
            self._control_tower.resources.record_usage(
                pid=pid,
                agent_hops=max(0, runtime_hops - 1),  # Subtract initial hop
                llm_calls=runtime_llm_calls,
                tool_calls=runtime_tool_calls,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
            )

            # Check quota after run
            if quota_exceeded := self._control_tower.resources.check_quota(pid):
                self._logger.warning(
                    "quota_exceeded_after_run",
                    envelope_id=pid,
                    reason=quota_exceeded,
                )
                # Don't override if already terminated with a different reason
                if not result_envelope.terminated:
                    result_envelope.terminated = True
                    result_envelope.termination_reason = quota_exceeded
                    if "llm" in quota_exceeded.lower():
                        result_envelope.terminal_reason = TerminalReason.MAX_LLM_CALLS_EXCEEDED
                    elif "agent" in quota_exceeded.lower() or "hop" in quota_exceeded.lower():
                        result_envelope.terminal_reason = TerminalReason.MAX_ITERATIONS_EXCEEDED
                    else:
                        result_envelope.terminal_reason = TerminalReason.MAX_ITERATIONS_EXCEEDED

        return result_envelope

    def get_dispatch_handler(self) -> Callable[[GenericEnvelope], Any]:
        """Get the dispatch handler for Control Tower registration.

        Returns:
            Async callable suitable for CommBusCoordinator.register_handler()
        """
        return self.handle_dispatch

    def _envelope_to_result(
        self,
        envelope: GenericEnvelope,
        session_id: str,
    ) -> CodeAnalysisResult:
        """Convert GenericEnvelope to CodeAnalysisResult."""
        integration = envelope.outputs.get("integration", {})
        traversal = envelope.metadata.get("traversal_state", {})

        # Clarification pending - return question
        if envelope.interrupt_pending and envelope.interrupt and envelope.interrupt.get("type") == "clarification":
            self._logger.info(
                "code_analysis_clarification_needed",
                envelope_id=envelope.envelope_id,
            )
            return CodeAnalysisResult(
                status="clarification_needed",
                clarification_question=envelope.interrupt.get("question"),
                thread_id=session_id,
                envelope_id=envelope.envelope_id,
                request_id=envelope.request_id,
            )

        # Success
        if envelope.terminal_reason == TerminalReason.COMPLETED:
            # Get final response - try final_response first, then fall back to response
            # (LLM output parsing may fallback to {"response": ...} if JSON is truncated)
            final_response = integration.get("final_response") or integration.get("response")

            # Debug log integration output structure for diagnostics
            integration_keys = list(integration.keys()) if isinstance(integration, dict) else []
            self._logger.debug(
                "code_analysis_integration_output",
                envelope_id=envelope.envelope_id,
                integration_keys=integration_keys,
                has_final_response="final_response" in integration_keys,
                has_response="response" in integration_keys,
                action=integration.get("action"),
                final_response_length=len(final_response) if final_response else 0,
            )

            self._logger.info(
                "code_analysis_completed",
                envelope_id=envelope.envelope_id,
                files_examined=len(traversal.get("explored_files", [])),
                has_response=bool(final_response),
            )
            return CodeAnalysisResult(
                status="complete",
                response=final_response,
                thread_id=session_id,
                envelope_id=envelope.envelope_id,
                request_id=envelope.request_id,
                files_examined=traversal.get("explored_files", []),
                citations=integration.get("citations", []),
            )

        # Error/failure
        self._logger.warning(
            "code_analysis_failed",
            envelope_id=envelope.envelope_id,
            terminal_reason=envelope.terminal_reason,
            termination_reason=envelope.termination_reason,
        )
        return CodeAnalysisResult(
            status="error",
            error=envelope.termination_reason or "Pipeline failed",
            envelope_id=envelope.envelope_id,
            request_id=envelope.request_id,
        )


__all__ = ["CodeAnalysisService"]
