"""
Orchestration Wiring for Hello World Capability.

Constitution R7 compliant dependency injection.
Factory functions create service instances with all dependencies injected.

Architecture:
    Apps should use the capability layer entry point:
        from jeeves_capability_hello_world.capability.wiring import (
            register_capability,
            create_hello_world_from_app_context,
        )

    This module provides create_hello_world_service() as an explicit-params
    factory for tests and the framework orchestrator path.

See Also:
    - capability/wiring.py: Full capability registration and AppContext-based factory
"""

from typing import Any, Callable, Optional, TYPE_CHECKING
import structlog

from jeeves_capability_hello_world.orchestration.chatbot_service import ChatbotService

if TYPE_CHECKING:
    from jeeves_infra.kernel_client import KernelClient
    from jeeves_infra.protocols import CapabilityToolCatalog

from jeeves_capability_hello_world.pipeline_config import ONBOARDING_CHATBOT_PIPELINE
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
        from jeeves_infra.wiring import create_tool_executor

        service = create_hello_world_service(
            llm_provider_factory=app_context.llm_provider_factory,
            tool_executor=tool_executor,
            kernel_client=app_context.kernel_client,
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


__all__ = [
    "create_hello_world_service",
    "get_capability_tool_catalog",
    "CAPABILITY_ID",
]
