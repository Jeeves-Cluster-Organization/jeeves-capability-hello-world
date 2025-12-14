"""CodeAnalysisServicer - gRPC adapter for CodeAnalysisFlowService.

This servicer adapts the LangGraph-based CodeAnalysisFlowService interface
to the gRPC-compatible interface expected by JeevesFlowServicer.

Architecture (Constitutional):
  gRPC Request → JeevesFlowServicer (core/generic)
                   ↓
                 CodeAnalysisServicer (capability-specific adapter)
                   ↓
                 CodeAnalysisFlowService (LangGraph pipeline)

This servicer lives in the capability layer (jeeves-capability-code-analyser)
to maintain Constitutional separation: mission_system (core) knows nothing
about code_analysis capability specifics.
"""

import json
from typing import Any, AsyncIterator, Optional

from jeeves_mission_system.adapters import get_logger
from jeeves_mission_system.contracts import LoggerProtocol
from jeeves_mission_system.orchestrator.agent_events import AgentEvent, AgentEventType
from orchestration.types import CodeAnalysisResult

# Import proto module for gRPC message conversion
try:
    from proto import jeeves_pb2
    _PROTO_AVAILABLE = True
except ImportError:
    jeeves_pb2 = None
    _PROTO_AVAILABLE = False


# Map AgentEventType to FlowEvent.EventType values
_AGENT_EVENT_TYPE_MAP = {
    AgentEventType.AGENT_STARTED: 11,
    AgentEventType.AGENT_COMPLETED: 12,
    AgentEventType.PERCEPTION_STARTED: 11,
    AgentEventType.PERCEPTION_COMPLETED: 12,
    AgentEventType.INTENT_STARTED: 11,
    AgentEventType.INTENT_COMPLETED: 12,
    AgentEventType.PLANNER_STARTED: 11,
    AgentEventType.PLANNER_COMPLETED: 2,  # PLAN_CREATED
    AgentEventType.TRAVERSER_STARTED: 11,
    AgentEventType.TRAVERSER_COMPLETED: 12,
    AgentEventType.TOOL_STARTED: 3,
    AgentEventType.TOOL_COMPLETED: 4,
    AgentEventType.SYNTHESIZER_STARTED: 11,
    AgentEventType.SYNTHESIZER_COMPLETED: 13,  # SYNTHESIZER_COMPLETE
    AgentEventType.CRITIC_STARTED: 11,
    AgentEventType.CRITIC_DECISION: 10,
    AgentEventType.INTEGRATION_STARTED: 11,
    AgentEventType.INTEGRATION_COMPLETED: 12,
    AgentEventType.STAGE_TRANSITION: 14,
    AgentEventType.FLOW_STARTED: 9,
    AgentEventType.FLOW_COMPLETED: 5,  # RESPONSE_READY
    AgentEventType.FLOW_ERROR: 8,
}


class CodeAnalysisServicer:
    """
    gRPC servicer adapter for Code Analysis pipeline.

    Provides a process_request method compatible with JeevesFlowServicer
    expectations, delegating to CodeAnalysisFlowService.process_query_streaming().
    """

    def __init__(
        self,
        code_analysis_service: Any,
        db: Any = None,  # For compatibility, not used
        logger: Optional[LoggerProtocol] = None,
    ):
        """
        Initialize the servicer.

        Args:
            code_analysis_service: CodeAnalysisFlowService instance
            db: Database client (compatibility parameter, not used)
            logger: Optional logger instance
        """
        self._logger = logger or get_logger()
        self.code_analysis_service = code_analysis_service
        self.db = db

    def _convert_to_flow_event(self, event: Any, session_id: str) -> Any:
        """
        Convert internal events to gRPC FlowEvent protobuf messages.

        Args:
            event: AgentEvent or CodeAnalysisResult
            session_id: Session ID for the event

        Returns:
            jeeves_pb2.FlowEvent protobuf message
        """
        if not _PROTO_AVAILABLE:
            # Fallback: return event as-is if proto not available
            return event

        if isinstance(event, AgentEvent):
            # Convert AgentEvent to FlowEvent
            event_type = _AGENT_EVENT_TYPE_MAP.get(event.event_type, 11)  # Default to AGENT_STARTED
            payload = event.to_dict()

            return jeeves_pb2.FlowEvent(
                type=event_type,
                request_id=event.request_id,
                session_id=event.session_id or session_id,
                payload=json.dumps(payload).encode('utf-8'),
                timestamp_ms=event.timestamp_ms,
            )

        elif isinstance(event, CodeAnalysisResult):
            # Convert CodeAnalysisResult to FlowEvent
            if event.status == "complete":
                event_type = 5  # RESPONSE_READY
            elif event.status == "clarification_needed":
                event_type = 6  # CLARIFICATION
            elif event.status == "error":
                event_type = 8  # ERROR
            else:
                event_type = 5  # Default to RESPONSE_READY

            payload = {
                "status": event.status,
                "response": event.response,
                "clarification_question": event.clarification_question,
                "error": event.error,
                "files_examined": event.files_examined,
                "citations": event.citations,
            }

            return jeeves_pb2.FlowEvent(
                type=event_type,
                request_id=event.request_id or "",
                session_id=event.thread_id or session_id,
                payload=json.dumps(payload).encode('utf-8'),
                timestamp_ms=0,  # Result doesn't have timestamp
            )

        else:
            # Unknown event type - log warning and return as-is
            self._logger.warning("unknown_event_type", event_type=type(event).__name__)
            return event

    async def process_request(
        self,
        user_id: str,
        session_id: str,
        message: str,
        context: Any,
    ) -> AsyncIterator[Any]:
        """
        Process a code analysis request (gRPC-compatible interface).

        This method adapts the gRPC parameters to the CodeAnalysisFlowService
        streaming interface, converting internal events to gRPC FlowEvent messages.

        Args:
            user_id: User identifier
            session_id: Session identifier
            message: User's code analysis query
            context: gRPC servicer context (not used, for compatibility)

        Yields:
            jeeves_pb2.FlowEvent protobuf messages
        """
        self._logger.info(
            "code_analysis_servicer_processing",
            user_id=user_id,
            session_id=session_id,
            message_length=len(message),
        )

        # Delegate to CodeAnalysisFlowService streaming method
        event_count = 0
        async for event in self.code_analysis_service.process_query_streaming(
            user_id=user_id,
            session_id=session_id,
            query=message,
        ):
            event_count += 1
            # Diagnostic: log each event received
            event_type_name = type(event).__name__
            self._logger.debug(
                "servicer_event_received",
                event_number=event_count,
                event_type=event_type_name,
                is_agent_event=isinstance(event, AgentEvent),
            )
            # Convert internal events to gRPC FlowEvent messages
            flow_event = self._convert_to_flow_event(event, session_id)
            self._logger.debug(
                "servicer_event_yielded",
                event_number=event_count,
                flow_event_type=getattr(flow_event, 'type', 'unknown'),
            )
            yield flow_event

        self._logger.info(
            "servicer_stream_complete",
            total_events=event_count,
        )
