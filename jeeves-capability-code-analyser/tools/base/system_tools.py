"""System and meta tools for assistant capabilities.

NOTE: The list_tools functionality is provided by session_tools.py.
This module is kept for future system-level tools that don't fit elsewhere.
"""

from typing import Optional

from protocols import LoggerProtocol
import structlog
get_logger = structlog.get_logger
# Constitutional imports - from mission_system contracts layer
from mission_system.contracts import PersistenceProtocol
from tools.registry import ToolRegistry, tool_registry


def register_system_tools(
    db: PersistenceProtocol,
    registry: Optional[ToolRegistry] = None
) -> None:
    """
    Register system and meta tools.

    Note: list_tools is registered in session_tools.py to avoid duplication.

    Args:
        db: Database client instance
        registry: Optional ToolRegistry instance. If None, uses global registry.
    """
    # list_tools is already registered in session_tools.py
    # This function is kept as a placeholder for future system tools
    _logger = get_logger()
    _logger.debug("system_tools_register_called", note="list_tools provided by session_tools")
