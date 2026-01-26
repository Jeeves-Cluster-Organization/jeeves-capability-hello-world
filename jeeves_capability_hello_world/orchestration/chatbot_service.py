"""
ChatbotService - Simple wrapper for PipelineRunner with general chatbot pipeline.

Provides a clean interface for running the 3-agent chatbot pipeline
(Understand → Think → Respond) using the centralized architecture.

This is a simplified version for hello-world demonstration - no streaming,
no Control Tower integration, no clarification handling.
"""

from typing import Any, Dict, List, Optional, AsyncIterator
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
from protocols import RequestContext


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

    This is a simplified service for the hello-world template:
    - 3-agent pipeline (Understand → Think → Respond)
    - Real LLM inference (no mocks by default)
    - Simple request/response (no streaming)
    - No Control Tower integration
    """

    def __init__(
        self,
        *,
        llm_provider_factory,
        tool_executor: ToolExecutorProtocol,
        logger: LoggerProtocol,
        pipeline_config: PipelineConfig,
        use_mock: bool = False,
    ):
        """
        Initialize ChatbotService.

        Args:
            llm_provider_factory: Factory to create LLM providers per role
            tool_executor: Tool executor for agent tool calls
            logger: Logger instance
            pipeline_config: Pipeline configuration (GENERAL_CHATBOT_PIPELINE)
            use_mock: Use mock handlers for testing (default: False - use real LLM)
        """
        # Get the global prompt registry
        from mission_system.prompts.core.registry import PromptRegistry
        prompt_registry = PromptRegistry.get_instance()

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
            # Run the 3-agent pipeline (Understand → Think → Respond)
            result_envelope = await self._runtime.run(envelope, thread_id=session_id)

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
        from protocols.envelope import PipelineEvent

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
            "chatbot_streaming_started",
            request_id=request_id,
            user_id=user_id,
            session_id=session_id,
        )

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
                from protocols.config import TokenStreamMode

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
        return ChatbotResult(
            status="error",
            error=envelope.termination_reason or "Pipeline failed",
            request_id=request_id,
        )


__all__ = ["ChatbotService", "ChatbotResult"]
