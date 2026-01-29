"""Capability Registration for Hello World Chatbot.

This module registers hello-world as a capability with jeeves-infra.
All capability resources (tools, agents, services) are registered here.

Uses mission_system.bootstrap for unified initialization (ADR-001).
Uses mission_system.adapters for infrastructure access.

Constitutional Reference:
- CONTRACT.md: Capabilities MUST implement a registration function
- Capability Constitution R6: Domain Config Ownership

Usage:
    from jeeves_capability_hello_world.capability.wiring import register_capability

    # At application startup (before using runtime services)
    register_capability()

    # Create app context via mission_system bootstrap (RECOMMENDED)
    from mission_system.bootstrap import create_app_context
    app_context = create_app_context()
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

# jeeves-airframe provides protocols and infrastructure
from jeeves_infra.protocols import (
    get_capability_resource_registry,
    DomainModeConfig,
    DomainServiceConfig,
    DomainAgentConfig,
    CapabilityToolsConfig,
    CapabilityOrchestratorConfig,
    CapabilityToolCatalog,
    AgentLLMConfig,
)

if TYPE_CHECKING:
    from jeeves_infra.protocols import CapabilityResourceRegistry
    from jeeves_infra.context import AppContext

logger = logging.getLogger(__name__)

# =============================================================================
# CAPABILITY CONSTANTS
# =============================================================================

CAPABILITY_ID = "hello_world"
CAPABILITY_DESCRIPTION = "General-purpose chatbot with 3-agent pipeline"
CAPABILITY_VERSION = "0.2.0"
CAPABILITY_ROOT = Path(__file__).resolve().parent.parent


# =============================================================================
# AGENT LLM CONFIGURATIONS
# =============================================================================

# Agent configurations for different roles in the pipeline
# These are registered with the capability registry for LLM provider lookup
AGENT_LLM_CONFIGS = {
    # Understand agent - analyzes user intent
    "understand": AgentLLMConfig(
        agent_name="understand",
        model=os.getenv("JEEVES_LLM_UNDERSTAND_MODEL", "gpt-4o-mini"),
        temperature=0.1,
        max_tokens=1000,
        context_window=8192,
        timeout_seconds=30,
    ),
    # Think agent - executes tools (no LLM needed, tool-only)
    "think": AgentLLMConfig(
        agent_name="think",
        model="",  # No model needed - tool execution only
        temperature=0.0,
        max_tokens=0,
        context_window=0,
        timeout_seconds=60,
    ),
    # Respond agent - generates final response
    "respond": AgentLLMConfig(
        agent_name="respond",
        model=os.getenv("JEEVES_LLM_RESPOND_MODEL", "gpt-4o-mini"),
        temperature=0.7,
        max_tokens=2000,
        context_window=8192,
        timeout_seconds=60,
    ),
}


# =============================================================================
# AGENT DEFINITIONS
# =============================================================================

AGENT_DEFINITIONS = [
    DomainAgentConfig(
        name="understand",
        description="Analyzes user intent and plans approach",
        layer="perception",
        tools=[],  # LLM-only
    ),
    DomainAgentConfig(
        name="think",
        description="Executes tools based on analyzed intent",
        layer="execution",
        tools=["web_search", "get_time", "list_tools"],
    ),
    DomainAgentConfig(
        name="respond",
        description="Synthesizes final response from gathered information",
        layer="synthesis",
        tools=[],  # LLM-only
    ),
]


# =============================================================================
# REGISTRATION FUNCTIONS
# =============================================================================

def _create_tool_catalog() -> CapabilityToolCatalog:
    """Create and populate the tool catalog for hello-world.

    Returns the tool catalog with all hello-world tools registered.
    This avoids circular imports and allows lazy loading.
    """
    from jeeves_capability_hello_world.tools.hello_world_tools import (
        web_search,
        get_time,
        list_tools,
    )

    catalog = CapabilityToolCatalog(CAPABILITY_ID)

    # Register web_search tool
    catalog.register(
        tool_id="web_search",
        func=web_search,
        description="Search the web for current information",
        parameters={
            "query": "string - The search query",
            "max_results": "integer? - Maximum results to return (default: 5)",
        },
        category="standalone",
        risk_level="read_only",
    )

    # Register get_time tool
    catalog.register(
        tool_id="get_time",
        func=get_time,
        description="Get current date and time",
        parameters={
            "timezone": "string? - Timezone (default: UTC)",
            "format": "string? - Output format (default: iso)",
        },
        category="standalone",
        risk_level="read_only",
    )

    # Register list_tools tool
    catalog.register(
        tool_id="list_tools",
        func=list_tools,
        description="List available tools with their descriptions",
        parameters={},
        category="standalone",
        risk_level="read_only",
    )

    return catalog


def _create_orchestrator_service(
    llm_factory: Callable,
    tool_executor: Any,
    log: Any,
    persistence: Optional[Any],
    kernel_client: Any,
) -> Any:
    """Factory function to create the orchestrator service.

    Called by infrastructure to create the service that handles requests.
    Returns ChatbotService directly - the framework's EventOrchestrator
    should be used at the API layer for event handling.

    Args:
        llm_factory: Factory for LLM providers
        tool_executor: Tool executor instance
        log: Logger instance
        persistence: Persistence adapter (optional)
        kernel_client: KernelClient instance for resource tracking

    Returns:
        ChatbotService instance (proper adapter over PipelineRunner)

    Note:
        For session memory and event streaming, use framework components:
        - mission_system.orchestrator.EventOrchestrator for events
        - jeeves_infra.memory.services.SessionStateService for sessions
    """
    from jeeves_capability_hello_world.orchestration.chatbot_service import ChatbotService
    from jeeves_capability_hello_world.pipeline_config import GENERAL_CHATBOT_PIPELINE

    # Return ChatbotService directly - it properly wraps PipelineRunner
    # Session memory and events handled at API layer with framework components
    return ChatbotService(
        llm_provider_factory=llm_factory,
        tool_executor=tool_executor,
        logger=log,
        pipeline_config=GENERAL_CHATBOT_PIPELINE,
        kernel_client=kernel_client,
        use_mock=False,
    )


def register_capability() -> None:
    """Register hello-world capability with jeeves-core.

    This function must be called at startup before using runtime services.
    It registers all capability resources with the infrastructure.
    """
    registry = get_capability_resource_registry()

    # 1. Register capability mode
    registry.register_mode(
        CAPABILITY_ID,
        DomainModeConfig(
            mode_id=CAPABILITY_ID,
            response_fields=["response", "citations", "confidence"],
            requires_repo_path=False,
        ),
    )

    # 2. Register service configuration
    registry.register_service(
        CAPABILITY_ID,
        DomainServiceConfig(
            service_id=f"{CAPABILITY_ID}_service",
            service_type="flow",
            capabilities=["query", "chat", "general"],
            max_concurrent=10,
            is_default=True,
            is_readonly=True,  # Hello-world doesn't modify anything
            requires_confirmation=False,
            default_session_title="Chat Session",
            pipeline_stages=["understand", "think", "respond"],
        ),
    )

    # 3. Register agent definitions
    registry.register_agents(CAPABILITY_ID, AGENT_DEFINITIONS)

    # 4. Register tools configuration (lazy initialization)
    registry.register_tools(
        CAPABILITY_ID,
        CapabilityToolsConfig(
            tool_ids=["web_search", "get_time", "list_tools"],
            initializer=_create_tool_catalog,
        ),
    )

    # 5. Register orchestrator factory
    registry.register_orchestrator(
        CAPABILITY_ID,
        CapabilityOrchestratorConfig(
            factory=_create_orchestrator_service,
        ),
    )

    # 6. Register LLM configurations with capability registry
    try:
        from jeeves_infra.capability_registry import get_capability_registry

        llm_registry = get_capability_registry()
        for agent_name, config in AGENT_LLM_CONFIGS.items():
            llm_registry.register(
                capability_id=CAPABILITY_ID,
                agent_name=agent_name,
                config=config,
            )
    except ImportError:
        # jeeves_infra not available - running standalone
        pass

    logger.info(
        "hello_world_capability_registered",
        extra={
            "capability_id": CAPABILITY_ID,
            "version": CAPABILITY_VERSION,
            "agents": [a.name for a in AGENT_DEFINITIONS],
            "tools": ["web_search", "get_time", "list_tools"],
        }
    )


def get_agent_config(agent_name: str) -> AgentLLMConfig:
    """Get LLM configuration for a specific agent.

    Args:
        agent_name: Name of the agent

    Returns:
        AgentLLMConfig for the agent

    Raises:
        KeyError: If agent not found
    """
    if agent_name not in AGENT_LLM_CONFIGS:
        raise KeyError(f"Unknown agent: {agent_name}")
    return AGENT_LLM_CONFIGS[agent_name]


# =============================================================================
# APP CONTEXT HELPERS (using mission_system.bootstrap)
# =============================================================================


def create_hello_world_from_app_context(
    app_context: "AppContext",
) -> Any:
    """Create ChatbotService from mission_system AppContext.

    This is the RECOMMENDED way to create the service.
    Uses mission_system.bootstrap for unified configuration.

    Args:
        app_context: AppContext from mission_system.bootstrap.create_app_context()

    Returns:
        Configured ChatbotService

    Note:
        For event handling, use framework's EventOrchestrator at API layer:
            from mission_system.orchestrator import EventOrchestrator, create_event_context

    Example:
        from mission_system.bootstrap import create_app_context
        from jeeves_capability_hello_world.capability.wiring import (
            register_capability,
            create_hello_world_from_app_context,
        )

        # Register capability first
        register_capability()

        # Create app context
        app_context = create_app_context()

        # Create service
        service = create_hello_world_from_app_context(app_context)

        # Use with framework's event orchestrator at API layer
        from mission_system.orchestrator import create_event_context
        event_context = create_event_context(request_context)
    """
    from mission_system.adapters import (
        create_llm_provider_factory,
        create_tool_executor,
    )
    from jeeves_capability_hello_world.orchestration.chatbot_service import ChatbotService
    from jeeves_capability_hello_world.pipeline_config import GENERAL_CHATBOT_PIPELINE

    # Get tool registry from capability registration
    registry = get_capability_resource_registry()
    tools_config = registry.get_tools(CAPABILITY_ID)
    tool_catalog = tools_config.get_catalog() if tools_config else _create_tool_catalog()

    # Create adapters using mission_system factories
    llm_factory = create_llm_provider_factory(app_context.settings)

    # Create tool executor adapter
    class ToolRegistryAdapter:
        def __init__(self, catalog):
            self._catalog = catalog

        def has_tool(self, name: str) -> bool:
            return self._catalog.has_tool(name)

        def get_tool(self, name: str):
            return self._catalog.get_tool(name)

    tool_executor = create_tool_executor(ToolRegistryAdapter(tool_catalog))

    # Get kernel_client from context for resource tracking
    kernel_client = getattr(app_context, 'kernel_client', None)

    # Return ChatbotService directly - proper adapter over PipelineRunner
    return ChatbotService(
        llm_provider_factory=llm_factory,
        tool_executor=tool_executor,
        logger=app_context.logger,
        pipeline_config=GENERAL_CHATBOT_PIPELINE,
        kernel_client=kernel_client,
        use_mock=False,
    )


__all__ = [
    # Registration
    "register_capability",
    "get_agent_config",
    # Constants
    "CAPABILITY_ID",
    "CAPABILITY_VERSION",
    "CAPABILITY_ROOT",
    "AGENT_LLM_CONFIGS",
    "AGENT_DEFINITIONS",
    # Tool catalog
    "_create_tool_catalog",
    # Service factory (returns ChatbotService, use framework EventOrchestrator for events)
    "create_hello_world_from_app_context",
]
