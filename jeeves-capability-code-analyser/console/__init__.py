"""Console layer for Jeeves Code Analysis.

Provides CommBus-based UI abstraction following JSF/DDS/K8s patterns.
All UI communication flows through CommBus for full decoupling.

Components:
- messages.py: CommBus message types (ProcessQuery, ConsoleEvent)
- handler.py: Handles queries, publishes events
- adapters/: UI-specific adapters (Chainlit, CLI, etc.)
"""

from console.messages import (
    ProcessQuery,
    SubmitClarification,
    GetSystemStatus,
    ConsoleEvent,
)
from console.handler import ConsoleHandler, create_handler

__all__ = [
    "ProcessQuery",
    "SubmitClarification",
    "GetSystemStatus",
    "ConsoleEvent",
    "ConsoleHandler",
    "create_handler",
]
