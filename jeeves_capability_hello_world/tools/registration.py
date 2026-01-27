"""
Tool Registration for Hello World Capability.

Constitution R7 compliant tool registration.
Single entry point for registering all tools with the catalog.

Architecture:
    Tools are registered at capability initialization time, not at import time.
    This avoids side effects during module import.
"""

from typing import Any, Dict, Optional
import structlog

from jeeves_capability_hello_world.tools.catalog import (
    tool_catalog,
    ToolId,
    ToolCategory,
    RiskLevel,
)


def register_all_tools(logger: Optional[Any] = None) -> Dict[str, Any]:
    """
    Register all Hello World tools with the catalog.

    SINGLE entry point for tool registration.
    Called at capability bootstrap time, NOT at import time.

    Args:
        logger: Optional logger instance

    Returns:
        Dict with registration results:
        - count: Number of tools registered
        - registered: List of registered tool IDs
    """
    if logger is None:
        logger = structlog.get_logger("tools.registration")

    # Import tool functions (deferred to avoid import-time side effects)
    from jeeves_capability_hello_world.tools.hello_world_tools import (
        web_search,
        get_time,
        list_tools,
    )

    logger.info("registering_hello_world_tools")

    # Register web_search tool
    tool_catalog.register(
        tool_id=ToolId.WEB_SEARCH.value,
        func=web_search,
        description="Search the web for current information, news, and facts",
        category=ToolCategory.SEARCH.value,
        risk_level=RiskLevel.EXTERNAL.value,
        parameters={
            "query": {
                "type": "string",
                "description": "The search query",
                "required": True,
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results (default: 5)",
                "required": False,
                "default": 5,
            },
        },
        is_async=True,
    )

    # Register get_time tool
    tool_catalog.register(
        tool_id=ToolId.GET_TIME.value,
        func=get_time,
        description="Get the current date and time (UTC)",
        category=ToolCategory.UTILITY.value,
        risk_level=RiskLevel.READ_ONLY.value,
        parameters={},
        is_async=False,
    )

    # Register list_tools tool
    tool_catalog.register(
        tool_id=ToolId.LIST_TOOLS.value,
        func=list_tools,
        description="List all available tools and their capabilities",
        category=ToolCategory.INTROSPECTION.value,
        risk_level=RiskLevel.READ_ONLY.value,
        parameters={},
        is_async=False,
    )

    registered_ids = [
        ToolId.WEB_SEARCH.value,
        ToolId.GET_TIME.value,
        ToolId.LIST_TOOLS.value,
    ]

    logger.info(
        "hello_world_tools_registered",
        count=len(registered_ids),
        tools=registered_ids,
    )

    return {
        "count": len(registered_ids),
        "registered": registered_ids,
    }


__all__ = ["register_all_tools"]
