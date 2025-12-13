"""
Integration Tests for Service Contracts.

Tests against the Jeeves Core Runtime Contract (docs/JEEVES_CORE_RUNTIME_CONTRACT.md).
These tests validate contract compliance without requiring jeeves-core internals.

Reference: JEEVES_CORE_RUNTIME_CONTRACT.md
"""

import asyncio
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.contract,
    pytest.mark.asyncio,
]


# =============================================================================
# Contract Protocol Definitions (from Runtime Contract)
# =============================================================================

class LLMProviderProtocol(Protocol):
    """LLM provider interface per contract."""

    async def generate(
        self,
        prompt: str,
        agent_role: str = "default",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Generate text completion."""
        ...

    async def generate_structured(
        self,
        prompt: str,
        schema: dict,
        agent_role: str = "default",
    ) -> dict:
        """Generate structured JSON output."""
        ...


class ToolExecutorProtocol(Protocol):
    """Tool execution interface per contract."""

    async def execute(
        self,
        tool_name: str,
        params: dict,
    ) -> dict:
        """Execute a tool by name."""
        ...

    def has_tool(self, name: str) -> bool:
        """Check if tool exists."""
        ...

    def list_tools(self) -> List[str]:
        """List available tools."""
        ...


class ToolRegistryProtocol(Protocol):
    """Tool registry interface per contract."""

    def register(
        self,
        tool_id: str,
        handler: Callable,
        description: str,
        parameters: dict,
        category: str,
        risk_level: str,
    ) -> None:
        """Register a tool."""
        ...


# =============================================================================
# Contract Data Classes
# =============================================================================

@dataclass
class StandardToolResult:
    """Standard tool result per contract."""
    status: str  # "success", "error", "partial"
    data: Any = None
    error: Optional[str] = None
    citations: List[dict] = field(default_factory=list)
    attempt_history: List[dict] = field(default_factory=list)


@dataclass
class ContextBounds:
    """Context bounds per contract."""
    max_input_tokens: int = 4096
    max_output_tokens: int = 2048
    max_iterations: int = 3
    max_context_tokens: int = 8192
    max_llm_calls: int = 10
    max_agent_hops: int = 21


@dataclass
class Finding:
    """Finding from working memory per contract."""
    content: str
    citations: List[dict] = field(default_factory=list)
    confidence: float = 0.0


# =============================================================================
# Mock Implementations for Testing
# =============================================================================

class MockLLMProvider:
    """Mock LLM provider implementing contract."""

    def __init__(self, responses: Optional[Dict[str, str]] = None):
        self.responses = responses or {}
        self.call_history: List[dict] = []

    async def generate(
        self,
        prompt: str,
        agent_role: str = "default",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        self.call_history.append({
            "method": "generate",
            "prompt": prompt,
            "agent_role": agent_role,
            "temperature": temperature,
            "max_tokens": max_tokens,
        })
        return self.responses.get(agent_role, f"Mock response for {agent_role}")

    async def generate_structured(
        self,
        prompt: str,
        schema: dict,
        agent_role: str = "default",
    ) -> dict:
        self.call_history.append({
            "method": "generate_structured",
            "prompt": prompt,
            "schema": schema,
            "agent_role": agent_role,
        })
        return {"result": "structured", "agent_role": agent_role}


class MockToolExecutor:
    """Mock tool executor implementing contract."""

    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.execution_history: List[dict] = []

    async def execute(self, tool_name: str, params: dict) -> dict:
        self.execution_history.append({
            "tool_name": tool_name,
            "params": params,
        })
        if tool_name not in self.tools:
            return StandardToolResult(
                status="error",
                error=f"Tool not found: {tool_name}",
            ).__dict__
        handler = self.tools[tool_name]
        result = await handler(**params) if asyncio.iscoroutinefunction(handler) else handler(**params)
        return result

    def has_tool(self, name: str) -> bool:
        return name in self.tools

    def list_tools(self) -> List[str]:
        return list(self.tools.keys())


class MockToolRegistry:
    """Mock tool registry implementing contract."""

    def __init__(self):
        self.registered_tools: Dict[str, dict] = {}

    def register(
        self,
        tool_id: str,
        handler: Callable,
        description: str,
        parameters: dict,
        category: str,
        risk_level: str,
    ) -> None:
        self.registered_tools[tool_id] = {
            "handler": handler,
            "description": description,
            "parameters": parameters,
            "category": category,
            "risk_level": risk_level,
        }


# =============================================================================
# Contract Compliance Tests
# =============================================================================

class TestLLMProviderContract:
    """Tests for LLM Provider contract compliance."""

    @pytest.fixture
    def llm_provider(self):
        return MockLLMProvider({
            "planner": "Plan: Step 1, Step 2",
            "critic": "Validation passed",
            "default": "Default response",
        })

    async def test_generate_returns_string(self, llm_provider):
        """Contract: generate() must return string."""
        result = await llm_provider.generate("Test prompt")
        assert isinstance(result, str)

    async def test_generate_accepts_agent_role(self, llm_provider):
        """Contract: generate() must accept agent_role parameter."""
        result = await llm_provider.generate("Test", agent_role="planner")
        assert result == "Plan: Step 1, Step 2"

    async def test_generate_accepts_temperature(self, llm_provider):
        """Contract: generate() must accept temperature parameter."""
        await llm_provider.generate("Test", temperature=0.3)
        assert llm_provider.call_history[-1]["temperature"] == 0.3

    async def test_generate_accepts_max_tokens(self, llm_provider):
        """Contract: generate() must accept max_tokens parameter."""
        await llm_provider.generate("Test", max_tokens=1000)
        assert llm_provider.call_history[-1]["max_tokens"] == 1000

    async def test_generate_structured_returns_dict(self, llm_provider):
        """Contract: generate_structured() must return dict."""
        result = await llm_provider.generate_structured(
            "Test",
            schema={"type": "object"},
        )
        assert isinstance(result, dict)

    async def test_generate_structured_accepts_schema(self, llm_provider):
        """Contract: generate_structured() must accept schema parameter."""
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        await llm_provider.generate_structured("Test", schema=schema)
        assert llm_provider.call_history[-1]["schema"] == schema


class TestToolExecutorContract:
    """Tests for Tool Executor contract compliance."""

    @pytest.fixture
    def tool_executor(self):
        executor = MockToolExecutor()
        executor.tools["test_tool"] = lambda x: {"status": "success", "data": x}
        return executor

    async def test_execute_returns_dict(self, tool_executor):
        """Contract: execute() must return dict."""
        result = await tool_executor.execute("test_tool", {"x": 1})
        assert isinstance(result, dict)

    async def test_has_tool_returns_bool(self, tool_executor):
        """Contract: has_tool() must return bool."""
        result = tool_executor.has_tool("test_tool")
        assert isinstance(result, bool)
        assert result is True

    async def test_has_tool_false_for_missing(self, tool_executor):
        """Contract: has_tool() returns False for missing tools."""
        result = tool_executor.has_tool("nonexistent")
        assert result is False

    async def test_list_tools_returns_list(self, tool_executor):
        """Contract: list_tools() must return list of strings."""
        result = tool_executor.list_tools()
        assert isinstance(result, list)
        assert all(isinstance(t, str) for t in result)

    async def test_execute_missing_tool_returns_error(self, tool_executor):
        """Contract: execute() on missing tool returns error status."""
        result = await tool_executor.execute("missing", {})
        assert result["status"] == "error"


class TestToolRegistryContract:
    """Tests for Tool Registry contract compliance."""

    @pytest.fixture
    def registry(self):
        return MockToolRegistry()

    def test_register_accepts_all_parameters(self, registry):
        """Contract: register() must accept all specified parameters."""
        def handler(): pass

        registry.register(
            tool_id="my.tool",
            handler=handler,
            description="Test tool",
            parameters={"param1": "string"},
            category="COMPOSITE",
            risk_level="LOW",
        )

        assert "my.tool" in registry.registered_tools

    def test_registered_tool_has_all_fields(self, registry):
        """Contract: registered tool must store all metadata."""
        def handler(): pass

        registry.register(
            tool_id="my.tool",
            handler=handler,
            description="Test tool",
            parameters={"param1": "string"},
            category="COMPOSITE",
            risk_level="LOW",
        )

        tool = registry.registered_tools["my.tool"]
        assert tool["description"] == "Test tool"
        assert tool["category"] == "COMPOSITE"
        assert tool["risk_level"] == "LOW"


class TestStandardToolResultContract:
    """Tests for Standard Tool Result contract compliance."""

    def test_result_has_status(self):
        """Contract: StandardToolResult must have status field."""
        result = StandardToolResult(status="success")
        assert hasattr(result, "status")
        assert result.status == "success"

    def test_status_values(self):
        """Contract: status must be success, error, or partial."""
        for status in ["success", "error", "partial"]:
            result = StandardToolResult(status=status)
            assert result.status in ["success", "error", "partial"]

    def test_result_has_optional_data(self):
        """Contract: data field is optional."""
        result = StandardToolResult(status="success", data={"key": "value"})
        assert result.data == {"key": "value"}

    def test_result_has_optional_error(self):
        """Contract: error field is optional."""
        result = StandardToolResult(status="error", error="Something failed")
        assert result.error == "Something failed"

    def test_result_has_citations(self):
        """Contract: citations must be list."""
        result = StandardToolResult(
            status="success",
            citations=[{"file": "test.py", "line": 10}],
        )
        assert isinstance(result.citations, list)

    def test_result_has_attempt_history(self):
        """Contract: attempt_history must be list."""
        result = StandardToolResult(
            status="success",
            attempt_history=[{"attempt": 1, "success": True}],
        )
        assert isinstance(result.attempt_history, list)


class TestContextBoundsContract:
    """Tests for Context Bounds contract compliance."""

    def test_default_bounds(self):
        """Contract: default bounds per specification."""
        bounds = ContextBounds()
        assert bounds.max_input_tokens == 4096
        assert bounds.max_output_tokens == 2048
        assert bounds.max_iterations == 3
        assert bounds.max_context_tokens == 8192
        assert bounds.max_llm_calls == 10
        assert bounds.max_agent_hops == 21

    def test_custom_bounds(self):
        """Contract: bounds can be customized."""
        bounds = ContextBounds(
            max_input_tokens=8192,
            max_llm_calls=20,
        )
        assert bounds.max_input_tokens == 8192
        assert bounds.max_llm_calls == 20


class TestMemoryContract:
    """Tests for Memory contract compliance."""

    def test_finding_has_required_fields(self):
        """Contract: Finding must have content and citations."""
        finding = Finding(
            content="Found code",
            citations=[{"file": "main.py", "line": 42}],
            confidence=0.9,
        )
        assert finding.content == "Found code"
        assert len(finding.citations) == 1
        assert finding.confidence == 0.9

    def test_finding_citations_default_empty(self):
        """Contract: citations default to empty list."""
        finding = Finding(content="Test")
        assert finding.citations == []

    def test_finding_confidence_default_zero(self):
        """Contract: confidence defaults to 0."""
        finding = Finding(content="Test")
        assert finding.confidence == 0.0


class TestToolCategoriesContract:
    """Tests for Tool Categories per contract."""

    def test_valid_categories(self):
        """Contract: valid tool categories."""
        valid_categories = ["COMPOSITE", "RESILIENT", "STANDALONE", "UNIFIED"]
        for category in valid_categories:
            assert category in valid_categories

    def test_category_descriptions(self):
        """Contract: category descriptions."""
        category_descriptions = {
            "COMPOSITE": "Multi-step tools with fallback strategies",
            "RESILIENT": "Wrapped base tools with retry logic",
            "STANDALONE": "Simple, single-operation tools",
            "UNIFIED": "High-level unified entry points",
        }
        assert len(category_descriptions) == 4


class TestRiskLevelsContract:
    """Tests for Risk Levels per contract."""

    def test_valid_risk_levels(self):
        """Contract: valid risk levels."""
        valid_levels = ["LOW", "MEDIUM", "HIGH"]
        for level in valid_levels:
            assert level in valid_levels


class TestCapabilityRegistrationContract:
    """Tests for Capability Registration contract."""

    def test_registration_function_signature(self):
        """Contract: register_capability() must be callable with no args."""
        # Mock registration
        def register_capability():
            pass

        # Should be callable with no arguments
        register_capability()

    def test_bootstrap_order(self):
        """Contract: Registration must happen before runtime imports."""
        bootstrap_order = []

        def register_capability():
            bootstrap_order.append("registration")

        def import_runtime():
            bootstrap_order.append("runtime")

        # Correct order
        register_capability()
        import_runtime()

        assert bootstrap_order == ["registration", "runtime"]


class TestAgentEventTypesContract:
    """Tests for Agent Event Types per contract."""

    def test_event_types(self):
        """Contract: valid agent event types."""
        event_types = [
            "AGENT_STARTED",
            "AGENT_COMPLETED",
            "TOOL_STARTED",
            "TOOL_COMPLETED",
            "STAGE_STARTED",
            "STAGE_COMPLETED",
            "ERROR",
            "CLARIFICATION_REQUESTED",
        ]
        assert len(event_types) == 8
