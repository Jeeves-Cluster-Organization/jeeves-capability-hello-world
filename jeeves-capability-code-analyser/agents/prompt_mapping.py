"""
Agent-Prompt Mapping - Centralized reference for which prompts each agent uses.

This module formalizes the relationship between agents and their prompts,
making it easy to understand and maintain the prompt ecosystem.

Centralized Architecture (v4.0):
- Agent names use simple form: "perception", "intent", "planner", etc.
- Matches AgentConfig.name in pipeline_config.py

Constitutional Compliance:
- P1 (Accuracy First): Clear mapping ensures correct prompts
- P2 (Code Context Priority): Context builder provides repo awareness
- Amendment X: Prompt externalization tracking

Context Builder:
All code analysis prompts use agents.code_analysis.context_builder to inject context.
Each agent calls the appropriate build_*_context() function.
"""

from typing import Dict, List, Set


# Agent-to-prompt mapping
# Each agent lists the prompts it uses from the PromptRegistry
# Agent names use simple form per centralized architecture v4.0
AGENT_PROMPTS: Dict[str, List[str]] = {
    # --- CODE ANALYSIS AGENTS (7-agent read-only pipeline) ---
    #
    # LLM agents use context builders for dynamic context:
    #   - Intent: agents.code_analysis.context_builder.build_intent_context()
    #   - Planner: agents.code_analysis.context_builder.build_planner_context()
    #   - Critic: agents.code_analysis.context_builder.build_critic_context()
    #   - Integration: agents.code_analysis.context_builder.build_integration_context()
    #
    # Non-LLM agents (perception, executor) use hooks in pipeline_config.py
    #
    # Pipeline flow: perception -> intent -> planner -> executor -> synthesizer -> critic -> integration

    # Code Analysis Agent 1: Perception (has_llm=False - no prompts needed)
    # Uses perception_pre_process hook in pipeline_config.py
    "perception": [],

    # Code Analysis Agent 2: Intent
    # Classifies query type, extracts goals
    "intent": [
        "code_analysis.intent",
    ],

    # Code Analysis Agent 3: Planner
    # Creates tool execution plan (gets dynamic tool list from context builder)
    "planner": [
        "code_analysis.planner",
    ],

    # Code Analysis Agent 4: Executor (formerly Traverser)
    # No LLM prompts - deterministic tool execution using resilient ops
    "executor": [],

    # Code Analysis Agent 5: Synthesizer
    # Synthesizes findings from traversal
    "synthesizer": [
        "code_analysis.synthesizer",
    ],

    # Code Analysis Agent 6: Critic (anti-hallucination gate)
    # Validates results, checks for evidence
    "critic": [
        "code_analysis.critic",
    ],

    # Code Analysis Agent 7: Integration (response builder)
    # Builds final response with citations
    "integration": [
        "code_analysis.integration",
    ],
}


# Shared prompt building blocks (from prompts/core/)
SHARED_PROMPT_BLOCKS: Dict[str, str] = {
    "IDENTITY_BLOCK": "prompts/core/identity_block.py",
    "STYLE_BLOCK": "prompts/core/style_block.py",
    "ROLE_INVARIANTS": "prompts/core/role_invariants.py",
    "SAFETY_BLOCK": "prompts/core/safety_block.py",
}


# Context builder functions for LLM agents
# Note: perception and executor have has_llm=False, use hooks in pipeline_config.py
CONTEXT_BUILDERS: Dict[str, str] = {
    "intent": "agents.code_analysis.context_builder.build_intent_context",
    "planner": "agents.code_analysis.context_builder.build_planner_context",
    "synthesizer": "agents.code_analysis.context_builder.build_synthesizer_context",
    "critic": "agents.code_analysis.context_builder.build_critic_context",
    "integration": "agents.code_analysis.context_builder.build_integration_context",
}


# Primary prompts (main prompts used in production)
# Note: perception and executor have has_llm=False, so no primary prompts
PRIMARY_PROMPTS: Dict[str, str] = {
    "intent": "code_analysis.intent",
    "planner": "code_analysis.planner",
    "synthesizer": "code_analysis.synthesizer",
    "critic": "code_analysis.critic",
    "integration": "code_analysis.integration",
}


def get_agent_prompts(agent_name: str) -> List[str]:
    """Get list of prompts used by a specific agent.

    Args:
        agent_name: Name of the agent (e.g., "planner")

    Returns:
        List of prompt names used by the agent
    """
    return AGENT_PROMPTS.get(agent_name, [])


def get_primary_prompt(agent_name: str) -> str:
    """Get the primary prompt for an agent.

    Args:
        agent_name: Name of the agent

    Returns:
        Name of the primary prompt, or empty string if none
    """
    return PRIMARY_PROMPTS.get(agent_name, "")


def get_context_builder(agent_name: str) -> str:
    """Get the context builder function path for an agent.

    Args:
        agent_name: Name of the agent

    Returns:
        Import path for the context builder function, or empty string if none
    """
    return CONTEXT_BUILDERS.get(agent_name, "")


def get_agents_using_prompt(prompt_name: str) -> List[str]:
    """Get list of agents that use a specific prompt.

    Args:
        prompt_name: Name of the prompt (e.g., "code_analysis.planner")

    Returns:
        List of agent names that use this prompt
    """
    return [
        agent_name
        for agent_name, prompts in AGENT_PROMPTS.items()
        if prompt_name in prompts
    ]


def get_all_prompts() -> Set[str]:
    """Get set of all prompts used across all agents.

    Returns:
        Set of all unique prompt names
    """
    all_prompts: Set[str] = set()
    for prompts in AGENT_PROMPTS.values():
        all_prompts.update(prompts)
    return all_prompts


def get_llm_agents() -> List[str]:
    """Get list of agents that use LLM prompts.

    Returns:
        List of agent names that use LLM prompts
    """
    return [
        agent_name
        for agent_name, prompts in AGENT_PROMPTS.items()
        if prompts  # Has at least one prompt
    ]


def get_deterministic_agents() -> List[str]:
    """Get list of agents that don't use LLM prompts.

    Returns:
        List of agent names that are purely deterministic
    """
    return [
        agent_name
        for agent_name, prompts in AGENT_PROMPTS.items()
        if not prompts  # No prompts
    ]


def get_code_analysis_agents() -> List[str]:
    """Get list of code analysis pipeline agents.

    Returns:
        List of code analysis agent names in pipeline order
    """
    return [
        "perception",
        "intent",
        "planner",
        "executor",
        "synthesizer",
        "critic",
        "integration",
    ]


# Summary statistics
PROMPT_STATS = {
    "total_agents": len(AGENT_PROMPTS),
    "llm_agents": len(get_llm_agents()),
    "deterministic_agents": len(get_deterministic_agents()),
    "total_unique_prompts": len(get_all_prompts()),
    "code_analysis_agents": len(get_code_analysis_agents()),
}
