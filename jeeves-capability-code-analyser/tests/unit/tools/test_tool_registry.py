"""Tests for tool registry with risk levels.

Updated to use MockToolRegistry from test fixtures after refactoring.
The canonical ToolCatalog is in jeeves_avionics.tools.catalog.
"""

import pytest
from jeeves_protocols import RiskLevel
from tests.fixtures.mocks.tools import MockToolRegistry, MockToolDefinition


class TestMockToolRegistry:
    """Tests for MockToolRegistry risk level functionality."""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry for each test."""
        return MockToolRegistry()

    def test_default_tools_are_registered(self, registry):
        """Default code analysis tools should be pre-registered."""
        assert registry.has_tool("read_file")
        assert registry.has_tool("glob_files")
        assert registry.has_tool("grep_search")

    def test_tool_default_risk_level(self, registry):
        """Default tools have LOW risk level."""
        tool = registry.get_tool("read_file")
        assert tool.risk_level == RiskLevel.LOW
        assert tool.is_read_only

    def test_register_new_tool(self, registry):
        """Can register new tools with custom risk level."""
        @registry.register(
            name="delete_all",
            description="Delete all data",
            parameters={"force": "boolean"},
            risk_level=RiskLevel.HIGH
        )
        async def delete_all(force: bool):
            pass

        tool = registry.get_tool("delete_all")
        assert tool.risk_level == RiskLevel.HIGH
        assert tool.is_destructive

    def test_get_read_only_tools(self, registry):
        """Can query read-only tools."""
        read_only = registry.get_read_only_tools()
        assert "read_file" in read_only
        assert "glob_files" in read_only
        assert "grep_search" in read_only

    def test_get_destructive_tools(self, registry):
        """Destructive tools list is initially empty."""
        destructive = registry.get_destructive_tools()
        assert destructive == []

    def test_is_destructive_tool(self, registry):
        """Registry can check if a tool is destructive by name."""
        # Add a destructive tool
        @registry.register(
            name="dangerous",
            description="Dangerous operation",
            parameters={},
            risk_level=RiskLevel.HIGH
        )
        async def dangerous():
            pass

        assert not registry.is_destructive_tool("read_file")
        assert registry.is_destructive_tool("dangerous")
        assert not registry.is_destructive_tool("nonexistent")

    def test_tool_to_dict(self, registry):
        """Tool dict representation includes all fields."""
        tool = registry.get_tool("read_file")
        tool_dict = tool.to_dict()

        assert tool_dict["name"] == "read_file"
        assert "description" in tool_dict
        assert tool_dict["risk_level"] == "low"

    def test_list_tools(self, registry):
        """Can list all registered tools."""
        tools = registry.list_tools()
        assert len(tools) >= 6  # Default tools

    def test_list_tools_with_filter(self, registry):
        """Can filter tools by risk level."""
        low_risk = registry.list_tools(risk_filter="low")
        assert all(t["risk_level"] == "low" for t in low_risk)


class TestRiskLevelRequiresConfirmation:
    """Tests for confirmation requirement based on risk level."""

    def test_destructive_requires_confirmation(self):
        """DESTRUCTIVE risk level should require confirmation."""
        assert RiskLevel.requires_confirmation(RiskLevel.DESTRUCTIVE) is True

    def test_high_requires_confirmation(self):
        """HIGH risk level should require confirmation."""
        assert RiskLevel.requires_confirmation(RiskLevel.HIGH) is True

    def test_critical_requires_confirmation(self):
        """CRITICAL risk level should require confirmation."""
        assert RiskLevel.requires_confirmation(RiskLevel.CRITICAL) is True

    def test_write_does_not_require_confirmation(self):
        """WRITE risk level should not require confirmation."""
        assert RiskLevel.requires_confirmation(RiskLevel.WRITE) is False

    def test_read_only_does_not_require_confirmation(self):
        """READ_ONLY risk level should not require confirmation."""
        assert RiskLevel.requires_confirmation(RiskLevel.READ_ONLY) is False

    def test_low_does_not_require_confirmation(self):
        """LOW risk level should not require confirmation."""
        assert RiskLevel.requires_confirmation(RiskLevel.LOW) is False

    def test_medium_does_not_require_confirmation(self):
        """MEDIUM risk level should not require confirmation."""
        assert RiskLevel.requires_confirmation(RiskLevel.MEDIUM) is False
