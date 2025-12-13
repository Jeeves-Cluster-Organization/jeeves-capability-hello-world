"""
Wiring module for Code Analysis Service.

Provides factory functions for creating CodeAnalysisService instances
with proper dependency injection.

Constitutional Reference:
- Capability Constitution R7: Capability MUST register its resources at application startup
- Runtime Contract: Factory functions for service creation

See docs/JEEVES_CORE_RUNTIME_CONTRACT.md for the authoritative contract.
"""

from typing import Any, Optional

from jeeves_mission_system.contracts_core import (
    LoggerProtocol,
    PersistenceProtocol,
    ToolExecutorProtocol,
)
from jeeves_mission_system.adapters import get_logger


def create_code_analysis_service(
    *,
    runtime: Any,
    database_url: Optional[str] = None,
    control_tower: Optional[Any] = None,
) -> "CodeAnalysisService":
    """
    Factory function to create a CodeAnalysisService instance.

    This is the primary entry point for creating the code analysis service.
    It extracts the necessary dependencies from the runtime and creates
    the service with proper wiring.

    Args:
        runtime: MissionRuntime instance containing LLM factory, tool executor,
                 persistence, and settings
        database_url: Optional database URL for checkpointing
        control_tower: Optional Control Tower instance for resource tracking

    Returns:
        Configured CodeAnalysisService instance

    Example:
        ```python
        from orchestration.wiring import create_code_analysis_service
        from jeeves_mission_system.api import create_mission_runtime

        runtime = create_mission_runtime(
            tool_registry=tool_registry,
            persistence=db,
            settings=settings,
        )

        service = create_code_analysis_service(
            runtime=runtime,
            database_url=database_url,
        )
        ```
    """
    from orchestration.service import CodeAnalysisService

    logger = get_logger()

    # Extract dependencies from runtime
    llm_provider_factory = runtime.llm_provider_factory
    tool_executor = runtime.tool_executor
    persistence = runtime.persistence

    logger.info(
        "creating_code_analysis_service",
        has_llm_factory=llm_provider_factory is not None,
        has_tool_executor=tool_executor is not None,
        has_persistence=persistence is not None,
        has_control_tower=control_tower is not None,
    )

    return CodeAnalysisService(
        llm_provider_factory=llm_provider_factory,
        tool_executor=tool_executor,
        logger=logger,
        persistence=persistence,
        control_tower=control_tower,
    )


def create_code_analysis_service_from_components(
    *,
    llm_provider_factory: Any,
    tool_executor: ToolExecutorProtocol,
    logger: Optional[LoggerProtocol] = None,
    persistence: Optional[PersistenceProtocol] = None,
    control_tower: Optional[Any] = None,
    use_mock: bool = False,
) -> "CodeAnalysisService":
    """
    Factory function to create a CodeAnalysisService from individual components.

    Use this when you need fine-grained control over dependencies or for testing.

    Args:
        llm_provider_factory: Factory to create LLM providers per agent role
        tool_executor: Tool executor for agent tool calls
        logger: Optional logger instance (defaults to get_logger())
        persistence: Optional persistence for state storage
        control_tower: Optional Control Tower for resource tracking
        use_mock: Use mock handlers for testing

    Returns:
        Configured CodeAnalysisService instance
    """
    from orchestration.service import CodeAnalysisService

    if logger is None:
        logger = get_logger()

    return CodeAnalysisService(
        llm_provider_factory=llm_provider_factory,
        tool_executor=tool_executor,
        logger=logger,
        persistence=persistence,
        control_tower=control_tower,
        use_mock=use_mock,
    )


__all__ = [
    "create_code_analysis_service",
    "create_code_analysis_service_from_components",
]
