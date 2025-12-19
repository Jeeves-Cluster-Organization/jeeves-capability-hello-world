"""Tests for agents/PROMPT_MAPPING module.

Validates that the agent-to-prompt mapping is consistent and complete,
ensuring all prompts referenced exist in the registry and all registered
prompts are properly mapped to agents.

Note: v4.0 centralized architecture uses simple agent names like
"perception", "intent", "planner", etc.
"""

import pytest
from agents.prompt_mapping import (
    AGENT_PROMPTS,
    SHARED_PROMPT_BLOCKS,
    PRIMARY_PROMPTS,
    CONTEXT_BUILDERS,
    get_agent_prompts,
    get_primary_prompt,
    get_context_builder,
    get_agents_using_prompt,
    get_all_prompts,
    get_llm_agents,
    get_deterministic_agents,
    get_code_analysis_agents,
    PROMPT_STATS,
)
from jeeves_mission_system.prompts.core.registry import PromptRegistry

# Ensure code analysis prompts are registered before tests run
from prompts.code_analysis import register_code_analysis_prompts
register_code_analysis_prompts()


class TestAgentPromptsMapping:
    """Test AGENT_PROMPTS dictionary structure and consistency."""

    def test_all_code_analysis_agents_have_mapping(self):
        """Ensure all 7 code analysis agents are represented in the mapping."""
        expected_agents = [
            "perception",
            "intent",
            "planner",
            "executor",
            "synthesizer",
            "critic",
            "integration",
        ]

        for agent in expected_agents:
            assert agent in AGENT_PROMPTS, f"Agent '{agent}' missing from AGENT_PROMPTS"

    def test_prompt_lists_are_lists(self):
        """Ensure all values in AGENT_PROMPTS are lists."""
        for agent_name, prompts in AGENT_PROMPTS.items():
            assert isinstance(prompts, list), f"{agent_name} prompts should be a list"

    def test_deterministic_agents_have_no_prompts(self):
        """Ensure agents without LLM calls have empty prompt lists."""
        # perception and executor have has_llm=False
        deterministic_agents = [
            "perception",  # Deterministic - uses pre_process hook
            "executor",  # Deterministic tool executor
        ]

        for agent in deterministic_agents:
            assert AGENT_PROMPTS[agent] == [], f"{agent} should have no prompts"

    def test_llm_agents_have_prompts(self):
        """Ensure agents with LLM calls have non-empty prompt lists."""
        # Note: perception removed - has_llm=False
        llm_agents = [
            "intent",
            "planner",
            "synthesizer",
            "critic",
            "integration",
        ]

        for agent in llm_agents:
            assert len(AGENT_PROMPTS[agent]) > 0, f"{agent} should have prompts"


class TestPromptRegistryIntegration:
    """Test that mapped prompts exist in the registry."""

    def test_all_mapped_prompts_exist_in_registry(self):
        """Ensure all prompts in AGENT_PROMPTS exist in PromptRegistry."""
        registry = PromptRegistry.get_instance()
        registered_prompts = registry.list_prompts()

        for agent_name, prompts in AGENT_PROMPTS.items():
            for prompt_name in prompts:
                assert prompt_name in registered_prompts, (
                    f"Prompt '{prompt_name}' (used by {agent_name}) "
                    f"not found in PromptRegistry"
                )

    def test_code_analysis_prompts_registered(self):
        """Ensure code analysis prompts are in registry."""
        registry = PromptRegistry.get_instance()
        registered_prompts = registry.list_prompts()

        # Note: perception removed - has_llm=False, no prompt needed
        expected_prompts = [
            "code_analysis.intent",
            "code_analysis.planner",
            "code_analysis.synthesizer",
            "code_analysis.critic",
            "code_analysis.integration",
        ]

        for prompt in expected_prompts:
            assert prompt in registered_prompts, f"Code analysis prompt '{prompt}' not registered"


class TestHelperFunctions:
    """Test helper functions in PROMPT_MAPPING module."""

    def test_get_agent_prompts_returns_list(self):
        """Ensure get_agent_prompts returns correct prompts."""
        prompts = get_agent_prompts("planner")
        assert isinstance(prompts, list)
        assert len(prompts) > 0
        assert "code_analysis.planner" in prompts

    def test_get_agent_prompts_unknown_agent(self):
        """Ensure unknown agent returns empty list."""
        prompts = get_agent_prompts("UnknownAgent")
        assert prompts == []

    def test_get_primary_prompt(self):
        """Ensure get_primary_prompt returns correct values."""
        assert get_primary_prompt("planner") == "code_analysis.planner"
        assert get_primary_prompt("critic") == "code_analysis.critic"

    def test_get_primary_prompt_unknown_agent(self):
        """Ensure unknown agent returns empty string."""
        assert get_primary_prompt("UnknownAgent") == ""

    def test_get_context_builder(self):
        """Ensure get_context_builder returns correct paths."""
        assert get_context_builder("planner") == "agents.code_analysis.context_builder.build_planner_context"
        assert get_context_builder("critic") == "agents.code_analysis.context_builder.build_critic_context"
        assert get_context_builder("UnknownAgent") == ""

    def test_get_agents_using_prompt(self):
        """Ensure reverse lookup works correctly."""
        agents = get_agents_using_prompt("code_analysis.planner")
        assert "planner" in agents
        assert len(agents) == 1

    def test_get_agents_using_prompt_not_found(self):
        """Ensure non-existent prompt returns empty list."""
        agents = get_agents_using_prompt("nonexistent.prompt")
        assert agents == []

    def test_get_all_prompts(self):
        """Ensure get_all_prompts returns all unique prompts."""
        all_prompts = get_all_prompts()
        assert isinstance(all_prompts, set)
        assert "code_analysis.planner" in all_prompts
        assert "code_analysis.critic" in all_prompts
        assert "code_analysis.intent" in all_prompts

    def test_get_llm_agents(self):
        """Ensure LLM agents are correctly identified."""
        llm_agents = get_llm_agents()
        assert "planner" in llm_agents
        assert "critic" in llm_agents
        assert "executor" not in llm_agents

    def test_get_deterministic_agents(self):
        """Ensure deterministic agents are correctly identified."""
        det_agents = get_deterministic_agents()
        assert "executor" in det_agents
        assert "planner" not in det_agents

    def test_get_code_analysis_agents(self):
        """Ensure code analysis agents are returned in order."""
        ca_agents = get_code_analysis_agents()
        assert len(ca_agents) == 7
        assert ca_agents[0] == "perception"
        assert ca_agents[2] == "planner"
        assert ca_agents[3] == "executor"
        assert ca_agents[4] == "synthesizer"
        assert ca_agents[5] == "critic"
        assert ca_agents[6] == "integration"


class TestContextBuilders:
    """Test context builder mapping."""

    def test_code_analysis_agents_have_context_builders(self):
        """Ensure code analysis LLM agents have context builders."""
        # Note: perception removed - has_llm=False, uses hook in pipeline_config.py
        expected = {
            "intent": "agents.code_analysis.context_builder.build_intent_context",
            "planner": "agents.code_analysis.context_builder.build_planner_context",
            "synthesizer": "agents.code_analysis.context_builder.build_synthesizer_context",
            "critic": "agents.code_analysis.context_builder.build_critic_context",
            "integration": "agents.code_analysis.context_builder.build_integration_context",
        }

        for agent, builder in expected.items():
            assert CONTEXT_BUILDERS.get(agent) == builder, (
                f"{agent} should have context builder '{builder}'"
            )

    def test_deterministic_agents_have_no_context_builder(self):
        """Ensure deterministic agents have no context builder."""
        # perception and executor have has_llm=False
        assert "perception" not in CONTEXT_BUILDERS
        assert "executor" not in CONTEXT_BUILDERS


class TestPromptStats:
    """Test PROMPT_STATS summary."""

    def test_stats_has_expected_keys(self):
        """Ensure PROMPT_STATS has all expected keys."""
        expected_keys = [
            "total_agents",
            "llm_agents",
            "deterministic_agents",
            "total_unique_prompts",
            "code_analysis_agents",
        ]

        for key in expected_keys:
            assert key in PROMPT_STATS, f"PROMPT_STATS missing key '{key}'"

    def test_stats_values_consistent(self):
        """Ensure stats values are internally consistent."""
        total = PROMPT_STATS["total_agents"]
        llm = PROMPT_STATS["llm_agents"]
        det = PROMPT_STATS["deterministic_agents"]

        assert llm + det == total, "LLM + deterministic agents should equal total"
        assert total == 7, f"Should have 7 agents total, got {total}"
        # perception and executor are deterministic (has_llm=False)
        assert det == 2, f"Should have 2 deterministic agents, got {det}"
        assert llm == 5, f"Should have 5 LLM agents, got {llm}"

    def test_stats_code_analysis_count(self):
        """Ensure code analysis agents count matches."""
        assert PROMPT_STATS["code_analysis_agents"] == 7


class TestSharedPromptBlocks:
    """Test SHARED_PROMPT_BLOCKS configuration."""

    def test_shared_blocks_paths_valid(self):
        """Ensure shared block paths point to valid files."""
        expected_blocks = [
            "IDENTITY_BLOCK",
            "STYLE_BLOCK",
            "ROLE_INVARIANTS",
            "SAFETY_BLOCK",
        ]

        for block in expected_blocks:
            assert block in SHARED_PROMPT_BLOCKS, f"Missing shared block '{block}'"
            path = SHARED_PROMPT_BLOCKS[block]
            assert path.startswith("prompts/core/"), f"Block path should be in prompts/core/"
