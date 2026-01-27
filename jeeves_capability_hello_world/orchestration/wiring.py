"""
Orchestration Wiring for Hello World Capability.

Constitution R7 compliant dependency injection.
Factory functions create service instances with all dependencies injected.

Architecture:
    Apps use create_hello_world_service() instead of constructing services directly.
    This centralizes wiring logic and makes dependencies explicit.
"""

from typing import Any, Callable, Optional
import structlog

from jeeves_capability_hello_world.orchestration.chatbot_service import ChatbotService
from jeeves_capability_hello_world.pipeline_config import GENERAL_CHATBOT_PIPELINE
from jeeves_capability_hello_world.tools import initialize_all_tools, tool_catalog


def get_logger() -> Any:
    """Get logger for wiring module."""
    return structlog.get_logger("orchestration.wiring")


def create_hello_world_service(
    *,
    llm_provider_factory: Callable,
    tool_executor: Any,
    logger: Optional[Any] = None,
    persistence: Optional[Any] = None,
    control_tower: Optional[Any] = None,
    use_mock: bool = False,
) -> ChatbotService:
    """
    Create Hello World chatbot service with dependency injection.

    Factory function that creates a fully configured ChatbotService.
    All dependencies are explicitly passed, no global state access.

    Args:
        llm_provider_factory: Factory function to create LLM providers
        tool_executor: Tool executor instance
        logger: Optional logger (creates one if None)
        persistence: Optional persistence adapter (not used by hello-world)
        control_tower: Optional Control Tower for event tracking
        use_mock: Whether to use mock LLM (for testing)

    Returns:
        Configured ChatbotService instance

    Example:
        from mission_system.adapters import (
            create_llm_provider_factory,
            create_tool_executor,
            get_settings,
        )
        from jeeves_capability_hello_world.orchestration.wiring import (
            create_hello_world_service,
        )

        settings = get_settings()
        llm_factory = create_llm_provider_factory(settings)
        tool_executor = create_tool_executor(tool_registry)

        service = create_hello_world_service(
            llm_provider_factory=llm_factory,
            tool_executor=tool_executor,
        )
    """
    if logger is None:
        logger = get_logger()

    logger.info(
        "creating_hello_world_service",
        use_mock=use_mock,
        has_control_tower=control_tower is not None,
    )

    service = ChatbotService(
        llm_provider_factory=llm_provider_factory,
        tool_executor=tool_executor,
        logger=logger,
        pipeline_config=GENERAL_CHATBOT_PIPELINE,
        use_mock=use_mock,
    )

    logger.info(
        "hello_world_service_created",
        pipeline="general_chatbot",
        agents=3,
    )

    return service


def create_tool_registry_adapter() -> Any:
    """
    Create a tool registry adapter from the tool catalog.

    Adapts the capability's tool_catalog to the ToolRegistryProtocol
    expected by ToolExecutor.

    Returns:
        Tool registry adapter implementing has_tool() and get_tool()
    """

    class ToolRegistryAdapter:
        """Adapter from tool_catalog to ToolRegistryProtocol."""

        def __init__(self, catalog):
            self._catalog = catalog

        def has_tool(self, name: str) -> bool:
            """Check if tool exists."""
            return self._catalog.has_tool(name)

        def get_tool(self, name: str) -> Optional[Any]:
            """Get tool by name."""
            tool_info = self._catalog.get_tool(name)
            if tool_info:
                return tool_info
            return None

    return ToolRegistryAdapter(tool_catalog)


def create_wiring(
    settings: Any,
    logger: Optional[Any] = None,
) -> dict:
    """
    Create complete wiring for Hello World capability.

    Convenience function that creates all required components
    and returns them as a dict ready for service creation.

    Args:
        settings: Settings instance (from mission_system.adapters.get_settings)
        logger: Optional logger instance

    Returns:
        Dict with wiring components:
        - llm_provider_factory: LLM factory function
        - tool_executor: Tool executor instance
        - tool_registry: Tool registry adapter
        - logger: Logger instance

    Example:
        from mission_system.adapters import get_settings
        from jeeves_capability_hello_world.orchestration.wiring import (
            create_wiring,
            create_hello_world_service,
        )

        settings = get_settings()
        wiring = create_wiring(settings)
        service = create_hello_world_service(**wiring)
    """
    if logger is None:
        logger = get_logger()

    # Import adapters (Constitution R7: use adapters, not direct avionics)
    from mission_system.adapters import (
        create_llm_provider_factory,
        create_tool_executor,
    )

    logger.info("creating_hello_world_wiring")

    # Initialize tools
    initialize_all_tools(logger=logger)

    # Create tool registry adapter
    tool_registry = create_tool_registry_adapter()

    # Create LLM provider factory
    llm_provider_factory = create_llm_provider_factory(settings)

    # Create tool executor
    tool_executor = create_tool_executor(tool_registry)

    logger.info("hello_world_wiring_created")

    return {
        "llm_provider_factory": llm_provider_factory,
        "tool_executor": tool_executor,
        "logger": logger,
    }


__all__ = [
    "create_hello_world_service",
    "create_tool_registry_adapter",
    "create_wiring",
]
