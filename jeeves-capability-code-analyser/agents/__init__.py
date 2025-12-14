"""
Code Analysis Agent Pipeline

Agents are defined declaratively via AgentConfig in pipeline_config.py.
This module exports supporting utilities only.

The 7-agent pipeline:
1. perception - Load session state, detect scope
2. intent - Classify query intent (LLM)
3. planner - Generate tool call plan (LLM)
4. executor - Execute read-only code operations (tools)
5. synthesizer - Aggregate findings (LLM)
6. critic - Validate results (LLM)
7. integration - Build response with citations (LLM)

Architecture:
- No concrete agent classes (all via AgentConfig)
- GenericEnvelope with dynamic outputs
- Hooks define capability-specific logic
- UnifiedRuntime executes pipeline from config
"""

# Context building functions (refactored from ContextBuilder class)
from .context_builder import (
    RepositoryContext,
    get_system_identity,
    get_available_tools_description,
    get_context_bounds_description,
    get_pipeline_overview,
    build_perception_context,
    build_intent_context,
    build_planner_context,
    build_synthesizer_context,
    build_critic_context,
    build_integration_context,
)
from .prompt_mapping import (
    AGENT_PROMPTS,
    PRIMARY_PROMPTS,
    CONTEXT_BUILDERS,
    get_agent_prompts,
    get_primary_prompt,
    get_context_builder,
)
from .protocols import (
    SessionStateServiceProtocol,
    ChunkServiceProtocol,
    GraphServiceProtocol,
    DomainEventEmitterProtocol,
)
from .summarizer import (
    summarize_tool_result,
    summarize_execution_results,
    extract_citations_from_results,
)

__all__ = [
    # Context building
    "RepositoryContext",
    "get_system_identity",
    "get_available_tools_description",
    "get_context_bounds_description",
    "get_pipeline_overview",
    "build_perception_context",
    "build_intent_context",
    "build_planner_context",
    "build_synthesizer_context",
    "build_critic_context",
    "build_integration_context",
    # Prompt mapping
    "AGENT_PROMPTS",
    "PRIMARY_PROMPTS",
    "CONTEXT_BUILDERS",
    "get_agent_prompts",
    "get_primary_prompt",
    "get_context_builder",
    # Protocols
    "SessionStateServiceProtocol",
    "ChunkServiceProtocol",
    "GraphServiceProtocol",
    "DomainEventEmitterProtocol",
    # Summarizer functions
    "summarize_tool_result",
    "summarize_execution_results",
    "extract_citations_from_results",
]
