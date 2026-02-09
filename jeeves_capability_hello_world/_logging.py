"""Capability-local structured logging utilities.

Replaces jeeves_infra.utils.logging imports with direct structlog usage.
Satisfies import boundary: no jeeves_infra.utils imports in capability code.
"""

import structlog
from typing import Any, Optional


def get_component_logger(component: str, logger: Optional[Any] = None) -> Any:
    """Get logger bound to a component name.

    Args:
        component: Component name (e.g., "ChunkService", "EventRepository")
        logger: Optional injected logger. If None, uses default structlog logger.

    Returns:
        Logger bound to the component name
    """
    base = logger or structlog.get_logger()
    return base.bind(component=component)


def get_logger() -> Any:
    """Get default structured logger."""
    return structlog.get_logger()
