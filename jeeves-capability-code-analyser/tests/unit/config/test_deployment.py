"""Tests for deployment configuration module."""

import pytest
import os
from jeeves_capability_code_analyser.config import (
    NodeProfile,
    PROFILES,
    get_deployment_mode,
    get_active_profile_names,
    get_node_for_agent,
    get_profile_for_agent,
    get_all_agents,
    get_node_summary,
    validate_configuration
)


class TestNodeProfile:
    """Test NodeProfile dataclass."""

    def test_create_valid_profile(self):
        """Test creating a valid node profile."""
        profile = NodeProfile(
            name="test-node",
            vram_gb=12,
            ram_gb=32,
            model="test-model.gguf",
            model_size_gb=8.0,
            max_parallel=4,
            agents=["planner"],
            base_url="http://localhost:11434"
        )

        assert profile.name == "test-node"
        assert profile.vram_gb == 12
        assert profile.max_parallel == 4

    def test_vram_utilization(self):
        """Test VRAM utilization calculation."""
        profile = NodeProfile(
            name="test",
            base_url="http://localhost:8080",
            vram_gb=10,
            ram_gb=20,
            model="test.gguf",
            model_size_gb=5.0,
            max_parallel=4,
            agents=["planner"]
        )

        assert profile.vram_utilization == 50.0

    def test_model_name_extraction(self):
        """Test model name extraction without extensions."""
        profile = NodeProfile(
            name="test",
            base_url="http://localhost:8080",
            vram_gb=10,
            ram_gb=20,
            model="qwen2.5-14b-instruct-q4_K_M.gguf",
            model_size_gb=8.5,
            max_parallel=4,
            agents=["planner"]
        )

        assert profile.model_name == "qwen2.5-14b-instruct"

    def test_can_handle_load(self):
        """Test load capacity checking."""
        profile = NodeProfile(
            name="test",
            base_url="http://localhost:8080",
            vram_gb=10,
            ram_gb=20,
            model="test.gguf",
            model_size_gb=5.0,
            max_parallel=4,
            agents=["planner"]
        )

        assert profile.can_handle_load(2) is True
        assert profile.can_handle_load(3) is True
        assert profile.can_handle_load(4) is False
        assert profile.can_handle_load(5) is False

    def test_invalid_vram_size(self):
        """Test that model size exceeding VRAM raises error."""
        with pytest.raises(ValueError, match="Model size .* exceeds VRAM capacity"):
            NodeProfile(
                name="test",
                base_url="http://localhost:8080",
                vram_gb=6,
                ram_gb=20,
                model="too-large.gguf",
                model_size_gb=10.0,
                max_parallel=4,
                agents=["planner"]
            )

    def test_invalid_max_parallel(self):
        """Test that max_parallel < 1 raises error."""
        with pytest.raises(ValueError, match="max_parallel must be >= 1"):
            NodeProfile(
                name="test",
                base_url="http://localhost:8080",
                vram_gb=6,
                ram_gb=20,
                model="test.gguf",
                model_size_gb=4.0,
                max_parallel=0,
                agents=["planner"]
            )


class TestDeploymentMode:
    """Test deployment mode detection."""

    def test_default_mode(self, monkeypatch):
        """Test default is single_node."""
        monkeypatch.delenv("DEPLOYMENT_MODE", raising=False)
        assert get_deployment_mode() == "single_node"

    def test_single_node_mode(self, monkeypatch):
        """Test single_node mode."""
        monkeypatch.setenv("DEPLOYMENT_MODE", "single_node")
        assert get_deployment_mode() == "single_node"

    def test_distributed_mode(self, monkeypatch):
        """Test distributed mode."""
        monkeypatch.setenv("DEPLOYMENT_MODE", "distributed")
        assert get_deployment_mode() == "distributed"

    def test_case_insensitive(self, monkeypatch):
        """Test deployment mode is case-insensitive."""
        monkeypatch.setenv("DEPLOYMENT_MODE", "DISTRIBUTED")
        assert get_deployment_mode() == "distributed"


class TestActiveProfiles:
    """Test active profile detection."""

    def test_single_node_profiles(self, monkeypatch):
        """Test single_node mode returns single_node profile."""
        monkeypatch.setenv("DEPLOYMENT_MODE", "single_node")
        profiles = get_active_profile_names()
        assert profiles == ["single_node"]

    def test_distributed_3node_profiles(self, monkeypatch):
        """Test distributed mode with 3 nodes."""
        monkeypatch.setenv("DEPLOYMENT_MODE", "distributed")
        monkeypatch.setenv("LLAMASERVER_NODE3_URL", "http://node3:8080")

        profiles = get_active_profile_names()
        assert profiles == ["node1", "node2", "node3"]

    def test_distributed_2node_profiles(self, monkeypatch):
        """Test distributed mode with 2 nodes."""
        monkeypatch.setenv("DEPLOYMENT_MODE", "distributed")
        monkeypatch.delenv("LLAMASERVER_NODE3_URL", raising=False)

        profiles = get_active_profile_names()
        assert profiles == ["node1_2node", "node2_2node"]


class TestAgentAssignment:
    """Test agent-to-node assignment."""

    def test_get_node_for_agent_single(self, monkeypatch):
        """Test agent assignment in single_node mode."""
        monkeypatch.setenv("DEPLOYMENT_MODE", "single_node")

        assert get_node_for_agent("planner") == "single_node"
        assert get_node_for_agent("traverser") == "single_node"
        assert get_node_for_agent("critic") == "single_node"

    @pytest.mark.prod
    def test_get_node_for_agent_distributed(self, monkeypatch):
        """Test agent assignment in distributed mode."""
        monkeypatch.setenv("DEPLOYMENT_MODE", "distributed")
        monkeypatch.setenv("LLAMASERVER_NODE3_URL", "http://node3:8080")

        assert get_node_for_agent("perception") == "node1"
        assert get_node_for_agent("traverser") == "node2"
        assert get_node_for_agent("planner") == "node3"
        assert get_node_for_agent("critic") == "node3"

    @pytest.mark.prod
    def test_get_node_for_agent_case_insensitive(self, monkeypatch):
        """Test agent name is case-insensitive."""
        monkeypatch.setenv("DEPLOYMENT_MODE", "distributed")
        monkeypatch.setenv("LLAMASERVER_NODE3_URL", "http://node3:8080")

        assert get_node_for_agent("PLANNER") == "node3"
        assert get_node_for_agent("Planner") == "node3"
        assert get_node_for_agent("planner") == "node3"

    def test_agent_override(self, monkeypatch):
        """Test agent node assignment can be overridden."""
        monkeypatch.setenv("DEPLOYMENT_MODE", "distributed")
        monkeypatch.setenv("LLAMASERVER_NODE3_URL", "http://node3:8080")
        monkeypatch.setenv("AGENT_NODE_OVERRIDE_PLANNER", "node2")

        assert get_node_for_agent("planner") == "node2"

    @pytest.mark.prod
    def test_get_profile_for_agent(self, monkeypatch):
        """Test getting full profile for agent."""
        monkeypatch.setenv("DEPLOYMENT_MODE", "distributed")
        monkeypatch.setenv("LLAMASERVER_NODE3_URL", "http://node3:8080")

        profile = get_profile_for_agent("planner")
        assert profile.name == "node3-reasoning-hub"
        assert "planner" in profile.agents
        assert profile.vram_gb == 12

    def test_get_all_agents_single(self, monkeypatch):
        """Test getting all agents in single_node mode."""
        monkeypatch.setenv("DEPLOYMENT_MODE", "single_node")

        agents = get_all_agents()
        assert "perception" in agents
        assert "intent" in agents
        assert "planner" in agents
        assert "traverser" in agents
        assert "synthesizer" in agents
        assert "critic" in agents
        assert "integration" in agents

    def test_get_all_agents_distributed(self, monkeypatch):
        """Test getting all agents in distributed mode."""
        monkeypatch.setenv("DEPLOYMENT_MODE", "distributed")
        monkeypatch.setenv("LLAMASERVER_NODE3_URL", "http://node3:8080")

        agents = get_all_agents()
        assert "perception" in agents
        assert "intent" in agents
        assert "planner" in agents
        assert "traverser" in agents
        assert "synthesizer" in agents
        assert "critic" in agents
        assert "integration" in agents


class TestNodeSummary:
    """Test node summary generation."""

    def test_node_summary_single(self, monkeypatch):
        """Test node summary in single_node mode."""
        monkeypatch.setenv("DEPLOYMENT_MODE", "single_node")

        summary = get_node_summary()
        assert "single_node" in summary
        assert summary["single_node"]["vram_gb"] == 6
        assert "planner" in summary["single_node"]["agents"]

    @pytest.mark.prod
    def test_node_summary_distributed(self, monkeypatch):
        """Test node summary in distributed mode."""
        monkeypatch.setenv("DEPLOYMENT_MODE", "distributed")
        monkeypatch.setenv("LLAMASERVER_NODE3_URL", "http://node3:8080")

        summary = get_node_summary()
        assert "node1" in summary
        assert "node2" in summary
        assert "node3" in summary


class TestConfiguration:
    """Test configuration validation."""

    def test_predefined_profiles_valid(self):
        """Test that all predefined profiles are valid."""
        for name, profile in PROFILES.items():
            assert profile.vram_gb > 0
            assert profile.model_size_gb <= profile.vram_gb
            assert profile.max_parallel > 0
            assert len(profile.agents) > 0

    def test_validate_configuration(self, monkeypatch):
        """Test configuration validation passes for valid setup."""
        monkeypatch.setenv("DEPLOYMENT_MODE", "single_node")
        validate_configuration()

    def test_distributed_profiles_have_all_agents(self, monkeypatch):
        """Test that distributed mode assigns all required agents."""
        monkeypatch.setenv("DEPLOYMENT_MODE", "distributed")
        monkeypatch.setenv("LLAMASERVER_NODE3_URL", "http://node3:8080")

        agents = get_all_agents()
        required = ["perception", "intent", "planner", "traverser", "synthesizer", "critic", "integration"]

        for agent in required:
            assert agent in agents, f"Required agent '{agent}' not assigned"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
