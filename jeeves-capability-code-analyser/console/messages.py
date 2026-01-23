"""CommBus message types for console layer.

All console communication uses these message types:
- ProcessQuery: Request to process a user query
- SubmitClarification: Resume with user clarification
- GetSystemStatus: Admin status request
- ConsoleEvent: Event published for each pipeline step
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from uuid import uuid4


@dataclass
class ProcessQuery:
    """Query message - request to process user query."""

    query: str
    session_id: str
    user_id: str
    request_id: str = field(default_factory=lambda: f"req_{uuid4().hex[:16]}")
    category: str = field(default="query", init=False)


@dataclass
class SubmitClarification:
    """Query message - resume with user clarification."""

    thread_id: str
    clarification: str
    category: str = field(default="query", init=False)


@dataclass
class GetSystemStatus:
    """Query message - admin status request."""

    category: str = field(default="query", init=False)


@dataclass
class ConsoleEvent:
    """Event message - published for each pipeline step.

    Events are published to CommBus and consumed by UI adapters.
    Event types follow the pattern: "console.{category}.{action}"

    Examples:
        - console.agent.started
        - console.agent.completed
        - console.tool.started
        - console.tool.completed
        - console.response
        - console.clarification
    """

    event_type: str
    request_id: str
    session_id: str
    agent_name: Optional[str] = None
    content: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    category: str = field(default="event", init=False)


__all__ = [
    "ProcessQuery",
    "SubmitClarification",
    "GetSystemStatus",
    "ConsoleEvent",
]
