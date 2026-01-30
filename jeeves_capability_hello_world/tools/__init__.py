"""
Tools module for Onboarding chatbot capability.

Constitution R7 compliant tool initialization.
Tools are registered at bootstrap time, not at import time.

Contains minimal tools for demonstration:
- get_time: Get current date/time
- list_tools: Tool introspection and onboarding capabilities

Usage:
    from jeeves_capability_hello_world.tools import initialize_all_tools

    # At bootstrap time
    result = initialize_all_tools(db=db, logger=logger)
"""

from typing import Any, Dict, Optional

from .catalog import (
    ToolId,
    ToolCategory,
    RiskLevel,
    EXPOSED_TOOL_IDS,
    tool_catalog,
)
from .registration import register_all_tools
from .hello_world_tools import (
    get_time,
    list_tools,
)


def initialize_all_tools(
    db: Optional[Any] = None,
    skip_validation: bool = False,
    logger: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Initialize and register all tools.

    SINGLE CANONICAL PATH per Constitution R7.
    Called at bootstrap time, NOT at import time.

    Args:
        db: Optional database client (not used by hello-world tools)
        skip_validation: Skip validation (for testing)
        logger: Optional logger instance

    Returns:
        Dict with initialization results:
        - registration: Registration results from register_all_tools
        - catalog: Reference to tool_catalog
        - tool_count: Number of registered tools
    """
    import structlog

    if logger is None:
        logger = structlog.get_logger("tools")

    logger.info("initializing_hello_world_tools")

    # Register all tools with the catalog
    registration_result = register_all_tools(logger=logger)

    logger.info(
        "hello_world_tools_initialized",
        tool_count=tool_catalog.tool_count,
    )

    return {
        "registration": registration_result,
        "catalog": tool_catalog,
        "tool_count": tool_catalog.tool_count,
    }


__all__ = [
    # Initialization
    "initialize_all_tools",
    # Catalog exports
    "ToolId",
    "ToolCategory",
    "RiskLevel",
    "EXPOSED_TOOL_IDS",
    "tool_catalog",
    # Individual tools (for direct access if needed)
    "get_time",
    "list_tools",
]
