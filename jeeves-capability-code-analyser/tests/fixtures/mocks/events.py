"""Mock event bus for testing.

Provides event capture for testing agent event emissions
without requiring a real event bus.
"""

from typing import Any, Callable, Dict, List, Optional


class MockEventBus:
    """Mock event bus for testing.

    Captures all emitted events for assertion in tests.
    """

    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self._subscribers: Dict[str, List[Callable]] = {}

    async def emit(self, event: Any) -> None:
        """Emit an event (capture for testing)."""
        self.events.append(event)

    def subscribe(self, pattern: str, handler: Callable) -> Callable[[], None]:
        """Subscribe to events matching pattern."""
        if pattern not in self._subscribers:
            self._subscribers[pattern] = []
        self._subscribers[pattern].append(handler)
        return lambda: self._subscribers[pattern].remove(handler)

    async def emit_agent_started(
        self,
        agent_name: str,
        envelope_id: Optional[str] = None,
        **payload
    ) -> None:
        """Emit agent started event."""
        self.events.append({
            "event_type": "agent.started",
            "agent_name": agent_name,
            "envelope_id": envelope_id,
            **payload,
        })

    async def emit_agent_completed(
        self,
        agent_name: str,
        status: str,
        error: Optional[str] = None,
        duration_ms: Optional[int] = None,
        **payload
    ) -> None:
        """Emit agent completed event."""
        self.events.append({
            "event_type": "agent.completed",
            "agent_name": agent_name,
            "status": status,
            "error": error,
            "duration_ms": duration_ms,
            **payload,
        })

    async def emit_transition(
        self,
        from_node: str,
        to_node: str,
        reason: Optional[str] = None,
        **payload
    ) -> None:
        """Emit transition event."""
        self.events.append({
            "type": "transition",
            "from": from_node,
            "to": to_node,
            "reason": reason,
            **payload,
        })

    async def emit_pipeline_started(
        self,
        pipeline_name: str,
        envelope_id: str,
        **payload
    ) -> None:
        """Emit pipeline started event."""
        self.events.append({
            "type": "pipeline.started",
            "pipeline": pipeline_name,
            "envelope_id": envelope_id,
            **payload,
        })

    async def emit_pipeline_completed(
        self,
        pipeline_name: str,
        envelope_id: str,
        status: str,
        duration_ms: int,
        **payload
    ) -> None:
        """Emit pipeline completed event."""
        self.events.append({
            "type": "pipeline.completed",
            "pipeline": pipeline_name,
            "envelope_id": envelope_id,
            "status": status,
            "duration_ms": duration_ms,
            **payload,
        })

    async def emit_tool_started(
        self,
        tool_name: str,
        step: int,
        total: int,
        **payload
    ) -> None:
        """Emit tool started event."""
        self.events.append({
            "type": "tool.started",
            "tool": tool_name,
            "step": step,
            "total": total,
            **payload,
        })

    async def emit_tool_completed(
        self,
        tool_name: str,
        status: str,
        execution_time_ms: int,
        error: Optional[str] = None,
        **payload
    ) -> None:
        """Emit tool completed event."""
        self.events.append({
            "type": "tool.completed",
            "tool": tool_name,
            "status": status,
            "execution_time_ms": execution_time_ms,
            "error": error,
            **payload,
        })

    def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """Get all events of a specific type."""
        return [e for e in self.events if e.get("event_type") == event_type]

    def get_agent_events(self, agent_name: str) -> List[Dict[str, Any]]:
        """Get all events for a specific agent."""
        return [e for e in self.events if e.get("agent_name") == agent_name]

    def reset(self):
        """Clear all captured events."""
        self.events = []

    @property
    def event_types(self) -> List[str]:
        """Get list of captured event types."""
        return [e.get("event_type") for e in self.events if e.get("event_type")]
