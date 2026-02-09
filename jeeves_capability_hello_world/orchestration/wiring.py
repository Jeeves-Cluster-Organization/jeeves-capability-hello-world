"""
Orchestration Wiring for Hello World Capability.

Constitution R7 compliant dependency injection.
Factory functions create service instances with all dependencies injected.

This module provides convenience wiring functions that wrap the capability
registration pattern from capability/wiring.py.

Architecture:
    Apps use create_hello_world_service() instead of constructing services directly.
    This centralizes wiring logic and makes dependencies explicit.

See Also:
    - capability/wiring.py: Full capability registration with jeeves_infra protocols
    - mission_system.capability_wiring: Standard capability registration entry point
"""

from typing import Any, Callable, Optional, TYPE_CHECKING
import structlog

from jeeves_capability_hello_world.orchestration.chatbot_service import ChatbotService

if TYPE_CHECKING:
    from jeeves_infra.kernel_client import KernelClient
    from jeeves_infra.protocols import CapabilityToolCatalog

from jeeves_capability_hello_world.pipeline_config import ONBOARDING_CHATBOT_PIPELINE
from jeeves_capability_hello_world.tools import initialize_all_tools, tool_catalog
from jeeves_capability_hello_world.capability.wiring import (
    CAPABILITY_ID,
    _create_tool_catalog,
)


def get_logger() -> Any:
    """Get logger for wiring module."""
    return structlog.get_logger("orchestration.wiring")


def create_hello_world_service(
    *,
    llm_provider_factory: Callable,
    tool_executor: Any,
    kernel_client: Optional["KernelClient"] = None,
    logger: Optional[Any] = None,
    use_mock: bool = False,
) -> ChatbotService:
    """
    Create Hello World chatbot service with dependency injection.

    Factory function that creates a fully configured ChatbotService.
    All dependencies are explicitly passed, no global state access.

    Args:
        llm_provider_factory: Factory function to create LLM providers
        tool_executor: Tool executor instance
        kernel_client: Optional KernelClient for resource tracking via Rust kernel
                      (None for standalone operation without resource tracking)
        logger: Optional logger (creates one if None)
        use_mock: Whether to use mock LLM (for testing)

    Returns:
        Configured ChatbotService instance

    Example:
        from mission_system.adapters import (
            create_llm_provider_factory,
            create_tool_executor,
            get_settings,
        )
        from jeeves_infra.kernel_client import get_kernel_client
        from jeeves_capability_hello_world.orchestration.wiring import (
            create_hello_world_service,
        )

        settings = get_settings()
        llm_factory = create_llm_provider_factory(settings)
        tool_executor = create_tool_executor(tool_registry)

        # With Rust kernel (production)
        kernel_client = await get_kernel_client()
        service = create_hello_world_service(
            llm_provider_factory=llm_factory,
            tool_executor=tool_executor,
            kernel_client=kernel_client,
        )

        # Standalone mode (no resource tracking)
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
        has_kernel_client=kernel_client is not None,
    )

    service = ChatbotService(
        llm_provider_factory=llm_provider_factory,
        tool_executor=tool_executor,
        logger=logger,
        pipeline_config=ONBOARDING_CHATBOT_PIPELINE,
        kernel_client=kernel_client,
        use_mock=use_mock,
    )

    logger.info(
        "hello_world_service_created",
        pipeline="general_chatbot",
        agents=3,
    )

    return service


def get_capability_tool_catalog() -> "CapabilityToolCatalog":
    """
    Get the CapabilityToolCatalog for hello-world.

    This follows the minisweagent pattern of using CapabilityToolCatalog
    from jeeves_infra.protocols for tool registration.

    Returns:
        CapabilityToolCatalog instance with all tools registered
    """
    return _create_tool_catalog()


def create_tool_registry_adapter(use_capability_catalog: bool = False) -> Any:
    """
    Create a tool registry adapter from the tool catalog.

    Adapts the capability's tool_catalog to the ToolRegistryProtocol
    expected by ToolExecutor.

    Args:
        use_capability_catalog: If True, use the new CapabilityToolCatalog
                               pattern from capability/wiring.py

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

    if use_capability_catalog:
        return ToolRegistryAdapter(get_capability_tool_catalog())
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
        - kernel_client: KernelClient instance (or None for standalone)
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

    # kernel_client is None for standalone mode
    # When running with Rust kernel, pass kernel_client from AppContext
    logger.info("hello_world_wiring_created", standalone_mode=True)

    return {
        "llm_provider_factory": llm_provider_factory,
        "tool_executor": tool_executor,
        "kernel_client": None,  # Set from AppContext when running with Rust kernel
        "logger": logger,
    }


__all__ = [
    "create_hello_world_service",
    "create_tool_registry_adapter",
    "create_wiring",
    "get_capability_tool_catalog",
    "CAPABILITY_ID",
]
