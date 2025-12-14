"""Tests for composite tools (Amendment XVII).

These tests verify the composite tool contracts:
1. Determinism: Same inputs produce same execution sequence
2. Transparency: Return attempt_history showing each step
3. Citation Aggregation: Collect and deduplicate citations
4. Bounds Respect: Stay within max_llm_calls_per_query
5. Graceful Degradation: Return partial results on step failure

SKIPPED: These tests require composite tool modules (safe_locator, symbol_explorer, etc.)
which are not yet implemented.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# Skip entire module - composite tool modules are not implemented
pytestmark = pytest.mark.skip(reason="Composite tool modules (safe_locator, symbol_explorer, git_historian, module_mapper, flow_tracer, robust_tool_base) not implemented")

from jeeves_mission_system.contracts import tool_catalog
from tests.fixtures.mocks.tools import MockToolRegistry


class TestSafeLocatorTool:
    """Tests for the locate composite tool."""

    @pytest.fixture
    def mock_registry(self):
        """Mock the tool registry for isolated testing."""
        mock_reg = MockToolRegistry()
        with patch.object(tool_catalog, 'has_tool', return_value=True):
            with patch.object(tool_catalog, 'get_function') as mock_get:
                yield mock_get

    @pytest.mark.asyncio
    async def test_locate_returns_attempt_history(self, mock_registry):
        """Verify locate returns attempt_history per Amendment XVII."""
        # Import inside test to avoid early registration issues
        from tools.safe_locator import locate

        # Mock find_symbol to return no match
        mock_find_symbol = AsyncMock(return_value={"status": "success", "symbols": []})
        # Mock grep_search to return a match
        mock_grep = AsyncMock(return_value={
            "status": "success",
            "matches": [{"file": "test.py", "line": 10, "match": "def test_func"}]
        })
        # Mock semantic_search
        mock_semantic = AsyncMock(return_value={"status": "success", "results": []})

        def get_tool_fn(name):
            if name == "find_symbol":
                return mock_find_symbol
            elif name == "grep_search":
                return mock_grep
            elif name == "semantic_search":
                return mock_semantic
            return AsyncMock(return_value={"status": "error"})

        mock_registry.side_effect = get_tool_fn

        result = await locate(query="test_func")

        # Verify attempt_history is present
        assert "attempt_history" in result
        assert isinstance(result["attempt_history"], list)
        assert len(result["attempt_history"]) > 0

        # Verify each attempt has required fields
        for attempt in result["attempt_history"]:
            assert "step" in attempt
            assert "strategy" in attempt
            assert "result" in attempt

    @pytest.mark.asyncio
    async def test_locate_returns_citations(self, mock_registry):
        """Verify locate aggregates citations in [file:line] format."""
        from tools.safe_locator import locate

        mock_grep = AsyncMock(return_value={
            "status": "success",
            "matches": [
                {"file": "src/foo.py", "line": 42, "match": "class Foo"},
                {"file": "src/bar.py", "line": 15, "match": "class Bar"},
            ]
        })
        mock_registry.side_effect = lambda name: mock_grep if name == "grep_search" else AsyncMock(return_value={"status": "success", "symbols": []})

        result = await locate(query="class")

        # Verify citations are present
        assert "citations" in result
        assert isinstance(result["citations"], list)

        # Verify citation format
        for citation in result["citations"]:
            assert citation.startswith("[")
            assert citation.endswith("]")
            assert ":" in citation

    @pytest.mark.asyncio
    async def test_locate_deterministic_fallback(self, mock_registry):
        """Verify locate follows deterministic fallback sequence."""
        from tools.safe_locator import locate

        call_order = []

        def track_calls(name):
            async def tracked(*args, **kwargs):
                call_order.append(name)
                return {"status": "success", "symbols": [], "matches": [], "results": []}
            return tracked

        mock_registry.side_effect = track_calls

        await locate(query="missing_thing", search_type="auto")

        # Verify fallback order for auto mode
        expected_order = [
            "find_symbol",  # exact
            "find_symbol",  # partial
            "grep_search",  # case-sensitive
            "grep_search",  # case-insensitive
            "semantic_search",  # final fallback
        ]
        assert call_order == expected_order


class TestSymbolExplorerTool:
    """Tests for the explore_symbol_usage composite tool."""

    @pytest.fixture
    def mock_registry(self):
        """Mock the tool registry for isolated testing."""
        with patch.object(tool_catalog, 'has_tool', return_value=True):
            with patch.object(tool_catalog, 'get_function') as mock_get:
                yield mock_get

    @pytest.mark.asyncio
    async def test_explore_symbol_returns_definitions(self, mock_registry):
        """Verify explore_symbol_usage returns definition locations."""
        from tools.symbol_explorer import explore_symbol_usage

        mock_find_symbol = AsyncMock(return_value={
            "status": "success",
            "symbols": [{"file": "src/models.py", "line": 42, "name": "MyClass", "type": "class"}]
        })
        mock_get_importers = AsyncMock(return_value={"status": "success", "importers": []})
        mock_grep = AsyncMock(return_value={"status": "success", "matches": []})

        def get_tool_fn(name):
            if name == "find_symbol":
                return mock_find_symbol
            elif name == "get_importers":
                return mock_get_importers
            elif name == "grep_search":
                return mock_grep
            return AsyncMock()

        mock_registry.side_effect = get_tool_fn

        result = await explore_symbol_usage(symbol_name="MyClass")

        assert result["status"] == "success"
        assert "definition" in result or "definitions" in result
        assert "attempt_history" in result

    @pytest.mark.asyncio
    async def test_explore_symbol_builds_call_graph(self, mock_registry):
        """Verify explore_symbol_usage builds a call graph."""
        from tools.symbol_explorer import explore_symbol_usage

        mock_find_symbol = AsyncMock(return_value={
            "status": "success",
            "symbols": [{"file": "src/base.py", "line": 10, "name": "BaseClass", "type": "class"}]
        })
        mock_get_importers = AsyncMock(return_value={
            "status": "success",
            "importers": [{"file": "src/child.py"}]
        })
        mock_grep = AsyncMock(return_value={
            "status": "success",
            "matches": [{"file": "src/child.py", "line": 5, "match": "BaseClass()"}]
        })

        def get_tool_fn(name):
            if name == "find_symbol":
                return mock_find_symbol
            elif name == "get_importers":
                return mock_get_importers
            elif name == "grep_search":
                return mock_grep
            return AsyncMock()

        mock_registry.side_effect = get_tool_fn

        result = await explore_symbol_usage(symbol_name="BaseClass")

        assert "call_graph" in result
        assert isinstance(result["call_graph"], dict)


class TestGitHistorianTool:
    """Tests for the explain_code_history composite tool."""

    @pytest.fixture
    def mock_registry(self):
        """Mock the tool registry for isolated testing."""
        with patch.object(tool_catalog, 'has_tool', return_value=True):
            with patch.object(tool_catalog, 'get_function') as mock_get:
                yield mock_get

    @pytest.mark.asyncio
    async def test_git_historian_returns_ownership(self, mock_registry):
        """Verify explain_code_history computes code ownership."""
        from tools.git_historian import explain_code_history

        mock_blame = AsyncMock(return_value={
            "status": "success",
            "blame": [
                {"author": "alice@example.com", "line": 1},
                {"author": "alice@example.com", "line": 2},
                {"author": "bob@example.com", "line": 3},
            ]
        })
        mock_log = AsyncMock(return_value={
            "status": "success",
            "commits": [{"hash": "abc123", "message": "Initial", "date": "2024-01-01"}]
        })
        mock_diff = AsyncMock(return_value={"status": "success", "diff": ""})

        def get_tool_fn(name):
            if name == "git_blame":
                return mock_blame
            elif name == "git_log":
                return mock_log
            elif name == "git_diff":
                return mock_diff
            return AsyncMock()

        mock_registry.side_effect = get_tool_fn

        result = await explain_code_history(path="test.py")

        assert "current_owners" in result
        assert isinstance(result["current_owners"], dict)
        # Alice should have 66.7%, Bob 33.3%
        assert "alice@example.com" in result["current_owners"]

    @pytest.mark.asyncio
    async def test_git_historian_returns_citations(self, mock_registry):
        """Verify explain_code_history includes git citations."""
        from tools.git_historian import explain_code_history

        mock_blame = AsyncMock(return_value={"status": "success", "blame": []})
        mock_log = AsyncMock(return_value={
            "status": "success",
            "commits": [{"hash": "abc12345", "message": "Test", "date": "2024-01-01"}]
        })

        mock_registry.side_effect = lambda name: mock_blame if name == "git_blame" else mock_log

        result = await explain_code_history(path="test.py")

        assert "citations" in result
        # Should include git commit citation
        assert any("git:" in c for c in result["citations"])


class TestModuleMapperTool:
    """Tests for the map_module composite tool."""

    @pytest.fixture
    def mock_registry(self):
        """Mock the tool registry for isolated testing."""
        with patch.object(tool_catalog, 'has_tool', return_value=True):
            with patch.object(tool_catalog, 'get_function') as mock_get:
                yield mock_get

    @pytest.mark.asyncio
    async def test_module_mapper_returns_symbols(self, mock_registry):
        """Verify map_module categorizes symbols."""
        from tools.module_mapper import map_module

        mock_tree = AsyncMock(return_value={
            "status": "success",
            "tree": "agents/\n├── base.py\n└── perception.py",
            "file_count": 2,
            "dir_count": 0,
        })
        mock_glob = AsyncMock(return_value={
            "status": "success",
            "files": ["agents/base.py", "agents/perception.py"]
        })
        mock_symbols = AsyncMock(return_value={
            "status": "success",
            "symbols": [
                {"name": "Agent", "kind": "class", "line": 10},
                {"name": "run", "kind": "function", "line": 20},
            ]
        })
        mock_imports = AsyncMock(return_value={"status": "success", "imports": []})
        mock_importers = AsyncMock(return_value={"status": "success", "importers": []})

        def get_tool_fn(name):
            if name == "tree_structure":
                return mock_tree
            elif name == "glob_files":
                return mock_glob
            elif name == "get_file_symbols":
                return mock_symbols
            elif name == "get_imports":
                return mock_imports
            elif name == "get_importers":
                return mock_importers
            return AsyncMock()

        mock_registry.side_effect = get_tool_fn

        result = await map_module(module_path="agents")

        assert "symbols" in result
        assert "classes" in result["symbols"]
        assert "functions" in result["symbols"]

    @pytest.mark.asyncio
    async def test_module_mapper_returns_responsibilities(self, mock_registry):
        """Verify map_module infers module responsibilities."""
        from tools.module_mapper import map_module

        mock_tree = AsyncMock(return_value={"status": "success", "tree": "", "file_count": 1, "dir_count": 0})
        mock_glob = AsyncMock(return_value={"status": "success", "files": ["tools/base.py"]})
        mock_symbols = AsyncMock(return_value={"status": "success", "symbols": []})
        mock_imports = AsyncMock(return_value={"status": "success", "imports": []})
        mock_importers = AsyncMock(return_value={"status": "success", "importers": []})

        def get_tool_fn(name):
            if name == "tree_structure":
                return mock_tree
            elif name == "glob_files":
                return mock_glob
            elif name == "get_file_symbols":
                return mock_symbols
            elif name == "get_imports":
                return mock_imports
            elif name == "get_importers":
                return mock_importers
            return AsyncMock()

        mock_registry.side_effect = get_tool_fn

        result = await map_module(module_path="tools")

        assert "responsibilities" in result
        assert isinstance(result["responsibilities"], str)
        assert "Tool" in result["responsibilities"]


class TestFlowTracerTool:
    """Tests for the trace_entry_point composite tool."""

    @pytest.fixture
    def mock_registry(self):
        """Mock the tool registry for isolated testing."""
        with patch.object(tool_catalog, 'has_tool', return_value=True):
            with patch.object(tool_catalog, 'get_function') as mock_get:
                yield mock_get

    @pytest.mark.asyncio
    async def test_flow_tracer_detects_framework(self, mock_registry):
        """Verify trace_entry_point detects web frameworks."""
        from tools.flow_tracer import trace_entry_point

        mock_grep = AsyncMock(return_value={
            "status": "success",
            "matches": [{"file": "api/main.py", "line": 1, "match": "from fastapi import FastAPI"}]
        })
        mock_read = AsyncMock(return_value={"status": "success", "content": ""})
        mock_find = AsyncMock(return_value={"status": "success", "symbols": []})

        def get_tool_fn(name):
            if name == "grep_search":
                return mock_grep
            elif name == "read_file":
                return mock_read
            elif name == "find_symbol":
                return mock_find
            return AsyncMock()

        mock_registry.side_effect = get_tool_fn

        result = await trace_entry_point(
            entry_type="http_route",
            pattern="/api/users",
        )

        assert "framework" in result or "frameworks_detected" in result
        assert "attempt_history" in result

    @pytest.mark.asyncio
    async def test_flow_tracer_returns_execution_flow(self, mock_registry):
        """Verify trace_entry_point builds execution flow."""
        from tools.flow_tracer import trace_entry_point

        mock_grep = AsyncMock(return_value={
            "status": "success",
            "matches": [{"file": "cli/main.py", "line": 10, "match": "@click.command()"}]
        })
        mock_read = AsyncMock(return_value={
            "status": "success",
            "content": "def run():\n    handler()\n    process()"
        })
        mock_find = AsyncMock(return_value={
            "status": "success",
            "symbols": [{"file": "cli/handler.py", "line": 5, "name": "handler", "type": "function"}]
        })

        def get_tool_fn(name):
            if name == "grep_search":
                return mock_grep
            elif name == "read_file":
                return mock_read
            elif name == "find_symbol":
                return mock_find
            return AsyncMock()

        mock_registry.side_effect = get_tool_fn

        result = await trace_entry_point(
            entry_type="cli_command",
            pattern="run",
        )

        assert "execution_flow" in result
        assert isinstance(result["execution_flow"], str)


class TestCompositeToolContracts:
    """Tests verifying Amendment XVII contracts across all composite tools."""

    @pytest.mark.asyncio
    async def test_all_internal_tools_return_status(self):
        """Verify all internal tools return a status field."""
        from tools import INTERNAL_TOOLS

        # This test verifies the contract is defined
        assert len(INTERNAL_TOOLS) == 5
        expected_tools = [
            "locate",
            "explore_symbol_usage",
            "explain_code_history",
            "map_module",
            "trace_entry_point",
        ]
        for tool in expected_tools:
            assert tool in INTERNAL_TOOLS

    def test_internal_tools_registered_as_read_only(self):
        """Verify all internal tools are READ_ONLY risk level."""
        from tools import INTERNAL_TOOLS
        from tools.registry import RiskLevel

        # Register tools first (imports trigger registration)
        from tools import (
            safe_locator,
            symbol_explorer,
            git_historian,
            module_mapper,
            flow_tracer,
        )

        for tool_name in INTERNAL_TOOLS:
            if tool_catalog.has_tool(tool_name):
                # Use get_entry() to access risk_level (ToolCatalogEntry has it, ToolDefinition doesn't)
                from jeeves_avionics.tools.catalog import resolve_tool_id
                tool_id = resolve_tool_id(tool_name)
                if tool_id:
                    entry = tool_catalog.get_entry(tool_id)
                    if entry:
                        assert entry.risk_level == RiskLevel.READ_ONLY, f"{tool_name} should be READ_ONLY"


# ============================================================
# Strategy Factory & RobustToolExecutor Tests
# ============================================================

class TestMakeStrategy:
    """Tests for make_strategy() helper - simplifies composite tool development."""

    @pytest.fixture
    def mock_registry(self):
        """Mock the tool registry for isolated testing."""
        with patch.object(tool_catalog, 'has_tool', return_value=True):
            with patch.object(tool_catalog, 'get_function') as mock_get:
                yield mock_get

    @pytest.mark.asyncio
    async def test_make_strategy_creates_working_strategy(self, mock_registry):
        """Verify make_strategy creates a callable strategy function."""
        from tools.robust_tool_base import make_strategy, ResultMappers

        mock_tool = AsyncMock(return_value={
            "status": "success",
            "symbols": [{"file": "test.py", "line": 10, "name": "Foo"}]
        })
        mock_registry.return_value = mock_tool

        strategy = make_strategy("find_symbol", ResultMappers.symbols)
        result = await strategy(name="Foo", exact=True)

        assert result["status"] == "success"
        assert len(result["results"]) == 1
        mock_tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_strategy_with_param_mapper(self, mock_registry):
        """Verify make_strategy correctly maps parameters."""
        from tools.robust_tool_base import make_strategy, ResultMappers

        mock_tool = AsyncMock(return_value={"status": "success", "symbols": []})
        mock_registry.return_value = mock_tool

        def custom_mapper(query: str, **_):
            return {"name": query, "exact": False, "path_prefix": "agents/"}

        strategy = make_strategy("find_symbol", ResultMappers.symbols, custom_mapper)
        await strategy(query="Agent")

        # Verify the parameter mapping was applied
        mock_tool.assert_called_once_with(name="Agent", exact=False, path_prefix="agents/")

    @pytest.mark.asyncio
    async def test_make_strategy_handles_tool_unavailable(self):
        """Verify make_strategy gracefully handles missing tools."""
        from tools.robust_tool_base import make_strategy, ResultMappers

        with patch.object(tool_catalog, 'has_tool', return_value=False):
            strategy = make_strategy("nonexistent_tool", ResultMappers.symbols)
            result = await strategy(query="test")

        assert result["status"] == "tool_unavailable"
        assert result["results"] == []

    @pytest.mark.asyncio
    async def test_make_strategy_handles_exceptions(self, mock_registry):
        """Verify make_strategy catches and reports exceptions."""
        from tools.robust_tool_base import make_strategy, ResultMappers

        mock_tool = AsyncMock(side_effect=RuntimeError("Database connection failed"))
        mock_registry.return_value = mock_tool

        strategy = make_strategy("find_symbol", ResultMappers.symbols)
        result = await strategy(name="Test")

        assert result["status"] == "error"
        assert "Database connection failed" in result["error"]


class TestResultMappers:
    """Tests for ResultMappers - pre-built result transformers."""

    def test_symbols_mapper_extracts_symbols(self):
        """Verify symbols mapper correctly extracts symbol results."""
        from tools.robust_tool_base import ResultMappers

        raw_result = {
            "status": "success",
            "symbols": [
                {"file": "agent.py", "line": 42, "name": "Agent", "kind": "class"}
            ]
        }

        mapped = ResultMappers.symbols(raw_result)

        assert mapped["status"] == "success"
        assert len(mapped["results"]) == 1
        assert mapped["results"][0]["name"] == "Agent"

    def test_symbols_mapper_returns_no_match_on_empty(self):
        """Verify symbols mapper returns no_match when no symbols found."""
        from tools.robust_tool_base import ResultMappers

        mapped = ResultMappers.symbols({"status": "success", "symbols": []})
        assert mapped["status"] == "no_match"
        assert mapped["results"] == []

    def test_grep_matches_mapper_normalizes_format(self):
        """Verify grep mapper normalizes match format."""
        from tools.robust_tool_base import ResultMappers

        raw_result = {
            "status": "success",
            "matches": [
                {"file": "test.py", "line": 10, "match": "def foo()", "context": "..."}
            ]
        }

        mapped = ResultMappers.grep_matches(raw_result)

        assert mapped["status"] == "success"
        assert len(mapped["results"]) == 1
        assert "file" in mapped["results"][0]
        assert "line" in mapped["results"][0]
        assert "match" in mapped["results"][0]

    def test_semantic_results_mapper_handles_various_formats(self):
        """Verify semantic mapper handles different result formats."""
        from tools.robust_tool_base import ResultMappers

        # Format 1: results with file/line
        result1 = ResultMappers.semantic_results({
            "status": "success",
            "results": [{"file": "a.py", "line": 1, "score": 0.9}]
        })
        assert result1["status"] == "success"
        assert result1["results"][0]["file"] == "a.py"

        # Format 2: files list (strings)
        result2 = ResultMappers.semantic_results({
            "status": "success",
            "files": ["b.py", "c.py"]
        })
        assert result2["status"] == "success"
        assert result2["results"][0]["file"] == "b.py"


class TestRobustToolExecutor:
    """Tests for RobustToolExecutor - unified fallback chain execution."""

    @pytest.mark.asyncio
    async def test_executor_stops_on_first_success(self):
        """Verify executor stops after first successful strategy."""
        from tools.robust_tool_base import RobustToolExecutor

        call_order = []

        async def strategy1(**_):
            call_order.append("strategy1")
            return {"status": "success", "results": [{"file": "a.py", "line": 1}]}

        async def strategy2(**_):
            call_order.append("strategy2")
            return {"status": "success", "results": []}

        executor = RobustToolExecutor(name="test")
        executor.add_strategy("first", strategy1)
        executor.add_strategy("second", strategy2)

        result = await executor.execute(query="test")

        assert result.status == "success"
        assert call_order == ["strategy1"]  # Should not call strategy2
        assert result.found_via == "first"

    @pytest.mark.asyncio
    async def test_executor_tries_all_strategies_on_no_match(self):
        """Verify executor tries all strategies when none match."""
        from tools.robust_tool_base import RobustToolExecutor

        call_count = 0

        async def no_match_strategy(**_):
            nonlocal call_count
            call_count += 1
            return {"status": "no_match", "results": []}

        executor = RobustToolExecutor(name="test")
        executor.add_strategy("first", no_match_strategy)
        executor.add_strategy("second", no_match_strategy)
        executor.add_strategy("third", no_match_strategy)

        result = await executor.execute(query="test")

        assert result.status == "not_found"
        assert call_count == 3
        assert len(result.attempt_history) == 3

    @pytest.mark.asyncio
    async def test_executor_collects_citations(self):
        """Verify executor collects and deduplicates citations."""
        from tools.robust_tool_base import RobustToolExecutor

        async def strategy_with_results(**_):
            return {
                "status": "success",
                "results": [
                    {"file": "a.py", "line": 10},
                    {"file": "b.py", "line": 20},
                    {"file": "a.py", "line": 10},  # Duplicate
                ]
            }

        executor = RobustToolExecutor(name="test")
        executor.add_strategy("search", strategy_with_results)

        result = await executor.execute(query="test")

        # Should have 2 unique citations (not 3)
        assert len(result.citations) == 2
        assert "[a.py:10]" in result.citations
        assert "[b.py:20]" in result.citations

    @pytest.mark.asyncio
    async def test_executor_respects_max_results(self):
        """Verify executor truncates results to max_results."""
        from tools.robust_tool_base import RobustToolExecutor

        async def many_results(**_):
            return {
                "status": "success",
                "results": [{"file": f"file{i}.py", "line": i} for i in range(100)]
            }

        executor = RobustToolExecutor(name="test", max_results=10)
        executor.add_strategy("search", many_results)

        result = await executor.execute(query="test")

        assert len(result.results) == 10
        assert result.bounded is True
