"""
Tool Registration for Onboarding Capability.

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
    Register all Onboarding tools with the catalog.

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
        get_time,
        list_tools,
    )

    logger.info("registering_onboarding_tools")

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
        description="List all available tools and onboarding capabilities",
        category=ToolCategory.INTROSPECTION.value,
        risk_level=RiskLevel.READ_ONLY.value,
        parameters={},
        is_async=False,
    )

    registered_ids = [
        ToolId.GET_TIME.value,
        ToolId.LIST_TOOLS.value,
    ]

    logger.info(
        "onboarding_tools_registered",
        count=len(registered_ids),
        tools=registered_ids,
    )

    return {
        "count": len(registered_ids),
        "registered": registered_ids,
    }


__all__ = ["register_all_tools"]
