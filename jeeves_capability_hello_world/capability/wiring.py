"""Capability Registration for Hello World Chatbot.

This module registers hello-world as a capability with jeeves-infra.
All capability resources (tools, agents, services) are registered here.

Uses jeeves_infra.bootstrap for unified initialization (ADR-001).
Uses jeeves_infra.wiring for infrastructure access.

Constitutional Reference:
- CONTRACT.md: Capabilities MUST implement a registration function
- Capability Constitution R6: Domain Config Ownership

Usage:
    from jeeves_capability_hello_world.capability.wiring import register_capability

    # At application startup (before using runtime services)
    register_capability()

    # Create app context via jeeves_infra bootstrap (RECOMMENDED)
    from jeeves_infra.bootstrap import create_app_context
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
CAPABILITY_DESCRIPTION = "Onboarding chatbot for Jeeves ecosystem with 3-agent pipeline"
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
        description="Analyzes user intent for onboarding questions",
        layer="perception",
        tools=[],  # LLM-only
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
        get_time,
        list_tools,
    )

    catalog = CapabilityToolCatalog(CAPABILITY_ID)

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
        description="List available tools and onboarding capabilities",
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
        - jeeves_infra.orchestrator.EventOrchestrator for events
        - jeeves_infra.memory.services.SessionStateService for sessions
    """
    from jeeves_capability_hello_world.orchestration.chatbot_service import ChatbotService
    from jeeves_capability_hello_world.pipeline_config import ONBOARDING_CHATBOT_PIPELINE

    # Return ChatbotService directly - it properly wraps PipelineRunner
    # Session memory and events handled at API layer with framework components
    return ChatbotService(
        llm_provider_factory=llm_factory,
        tool_executor=tool_executor,
        logger=log,
        pipeline_config=ONBOARDING_CHATBOT_PIPELINE,
        kernel_client=kernel_client,
        use_mock=False,
    )


def _create_event_emitter(db: Any) -> Any:
    """Factory for EventEmitter."""
    from jeeves_capability_hello_world.memory.repositories.event_repository import EventRepository
    from jeeves_capability_hello_world.memory.services.event_emitter import EventEmitter
    return EventEmitter(EventRepository(db))


def _create_session_state_service(db: Any) -> Any:
    """Factory for SessionStateService."""
    from jeeves_capability_hello_world.memory.services.session_state_service import SessionStateService
    return SessionStateService(db=db)


def _create_graph_storage() -> Any:
    """Factory for InMemoryGraphStorage."""
    from jeeves_capability_hello_world.memory.repositories.graph_stub import InMemoryGraphStorage
    return InMemoryGraphStorage()


def _create_chunk_service(db: Any) -> Any:
    """Factory for ChunkService."""
    from jeeves_capability_hello_world.memory.services.chunk_service import ChunkService
    return ChunkService(db=db)


def _create_trace_recorder(db: Any) -> Any:
    """Factory for TraceRecorder."""
    from jeeves_capability_hello_world.memory.repositories.trace_repository import TraceRepository
    from jeeves_capability_hello_world.memory.services.trace_recorder import TraceRecorder
    return TraceRecorder(TraceRepository(db))


def _create_session_state_adapter(db: Any) -> Any:
    """Factory for SessionStateAdapter."""
    from jeeves_capability_hello_world.memory.services.session_state_adapter import SessionStateAdapter
    return SessionStateAdapter(db=db)


def register_capability() -> None:
    """Register hello-world capability with jeeves-core.

    This function must be called at startup before using runtime services.
    It registers all capability resources with the infrastructure.
    """
    registry = get_capability_resource_registry()

    # 0. Register database backend (BEFORE any DB operations)
    from jeeves_capability_hello_world.database.postgres.config import register_postgres_backend
    register_postgres_backend()

    # Register schemas via capability registry
    schema_dir = CAPABILITY_ROOT / "database" / "schemas"
    for schema_file in sorted(schema_dir.glob("*.sql")):
        registry.register_schema(CAPABILITY_ID, str(schema_file))

    # Register memory layer definitions (capability-owned)
    registry.register_memory_layers(CAPABILITY_ID, [
        {"layer_id": "L1", "name": "Canonical State Store",
         "description": "Single source of truth - tasks, journal_entries, sessions, messages",
         "backend": "relational", "tables": ["tasks", "journal_entries", "sessions", "messages", "kv_store"]},
        {"layer_id": "L2", "name": "Event Log & Trace Store",
         "description": "Immutable record of state changes and agent decisions",
         "backend": "relational", "tables": ["domain_events", "agent_traces"]},
        {"layer_id": "L3", "name": "Semantic Memory",
         "description": "Semantic search with vector embeddings",
         "backend": "vector", "tables": ["semantic_chunks"]},
        {"layer_id": "L4", "name": "Working Memory",
         "description": "Bounded context for conversations, open loops, flow interrupts",
         "backend": "relational", "tables": ["session_state", "open_loops", "flow_interrupts"]},
        {"layer_id": "L5", "name": "State Graph",
         "description": "Entity relationships and dependencies",
         "backend": "relational", "tables": ["graph_nodes", "graph_edges"]},
        {"layer_id": "L6", "name": "Skills & Patterns",
         "description": "Reusable workflow patterns (deferred to v3.x)",
         "backend": "none", "tables": []},
        {"layer_id": "L7", "name": "Meta-Memory & Governance",
         "description": "System behavior tracking, tool metrics, prompt versions",
         "backend": "relational", "tables": ["tool_metrics", "prompt_versions", "agent_evaluations"]},
    ])

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

    # 7. Register API router (chat endpoints)
    from jeeves_capability_hello_world.api.chat_router import (
        router as chat_router,
        get_chat_service,
        get_orchestrator,
    )

    def _create_chat_deps(db, event_manager, orchestrator, **kwargs):
        """Create DI overrides for chat router."""
        from jeeves_capability_hello_world.services.chat_service import ChatService
        svc = ChatService(db, event_manager)
        return {get_chat_service: lambda: svc, get_orchestrator: lambda: orchestrator}

    registry.register_api_router(
        CAPABILITY_ID,
        chat_router,
        deps_factory=_create_chat_deps,
        feature_flag="chat_enabled",
    )

    # 8. Register memory service factories
    registry.register_memory_service(CAPABILITY_ID, "event_emitter",
        lambda db, **kw: _create_event_emitter(db))
    registry.register_memory_service(CAPABILITY_ID, "session_state_service",
        lambda db, **kw: _create_session_state_service(db))
    registry.register_memory_service(CAPABILITY_ID, "graph_storage",
        lambda db, **kw: _create_graph_storage())
    registry.register_memory_service(CAPABILITY_ID, "chunk_service",
        lambda db, **kw: _create_chunk_service(db))
    registry.register_memory_service(CAPABILITY_ID, "trace_recorder",
        lambda db, **kw: _create_trace_recorder(db))
    registry.register_memory_service(CAPABILITY_ID, "session_state_adapter",
        lambda db, **kw: _create_session_state_adapter(db))

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
            "tools": ["get_time", "list_tools"],
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
# APP CONTEXT HELPERS (using jeeves_infra.bootstrap)
# =============================================================================


def create_hello_world_from_app_context(
    app_context: "AppContext",
) -> Any:
    """Create ChatbotService from jeeves_infra AppContext.

    This is the RECOMMENDED way to create the service.
    Uses jeeves_infra.bootstrap for unified configuration.

    Args:
        app_context: AppContext from jeeves_infra.bootstrap.create_app_context()

    Returns:
        Configured ChatbotService

    Note:
        For event handling, use framework's EventOrchestrator at API layer:
            from jeeves_infra.orchestrator import EventOrchestrator, create_event_context

    Example:
        from jeeves_infra.bootstrap import create_app_context
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
        from jeeves_infra.orchestrator import create_event_context
        event_context = create_event_context(request_context)
    """
    from jeeves_infra.wiring import (
        create_llm_provider_factory,
        create_tool_executor,
    )
    from jeeves_capability_hello_world.orchestration.chatbot_service import ChatbotService
    from jeeves_capability_hello_world.pipeline_config import ONBOARDING_CHATBOT_PIPELINE

    # Get tool registry from capability registration
    registry = get_capability_resource_registry()
    tools_config = registry.get_tools(CAPABILITY_ID)
    tool_catalog = tools_config.get_catalog() if tools_config else _create_tool_catalog()

    # Create adapters using jeeves_infra factories
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
        pipeline_config=ONBOARDING_CHATBOT_PIPELINE,
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
