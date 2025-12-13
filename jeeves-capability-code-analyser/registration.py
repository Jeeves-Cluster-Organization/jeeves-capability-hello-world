"""Capability Registration for Code Analysis.

Constitutional Reference:
- Avionics R3: No Domain Logic - infrastructure provides transport, not business logic
- Mission System Constitution: Domain configs OWNED by capabilities
- Capability Constitution R7: Capability MUST register its resources at application startup

See docs/JEEVES_CORE_RUNTIME_CONTRACT.md for the authoritative runtime contract.

This module registers the code_analysis capability resources at startup.
Infrastructure queries these registrations instead of having hardcoded knowledge.

Layer Extraction Compliant:
- Registers ALL capability resources with the CapabilityResourceRegistry
- Infrastructure has zero hardcoded knowledge of this capability
- Capability can be extracted to separate repository as a package

Usage:
    # At application startup (before avionics initialization)
    from jeeves_capability_code_analyser.registration import register_capability

    register_capability()
"""

from pathlib import Path
from typing import Any, Dict

from jeeves_protocols import (
    CapabilityServiceConfig,
    CapabilityModeConfig,
    CapabilityOrchestratorConfig,
    CapabilityToolsConfig,
    CapabilityAgentConfig,
    CapabilityContractsConfig,
    get_capability_resource_registry,
)


# Capability identifier
CAPABILITY_ID = "code_analysis"

# Path to capability root (relative to this file)
CAPABILITY_ROOT = Path(__file__).parent


def _create_orchestrator_factory():
    """Create the orchestrator factory function.

    Returns a factory that creates CodeAnalysisService instances.
    This defers the import to avoid circular dependencies.
    """
    def factory(
        llm_provider_factory,
        tool_executor,
        logger,
        persistence,
        control_tower,
    ):
        from orchestration.service import CodeAnalysisService
        return CodeAnalysisService(
            llm_provider_factory=llm_provider_factory,
            tool_executor=tool_executor,
            logger=logger,
            persistence=persistence,
            control_tower=control_tower,
        )
    return factory


def _create_tools_initializer():
    """Create the tools initializer function.

    Returns a function that initializes all code analysis tools.
    This defers the import to avoid circular dependencies.
    """
    def initializer(db) -> Dict[str, Any]:
        from tools import initialize_all_tools
        return initialize_all_tools(db=db)
    return initializer


def _get_agent_definitions():
    """Get the agent definitions for the code analysis pipeline.

    Returns list of CapabilityAgentConfig for all 7 agents.
    """
    return [
        CapabilityAgentConfig(
            name="CodeAnalysisPerceptionAgent",
            description="Loads session context, normalizes query",
            layer="perception",
            tools=[],
        ),
        CapabilityAgentConfig(
            name="CodeAnalysisIntentAgent",
            description="Classifies query type, extracts goals",
            layer="perception",
            tools=[],
        ),
        CapabilityAgentConfig(
            name="CodeAnalysisPlannerAgent",
            description="Creates tool execution plan for code analysis",
            layer="planning",
            tools=[],
        ),
        CapabilityAgentConfig(
            name="CodeTraverserAgent",
            description="Executes read-only code operations using resilient ops",
            layer="execution",
            tools=["read_code", "find_code", "find_related", "glob_files", "grep_search"],
        ),
        CapabilityAgentConfig(
            name="SynthesizerAgent",
            description="Synthesizes findings from traversal",
            layer="synthesis",
            tools=[],
        ),
        CapabilityAgentConfig(
            name="CodeAnalysisCriticAgent",
            description="Validates results, checks for evidence",
            layer="validation",
            tools=[],
        ),
        CapabilityAgentConfig(
            name="CodeAnalysisIntegrationAgent",
            description="Builds final response with citations",
            layer="integration",
            tools=[],
        ),
    ]


def register_capability() -> None:
    """Register code_analysis capability resources with infrastructure.

    Registers:
    - Database schema: 002_code_analysis_schema.sql
    - Gateway mode: "code_analysis" with response field configuration
    - Service: "code_analysis" for Control Tower registration
    - Orchestrator: Factory function for CodeAnalysisService
    - Tools: Initializer function for all code analysis tools
    - Agents: Agent definitions for governance reporting
    - Prompts: Code analysis pipeline prompts
    - Contracts: Tool result contracts and validation

    This function should be called at application startup, before
    avionics/infrastructure initialization.
    """
    registry = get_capability_resource_registry()

    # Register database schema
    # Path is relative to capability root for portability
    schema_path = str(CAPABILITY_ROOT / "database" / "schemas" / "002_code_analysis_schema.sql")
    registry.register_schema(CAPABILITY_ID, schema_path)

    # Register gateway mode configuration
    mode_config = CapabilityModeConfig(
        mode_id=CAPABILITY_ID,
        response_fields=[
            "files_examined",
            "citations",
            "thread_id",
        ],
        requires_repo_path=False,  # Optional but useful
    )
    registry.register_mode(CAPABILITY_ID, mode_config)

    # Register service configuration for Control Tower
    service_config = CapabilityServiceConfig(
        service_id=CAPABILITY_ID,
        service_type="flow",
        capabilities=["analyze_code", "clarification"],
        max_concurrent=10,
        is_default=True,  # This is the primary service
    )
    registry.register_service(CAPABILITY_ID, service_config)

    # Register orchestrator factory (Layer Extraction Support)
    orchestrator_config = CapabilityOrchestratorConfig(
        factory=_create_orchestrator_factory(),
        result_type=None,  # Will be set lazily if needed
    )
    registry.register_orchestrator(CAPABILITY_ID, orchestrator_config)

    # Register tools initializer (Layer Extraction Support)
    tools_config = CapabilityToolsConfig(
        initializer=_create_tools_initializer(),
        tool_ids=[
            "read_code", "find_code", "find_related", "glob_files",
            "grep_search", "semantic_search", "tree_structure",
            "find_symbol", "get_file_symbols", "explore_symbol_usage",
            "map_module", "locate", "trace_entry_point",
        ],
    )
    registry.register_tools(CAPABILITY_ID, tools_config)

    # Register agent definitions (Layer Extraction Support)
    registry.register_agents(CAPABILITY_ID, _get_agent_definitions())

    # Register prompts (Layer Extraction Support)
    # Import and register prompts from the prompts module
    try:
        from prompts.code_analysis import register_code_analysis_prompts
        register_code_analysis_prompts()
    except ImportError:
        # Prompts module not available - skip
        pass

    # Register contracts (Layer Extraction Support)
    try:
        from contracts import (
            TOOL_RESULT_SCHEMAS,
            validate_tool_result,
        )
        contracts_config = CapabilityContractsConfig(
            schemas=TOOL_RESULT_SCHEMAS,
            validators={"validate": validate_tool_result},
        )
        registry.register_contracts(CAPABILITY_ID, contracts_config)
    except ImportError:
        # Contracts module not available - skip
        pass


def get_schema_path() -> str:
    """Get the absolute path to the code analysis schema.

    Returns:
        Absolute path to 002_code_analysis_schema.sql
    """
    return str(CAPABILITY_ROOT / "database" / "schemas" / "002_code_analysis_schema.sql")


__all__ = [
    "CAPABILITY_ID",
    "register_capability",
    "get_schema_path",
]
