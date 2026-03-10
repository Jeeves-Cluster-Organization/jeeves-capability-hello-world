"""Capability Registration for Hello World Chatbot.

Registers hello-world as a capability with jeeves-core via one-call
register_capability(). Uses service_class + pipeline_config for auto-wiring
and @tool decorators + from_decorated() for tool catalog.

Usage:
    from jeeves_capability_hello_world.capability.wiring import register_capability
    register_capability()

    # ChatbotService is auto-wired via service_class + pipeline_config.
    # Use jeeves_core.bootstrap.create_app_context() for runtime wiring.
"""

import logging
from pathlib import Path

from jeeves_core.protocols import (
    DomainModeConfig,
    DomainServiceConfig,
    DomainAgentConfig,
    CapabilityToolsConfig,
    CapabilityToolCatalog,
    AgentLLMConfig,
)
from jeeves_core.capability_wiring import register_capability as _register

logger = logging.getLogger(__name__)

# =============================================================================
# CAPABILITY CONSTANTS
# =============================================================================

CAPABILITY_ID = "hello_world"
_create_from_app_context = None  # Set by register_capability()
CAPABILITY_VERSION = "0.0.1"
CAPABILITY_ROOT = Path(__file__).resolve().parent.parent

# =============================================================================
# AGENT LLM CONFIGURATIONS
# =============================================================================

AGENT_LLM_CONFIGS = {
    "understand": AgentLLMConfig.from_env(
        "understand", temperature=0.1, max_tokens=1000, context_window=8192, timeout_seconds=30,
    ),
    "think_knowledge": AgentLLMConfig(
        agent_name="think_knowledge", model="", temperature=0.0,
        max_tokens=0, context_window=0, timeout_seconds=60,
    ),
    "think_tools": AgentLLMConfig(
        agent_name="think_tools", model="", temperature=0.0,
        max_tokens=0, context_window=0, timeout_seconds=60,
    ),
    "respond": AgentLLMConfig.from_env(
        "respond", temperature=0.7, max_tokens=2000, context_window=8192, timeout_seconds=60,
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
# TOOL CATALOG (from @tool decorators)
# =============================================================================


def _create_tool_catalog() -> CapabilityToolCatalog:
    """Build catalog from @tool-decorated functions."""
    from jeeves_capability_hello_world.tools import hello_world_tools

    return CapabilityToolCatalog.from_decorated(CAPABILITY_ID, hello_world_tools)


# =============================================================================
# ONE-CALL REGISTRATION
# =============================================================================


def register_capability() -> None:
    """Register hello-world capability with jeeves-core."""
    global _create_from_app_context
    from jeeves_capability_hello_world.orchestration.chatbot_service import ChatbotService
    from jeeves_capability_hello_world.pipeline_config import ONBOARDING_CHATBOT_PIPELINE
    from jeeves_capability_hello_world.database.sqlite_client import SQLiteClient

    db = SQLiteClient()

    _create_from_app_context = _register(
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
        agent_llm_configs=AGENT_LLM_CONFIGS,
        service_class=ChatbotService,
        pipeline_config=ONBOARDING_CHATBOT_PIPELINE,
        service_kwargs={"db": db},
    )

    logger.info(
        "hello_world_capability_registered",
        extra={
            "capability_id": CAPABILITY_ID,
            "version": CAPABILITY_VERSION,
        },
    )


def create_from_app_context(app_context):
    """Create ChatbotService from AppContext (for standalone apps like gradio_app)."""
    if _create_from_app_context is None:
        raise RuntimeError("Call register_capability() first")
    return _create_from_app_context(app_context)


__all__ = [
    "register_capability",
    "create_from_app_context",
    "CAPABILITY_ID",
    "CAPABILITY_VERSION",
    "CAPABILITY_ROOT",
    "AGENT_LLM_CONFIGS",
    "AGENT_DEFINITIONS",
]
