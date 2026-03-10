"""Capability Registration for Hello World Chatbot.

Registers hello-world as a capability with jeeves-core via one-call
register_capability(). SQLite-backed in-dialogue memory is created lazily
in ChatbotService.

Usage:
    from jeeves_capability_hello_world.capability.wiring import register_capability
    register_capability()

    from jeeves_core.bootstrap import create_app_context
    from jeeves_capability_hello_world.capability.wiring import create_hello_world_from_app_context
    app_context = create_app_context()
    service = create_hello_world_from_app_context(app_context)
"""

import logging
import os
from pathlib import Path
from typing import Any, TYPE_CHECKING

from jeeves_core.protocols import (
    DomainModeConfig,
    DomainServiceConfig,
    DomainAgentConfig,
    CapabilityToolsConfig,
    CapabilityOrchestratorConfig,
    CapabilityToolCatalog,
    AgentLLMConfig,
)
from jeeves_core.capability_wiring import register_capability as _register

if TYPE_CHECKING:
    from jeeves_core.context import AppContext

logger = logging.getLogger(__name__)

# =============================================================================
# CAPABILITY CONSTANTS
# =============================================================================

CAPABILITY_ID = "hello_world"
CAPABILITY_VERSION = "0.0.1"
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
    "think_knowledge": AgentLLMConfig(
        agent_name="think_knowledge",
        model="",
        temperature=0.0,
        max_tokens=0,
        context_window=0,
        timeout_seconds=60,
    ),
    "think_tools": AgentLLMConfig(
        agent_name="think_tools",
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
        description="Classifies user intent for targeted knowledge retrieval",
        layer="perception",
        tools=[],
    ),
    DomainAgentConfig(
        name="think_knowledge",
        description="Retrieves targeted knowledge sections (no LLM, no tools)",
        layer="execution",
        tools=[],
    ),
    DomainAgentConfig(
        name="think_tools",
        description="Executes tools based on classified intent",
        layer="execution",
        tools=["get_time", "list_tools"],
    ),
    DomainAgentConfig(
        name="respond",
        description="Synthesizes response with optional loop-back routing",
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
# FACTORY FUNCTIONS
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
        risk_semantic="read_only",
        risk_severity="low",
    )

    catalog.register(
        tool_id="list_tools",
        func=list_tools,
        description="List available tools and onboarding capabilities",
        parameters={},
        category="standalone",
        risk_semantic="read_only",
        risk_severity="low",
    )

    return catalog


def _create_orchestrator_service(
    llm_factory,
    tool_executor,
    log,
    persistence,
    kernel_client,
):
    """Factory: creates ChatbotService for kernel dispatch."""
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
# ONE-CALL REGISTRATION
# =============================================================================

def register_capability() -> None:
    """Register hello-world capability with jeeves-core.

    Creates the capability-owned SQLiteClient for in-dialogue memory.
    """
    global _capability_db
    from jeeves_capability_hello_world.database.sqlite_client import SQLiteClient
    _capability_db = SQLiteClient()

    _register(
        capability_id=CAPABILITY_ID,
        service_config=DomainServiceConfig(
            service_id=f"{CAPABILITY_ID}_service",
            service_type="flow",
            capabilities=["query", "chat", "general"],
            max_concurrent=10,
            is_default=True,
            is_readonly=True,
            requires_confirmation=False,
            default_session_title="Chat Session",
            pipeline_stages=["understand", "think_knowledge", "think_tools", "respond"],
        ),
        mode_config=DomainModeConfig(
            mode_id=CAPABILITY_ID,
            response_fields=["response", "citations", "confidence"],
            requires_repo_path=False,
        ),
        agents=AGENT_DEFINITIONS,
        tools_config=CapabilityToolsConfig(
            tool_ids=["get_time", "list_tools"],
            initializer=_create_tool_catalog,
        ),
        orchestrator_config=CapabilityOrchestratorConfig(
            factory=_create_orchestrator_service,
        ),
        agent_llm_configs=AGENT_LLM_CONFIGS,
    )

    logger.info(
        "hello_world_capability_registered",
        extra={
            "capability_id": CAPABILITY_ID,
            "version": CAPABILITY_VERSION,
        }
    )


# =============================================================================
# APP CONTEXT HELPER
# =============================================================================

def create_hello_world_from_app_context(app_context: "AppContext") -> Any:
    """Create ChatbotService from jeeves_core AppContext.

    Wires app_context.db from capability-owned SQLiteClient if not already set.
    """
    from jeeves_core.wiring import create_tool_executor
    from jeeves_capability_hello_world.orchestration.chatbot_service import ChatbotService
    from jeeves_capability_hello_world.pipeline_config import ONBOARDING_CHATBOT_PIPELINE

    if app_context.db is None:
        if _capability_db is None:
            raise RuntimeError("No database client available. Call register_capability() first.")
        app_context.db = _capability_db

    from jeeves_core.protocols import get_capability_resource_registry
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
    """Get the capability-owned database client."""
    return _capability_db


__all__ = [
    "register_capability",
    "get_capability_db",
    "CAPABILITY_ID",
    "CAPABILITY_VERSION",
    "AGENT_LLM_CONFIGS",
    "AGENT_DEFINITIONS",
    "ToolRegistryAdapter",
    "create_hello_world_from_app_context",
]
