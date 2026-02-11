"""Capability Registration for Hello World Chatbot.

Registers hello-world as a capability with jeeves-infra.
Tools, agents, and orchestrator are registered here.
SQLite-backed in-dialogue memory is created lazily in ChatbotService.

Usage:
    from jeeves_capability_hello_world.capability.wiring import register_capability
    register_capability()

    from jeeves_infra.bootstrap import create_app_context
    app_context = create_app_context()

    from jeeves_capability_hello_world.capability.wiring import create_hello_world_from_app_context
    service = create_hello_world_from_app_context(app_context)
"""

import logging
import os
from pathlib import Path
from typing import Any, Callable, Optional, TYPE_CHECKING

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
    from jeeves_infra.context import AppContext

logger = logging.getLogger(__name__)

# =============================================================================
# CAPABILITY CONSTANTS
# =============================================================================

CAPABILITY_ID = "hello_world"
CAPABILITY_VERSION = "0.3.0"
CAPABILITY_ROOT = Path(__file__).resolve().parent.parent

# Capability-owned database client — created in register_capability()
_capability_db = None


# =============================================================================
# AGENT LLM CONFIGURATIONS
# =============================================================================

AGENT_LLM_CONFIGS = {
    "understand": AgentLLMConfig(
        agent_name="understand",
        model=os.getenv("JEEVES_LLM_UNDERSTAND_MODEL", "gpt-4o-mini"),
        temperature=0.1,
        max_tokens=1000,
        context_window=8192,
        timeout_seconds=30,
    ),
    "think": AgentLLMConfig(
        agent_name="think",
        model="",
        temperature=0.0,
        max_tokens=0,
        context_window=0,
        timeout_seconds=60,
    ),
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
        description="Analyzes user intent for onboarding questions",
        layer="perception",
        tools=[],
    ),
    DomainAgentConfig(
        name="think",
        description="Executes tools based on analyzed intent",
        layer="execution",
        tools=["get_time", "list_tools"],
    ),
    DomainAgentConfig(
        name="respond",
        description="Synthesizes onboarding response from embedded knowledge",
        layer="synthesis",
        tools=[],
    ),
]


# =============================================================================
# TOOL REGISTRY ADAPTER
# =============================================================================

class ToolRegistryAdapter:
    """Adapter from CapabilityToolCatalog to ToolRegistryProtocol."""

    def __init__(self, catalog: "CapabilityToolCatalog"):
        self._catalog = catalog

    def has_tool(self, name: str) -> bool:
        return self._catalog.has_tool(name)

    def get_tool(self, name: str):
        return self._catalog.get_tool(name)


# =============================================================================
# TOOL CATALOG
# =============================================================================

def _create_tool_catalog() -> CapabilityToolCatalog:
    """Create and populate the tool catalog for hello-world."""
    from jeeves_capability_hello_world.tools.hello_world_tools import (
        get_time,
        list_tools,
    )

    catalog = CapabilityToolCatalog(CAPABILITY_ID)

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

    catalog.register(
        tool_id="list_tools",
        func=list_tools,
        description="List available tools and onboarding capabilities",
        parameters={},
        category="standalone",
        risk_level="read_only",
    )

    return catalog


# =============================================================================
# ORCHESTRATOR FACTORY (called by infra framework)
# =============================================================================

def _create_orchestrator_service(
    llm_factory: Callable,
    tool_executor: Any,
    log: Any,
    persistence: Optional[Any],
    kernel_client: Any,
) -> Any:
    """Factory to create ChatbotService for framework dispatch."""
    from jeeves_capability_hello_world.orchestration.chatbot_service import ChatbotService
    from jeeves_capability_hello_world.pipeline_config import ONBOARDING_CHATBOT_PIPELINE

    db = persistence or _capability_db
    if db is None:
        raise RuntimeError("No database client available. Call register_capability() first.")

    return ChatbotService(
        llm_provider_factory=llm_factory,
        tool_executor=tool_executor,
        logger=log,
        pipeline_config=ONBOARDING_CHATBOT_PIPELINE,
        kernel_client=kernel_client,
        db=db,
    )


# =============================================================================
# CAPABILITY REGISTRATION
# =============================================================================

def register_capability() -> None:
    """Register hello-world capability with jeeves-core.

    Must be called at startup before using runtime services.
    Creates the capability-owned SQLiteClient for in-dialogue memory.
    """
    global _capability_db
    from jeeves_capability_hello_world.database.sqlite_client import SQLiteClient
    _capability_db = SQLiteClient()

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
            is_readonly=True,
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
            tool_ids=["get_time", "list_tools"],
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

    # 6. Register LLM configurations
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
        pass

    logger.info(
        "hello_world_capability_registered",
        extra={
            "capability_id": CAPABILITY_ID,
            "version": CAPABILITY_VERSION,
            "agents": [a.name for a in AGENT_DEFINITIONS],
            "tools": ["get_time", "list_tools"],
        }
    )


# =============================================================================
# APP CONTEXT HELPER
# =============================================================================

def get_agent_config(agent_name: str) -> AgentLLMConfig:
    """Get LLM configuration for a specific agent."""
    if agent_name not in AGENT_LLM_CONFIGS:
        raise KeyError(f"Unknown agent: {agent_name}")
    return AGENT_LLM_CONFIGS[agent_name]


def create_hello_world_from_app_context(app_context: "AppContext") -> Any:
    """Create ChatbotService from jeeves_infra AppContext.

    Wires app_context.db from capability-owned SQLiteClient if not already set.
    Requires register_capability() to have been called first.
    """
    from jeeves_infra.wiring import create_tool_executor
    from jeeves_capability_hello_world.orchestration.chatbot_service import ChatbotService
    from jeeves_capability_hello_world.pipeline_config import ONBOARDING_CHATBOT_PIPELINE

    # Wire db from capability registration if not already on AppContext
    if app_context.db is None:
        if _capability_db is None:
            raise RuntimeError("No database client available. Call register_capability() first.")
        app_context.db = _capability_db

    # Get tool registry from capability registration
    registry = get_capability_resource_registry()
    tools_config = registry.get_tools(CAPABILITY_ID)
    tool_catalog = tools_config.get_catalog() if tools_config else _create_tool_catalog()

    tool_executor = create_tool_executor(ToolRegistryAdapter(tool_catalog))

    return ChatbotService(
        llm_provider_factory=app_context.llm_provider_factory,
        tool_executor=tool_executor,
        logger=app_context.logger,
        pipeline_config=ONBOARDING_CHATBOT_PIPELINE,
        kernel_client=app_context.kernel_client,
        db=app_context.db,
    )


def get_capability_db():
    """Get the capability-owned database client.

    Returns None if register_capability() hasn't been called yet.
    """
    return _capability_db


__all__ = [
    "register_capability",
    "get_agent_config",
    "get_capability_db",
    "CAPABILITY_ID",
    "CAPABILITY_VERSION",
    "AGENT_LLM_CONFIGS",
    "AGENT_DEFINITIONS",
    "ToolRegistryAdapter",
    "create_hello_world_from_app_context",
]
