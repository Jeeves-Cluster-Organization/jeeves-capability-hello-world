"""Console handler - bridges CodeAnalysisService to CommBus.

Registers handlers with CommBus to process console queries
and publishes ConsoleEvents for each pipeline step.
"""

from typing import Any, Dict
import structlog

from control_tower.ipc import get_commbus
from mission_system.orchestrator.agent_events import AgentEvent, AgentEventType

from console.messages import (
    ProcessQuery,
    SubmitClarification,
    GetSystemStatus,
    ConsoleEvent,
)

logger = structlog.get_logger()


# Map AgentEventType to console event types
_EVENT_TYPE_MAP = {
    AgentEventType.AGENT_STARTED: "console.agent.started",
    AgentEventType.AGENT_COMPLETED: "console.agent.completed",
    AgentEventType.PERCEPTION_STARTED: "console.perception.started",
    AgentEventType.PERCEPTION_COMPLETED: "console.perception.completed",
    AgentEventType.INTENT_STARTED: "console.intent.started",
    AgentEventType.INTENT_COMPLETED: "console.intent.completed",
    AgentEventType.PLANNER_STARTED: "console.planner.started",
    AgentEventType.PLANNER_COMPLETED: "console.planner.completed",
    AgentEventType.TRAVERSER_STARTED: "console.traverser.started",
    AgentEventType.TRAVERSER_COMPLETED: "console.traverser.completed",
    AgentEventType.TOOL_STARTED: "console.tool.started",
    AgentEventType.TOOL_COMPLETED: "console.tool.completed",
    AgentEventType.SYNTHESIZER_STARTED: "console.synthesizer.started",
    AgentEventType.SYNTHESIZER_COMPLETED: "console.synthesizer.completed",
    AgentEventType.CRITIC_STARTED: "console.critic.started",
    AgentEventType.CRITIC_DECISION: "console.critic.decision",
    AgentEventType.INTEGRATION_STARTED: "console.integration.started",
    AgentEventType.INTEGRATION_COMPLETED: "console.integration.completed",
    AgentEventType.FLOW_STARTED: "console.flow.started",
    AgentEventType.FLOW_COMPLETED: "console.flow.completed",
    AgentEventType.FLOW_ERROR: "console.flow.error",
    AgentEventType.STAGE_TRANSITION: "console.stage.transition",
}


class ConsoleHandler:
    """Handles console queries via CommBus."""

    def __init__(self, service):
        """Initialize with CodeAnalysisService instance."""
        self.service = service
        self.bus = get_commbus()

    def register(self):
        """Register handlers with CommBus."""
        self.bus.register_handler("ProcessQuery", self._handle_query)
        self.bus.register_handler("SubmitClarification", self._handle_clarification)
        self.bus.register_handler("GetSystemStatus", self._handle_status)
        logger.info("console_handler_registered")

    async def _handle_query(self, query: ProcessQuery) -> Dict[str, Any]:
        """Process query, publish events for each step."""
        logger.info(
            "console_query_received",
            request_id=query.request_id,
            session_id=query.session_id,
        )

        result = None
        async for event in self.service.process_query_streaming(
            user_id=query.user_id,
            session_id=query.session_id,
            query=query.query,
        ):
            if isinstance(event, AgentEvent):
                console_event = self._map_agent_event(event)
                await self.bus.publish(console_event)
            else:
                # CodeAnalysisResult
                result = event

        # Publish final response or clarification
        if result:
            if result.status == "clarification_needed":
                await self.bus.publish(ConsoleEvent(
                    event_type="console.clarification",
                    request_id=result.request_id or "",
                    session_id=query.session_id,
                    content=result.clarification_question,
                    metadata={"thread_id": result.thread_id},
                ))
            elif result.status == "complete":
                await self.bus.publish(ConsoleEvent(
                    event_type="console.response",
                    request_id=result.request_id or "",
                    session_id=query.session_id,
                    content=result.response,
                    metadata={
                        "files_examined": result.files_examined or [],
                        "citations": result.citations or [],
                    },
                ))
            elif result.status == "error":
                await self.bus.publish(ConsoleEvent(
                    event_type="console.error",
                    request_id=result.request_id or "",
                    session_id=query.session_id,
                    content=result.error,
                ))

        return {"status": "completed", "request_id": query.request_id}

    async def _handle_clarification(self, msg: SubmitClarification) -> Dict[str, Any]:
        """Resume with user clarification."""
        result = await self.service.resume_with_clarification(
            thread_id=msg.thread_id,
            clarification=msg.clarification,
        )

        if result.status == "complete":
            await self.bus.publish(ConsoleEvent(
                event_type="console.response",
                request_id=result.request_id or "",
                session_id="",
                content=result.response,
            ))

        return {"status": result.status}

    async def _handle_status(self, msg: GetSystemStatus) -> Dict[str, Any]:
        """Return system status for admin view."""
        return {
            "status": "healthy",
            "service": "code_analysis",
            "agents": [
                "perception", "intent", "planner", "traverser",
                "synthesizer", "critic", "integration"
            ],
        }

    def _map_agent_event(self, event: AgentEvent) -> ConsoleEvent:
        """Map AgentEvent to ConsoleEvent."""
        event_type = _EVENT_TYPE_MAP.get(event.event_type, f"console.{event.event_type.value}")

        return ConsoleEvent(
            event_type=event_type,
            request_id=event.request_id,
            session_id=event.session_id,
            agent_name=event.agent_name,
            content=event.payload.get("summary") or event.payload.get("output"),
            metadata={
                **event.payload,
                "request_context": event.request_context.to_dict(),
            },
        )


def create_handler(service=None):
    """Factory to create ConsoleHandler.

    If service is not provided, creates one using default wiring.
    """
    if service is None:
        from orchestration.wiring import create_code_analysis_service_from_components
        from mission_system.adapters import create_tool_executor, create_llm_provider_factory
        import os

        # Optional airframe path for Chainlit/CommBus runs
        from airframe_settings import is_airframe_enabled, is_airframe_strict
        airframe_enabled = is_airframe_enabled()
        if airframe_enabled:
            try:
                from airframe_bridge import create_airframe_registry_from_env, create_airframe_llm_factory
                registry = create_airframe_registry_from_env()
                llm_factory = create_airframe_llm_factory(registry)
                logger.info("airframe_enabled_console", endpoint_count=len(registry.list_endpoints()))
            except Exception as e:
                logger.warning(
                    "airframe_init_failed_falling_back",
                    entrypoint="chainlit",
                    airframe_enabled=airframe_enabled,
                    exception_class=type(e).__name__,
                    exception_message=str(e),
                )
                if is_airframe_strict():
                    raise
                llm_factory = create_llm_provider_factory()
        else:
            llm_factory = create_llm_provider_factory()

        service = create_code_analysis_service_from_components(
            llm_provider_factory=llm_factory,
            tool_executor=create_tool_executor(),
            use_mock=False,
        )

    return ConsoleHandler(service)


__all__ = ["ConsoleHandler", "create_handler"]
