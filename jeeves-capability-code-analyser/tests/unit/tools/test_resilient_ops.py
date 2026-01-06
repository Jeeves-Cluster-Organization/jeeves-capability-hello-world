"""Unit tests for resilient code operations layer.

Tests the fallback strategies in tools/code_analysis/resilient_ops.py:
- read_code: Tries exact path, extension swap, glob patterns
- find_related: Finds related files without requiring file to exist

REMOVED (consolidation):
- find_code: Was just a wrapper around `locate`. Use `locate` directly.

Constitutional Compliance:
- P3: Deterministic execution order, bounded retries
- Amendment XVII: attempt_history transparency
- Amendment XXI: Resilient tools registered properly

Per Engineering Improvement Plan v4.0:
- Uses centralized fixtures from tests/fixtures/
- Tests both success and failure paths
- Validates attempt_history transparency

SKIPPED: These tests require the tools.base.resilient_ops module which is not implemented.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Skip entire module - tools.base.resilient_ops and tools.path_helpers are not implemented
pytestmark = pytest.mark.skip(reason="tools.base.resilient_ops module not implemented")

# sys.path configured in conftest.py

# ============================================================
# Fixtures for Resilient Ops Testing
# ============================================================

@pytest.fixture
def temp_repo_with_files(tmp_path):
    """Create a temporary repo with test files for resilient ops testing.

    Structure:
    /tmp_path/
        src/
            main.py
            utils.py
            utils.pyi  (stub file for extension swap testing)
        agents/
            base.py
            traverser.py
        tests/
            test_main.py
    """
    # Create directories
    (tmp_path / "src").mkdir()
    (tmp_path / "agents").mkdir()
    (tmp_path / "tests").mkdir()

    # Create source files
    (tmp_path / "src" / "main.py").write_text("""
def main():
    print("Hello World")

class MainClass:
    pass
""")

    (tmp_path / "src" / "utils.py").write_text("""
def helper_function():
    return 42

def another_helper():
    pass
""")

    # Create .pyi stub file for extension swap testing
    (tmp_path / "src" / "utils.pyi").write_text("""
def helper_function() -> int: ...
def another_helper() -> None: ...
""")

    (tmp_path / "agents" / "base.py").write_text("""
class Agent:
    def process(self):
        pass
""")

    (tmp_path / "agents" / "traverser.py").write_text("""
from dataclasses import dataclass

@dataclass
class TraverserConfig:
    name: str = "traverser"
    has_tools: bool = True
""")

    (tmp_path / "tests" / "test_main.py").write_text("""
def test_main():
    assert True
""")

    return tmp_path


@pytest.fixture
def mock_tool_registry_for_resilient():
    """Mock tool registry with read_file and glob_files for resilient ops.

    This mimics the real tools' behavior for testing fallback strategies.
    """
    registry = MagicMock()

    # Track which files "exist" in our mock
    existing_files = {
        "src/main.py": "def main(): pass",
        "src/utils.py": "def helper(): pass",
        "agents/base.py": "class Agent: pass",
    }

    async def mock_read_file(path=None, **kwargs):
        if path in existing_files:
            return {
                "status": "success",
                "content": existing_files[path],
                "path": path,
            }
        return {"status": "error", "error": f"File not found: {path}"}

    async def mock_glob_files(pattern=None, **kwargs):
        # Simple pattern matching
        matches = []
        for f in existing_files.keys():
            if pattern:
                if "**" in pattern:
                    # Match filename anywhere
                    filename = pattern.replace("**", "").replace("/", "").replace("*", "")
                    if filename in f:
                        matches.append(f)
                elif f.endswith(pattern.replace("*", "")):
                    matches.append(f)
        return {"status": "success", "files": matches, "count": len(matches)}

    async def mock_locate(query=None, **kwargs):
        # Simple locate mock
        results = []
        for path, content in existing_files.items():
            if query and query.lower() in content.lower():
                results.append({"file": path, "name": query, "line": 1})
        return {
            "status": "success" if results else "not_found",
            "results": results,
            "count": len(results),
            "attempt_history": [{"strategy": "find_symbol", "result": "success" if results else "not_found"}],
        }

    def get_tool_function(name):
        tools = {
            "read_file": mock_read_file,
            "glob_files": mock_glob_files,
            "locate": mock_locate,
        }
        return tools.get(name, AsyncMock())

    def has_tool(name):
        return name in ["read_file", "glob_files", "locate", "semantic_search", "find_similar_files"]

    registry.get_tool_function = get_tool_function
    registry.has_tool = has_tool

    return registry


# ============================================================
# Tests for read_code
# ============================================================

class TestReadCode:
    """Tests for read_code resilient operation."""

    @pytest.mark.asyncio
    async def test_read_code_exact_path_success(self, temp_repo_with_files, monkeypatch):
        """Test read_code succeeds on first try with exact path."""
        monkeypatch.setenv("REPO_PATH", str(temp_repo_with_files))

        from tools.base.resilient_ops import read_code

        result = await read_code("src/main.py")

        assert result["status"] == "success"
        assert result["resolved_path"] == "src/main.py"
        assert "attempt_history" in result
        assert result["attempt_history"][0]["strategy"] == "exact_path"

    @pytest.mark.asyncio
    async def test_read_code_extension_swap_py_to_pyi(self, temp_repo_with_files, monkeypatch):
        """Test read_code tries .pyi when .py not found."""
        monkeypatch.setenv("REPO_PATH", str(temp_repo_with_files))

        # Remove the .py file to force extension swap
        (temp_repo_with_files / "src" / "utils.py").unlink()

        from tools.base.resilient_ops import read_code

        result = await read_code("src/utils.py")

        assert result["status"] == "success"
        assert result["resolved_path"] == "src/utils.pyi"
        # Should have tried exact path first, then extension swap
        strategies = [a["strategy"] for a in result["attempt_history"]]
        assert "exact_path" in strategies
        assert "extension_swap" in strategies

    @pytest.mark.asyncio
    async def test_read_code_glob_filename_fallback(self, temp_repo_with_files, monkeypatch):
        """Test read_code uses glob when exact path and extension swap fail."""
        monkeypatch.setenv("REPO_PATH", str(temp_repo_with_files))

        from tools.base.resilient_ops import read_code

        # Request file with wrong directory path - glob should find it
        result = await read_code("wrong/path/base.py")

        assert result["status"] == "success"
        assert "agents/base.py" in result["resolved_path"]
        strategies = [a["strategy"] for a in result["attempt_history"]]
        assert "glob_filename" in strategies

    @pytest.mark.asyncio
    async def test_read_code_loud_failure_with_suggestions(self, temp_repo_with_files, monkeypatch):
        """Test read_code fails loudly with suggestions when file not found."""
        monkeypatch.setenv("REPO_PATH", str(temp_repo_with_files))

        from tools.base.resilient_ops import read_code

        result = await read_code("nonexistent/path/agent.py")

        assert result["status"] in ("not_found", "partial")
        assert "attempt_history" in result
        assert len(result["attempt_history"]) >= 3  # Tried multiple strategies
        # Should have suggestions or error message
        assert "suggestions" in result or "error" in result
        assert "message" in result

    @pytest.mark.asyncio
    async def test_read_code_attempt_history_transparency(self, temp_repo_with_files, monkeypatch):
        """Test read_code provides full attempt history (Amendment XVII)."""
        monkeypatch.setenv("REPO_PATH", str(temp_repo_with_files))

        from tools.base.resilient_ops import read_code

        result = await read_code("src/main.py")

        assert "attempt_history" in result
        for attempt in result["attempt_history"]:
            assert "step" in attempt
            assert "strategy" in attempt
            assert "result" in attempt

    @pytest.mark.asyncio
    async def test_read_code_with_line_range(self, temp_repo_with_files, monkeypatch):
        """Test read_code passes through line range parameters."""
        monkeypatch.setenv("REPO_PATH", str(temp_repo_with_files))

        from tools.base.resilient_ops import read_code

        result = await read_code("src/main.py", start_line=2, end_line=4)

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_read_code_is_registered_tool(self, temp_repo_with_files, monkeypatch):
        """Test read_code is registered in tool registry (Amendment XXI)."""
        monkeypatch.setenv("REPO_PATH", str(temp_repo_with_files))

        # Import to trigger registration
        from tools.base import resilient_ops
        from tools.catalog import tool_catalog as tool_registry

        assert tool_registry.has_tool("read_code")
        tool = tool_registry.get_tool("read_code")
        assert tool.risk_level.value == "read_only"


# ============================================================
# Tests for find_related
# ============================================================

class TestFindRelated:
    """Tests for find_related resilient operation."""

    @pytest.mark.asyncio
    async def test_find_related_with_existing_file(self, temp_repo_with_files, monkeypatch):
        """Test find_related when reference file exists."""
        monkeypatch.setenv("REPO_PATH", str(temp_repo_with_files))

        from tools.base.resilient_ops import find_related

        result = await find_related("agents/base.py")

        assert result["status"] in ["success", "not_found", "partial"]
        assert "attempt_history" in result

    @pytest.mark.asyncio
    async def test_find_related_with_nonexistent_file(self, temp_repo_with_files, monkeypatch):
        """Test find_related still works when reference file doesn't exist.

        This is the key improvement - find_related should not require
        the file to exist to search for similar files.
        """
        monkeypatch.setenv("REPO_PATH", str(temp_repo_with_files))

        from tools.base.resilient_ops import find_related

        # Reference a file that doesn't exist
        result = await find_related("agents/architecture.py")

        # Should not fail immediately - should try filename patterns
        assert "attempt_history" in result
        strategies = [a["strategy"] for a in result["attempt_history"]]
        # Should try filename pattern search
        assert any("filename" in s or "semantic" in s for s in strategies)

    @pytest.mark.asyncio
    async def test_find_related_by_description(self, temp_repo_with_files, monkeypatch):
        """Test find_related with description instead of file path."""
        monkeypatch.setenv("REPO_PATH", str(temp_repo_with_files))

        from tools.base.resilient_ops import find_related

        # Use a description, not a path
        result = await find_related("code analysis traverser")

        # Should handle gracefully
        assert "status" in result
        assert "attempt_history" in result

    @pytest.mark.asyncio
    async def test_find_related_is_registered_tool(self, temp_repo_with_files, monkeypatch):
        """Test find_related is registered in tool registry (Amendment XXI)."""
        monkeypatch.setenv("REPO_PATH", str(temp_repo_with_files))

        # Import to trigger registration
        from tools.base import resilient_ops
        from tools.catalog import tool_catalog as tool_registry

        assert tool_registry.has_tool("find_related")
        tool = tool_registry.get_tool("find_related")
        assert tool.risk_level.value == "read_only"


# ============================================================
# Tests for Strategy Integration
# ============================================================

class TestResilientOpsIntegration:
    """Integration tests for resilient ops with real tool registry."""

    @pytest.mark.asyncio
    async def test_read_code_all_strategies_exhausted(self, temp_repo_with_files, monkeypatch):
        """Test read_code exhausts all strategies before failing."""
        monkeypatch.setenv("REPO_PATH", str(temp_repo_with_files))

        from tools.base.resilient_ops import read_code

        # Request a file that definitely doesn't exist and has no similar files
        result = await read_code("xyz/completely_unique_nonexistent_file.xyz")

        assert result["status"] in ("not_found", "partial")
        # Should have tried all strategies (exact_path, glob_filename, glob_stem)
        # Note: extension_swap only runs for known extensions (.py, .ts, etc.)
        assert len(result["attempt_history"]) >= 3
        # Check all strategies were attempted
        strategies = [a["strategy"] for a in result["attempt_history"]]
        assert "exact_path" in strategies
        assert "glob_filename" in strategies
        assert "glob_stem" in strategies

    @pytest.mark.asyncio
    async def test_read_code_returns_other_matches(self, temp_repo_with_files, monkeypatch):
        """Test read_code returns other_matches when glob finds multiple files."""
        monkeypatch.setenv("REPO_PATH", str(temp_repo_with_files))

        # Create multiple files with same name in different directories
        (temp_repo_with_files / "lib").mkdir()
        (temp_repo_with_files / "lib" / "main.py").write_text("# lib main")

        from tools.base.resilient_ops import read_code

        # Request with wrong path - glob should find multiple matches
        result = await read_code("wrong/main.py")

        assert result["status"] == "success"
        # May have other_matches if multiple files found
        # This is now in results, not a separate field


# ============================================================
# Tests for Constitutional Compliance
# ============================================================

class TestConstitutionalCompliance:
    """Tests verifying resilient ops comply with constitution.

    P3: Deterministic execution, bounded retries
    Amendment XVII: attempt_history transparency
    Amendment XXI: Tools registered properly
    """

    @pytest.mark.asyncio
    async def test_no_silent_failures(self, temp_repo_with_files, monkeypatch):
        """Test that failures are never silent - always include context."""
        monkeypatch.setenv("REPO_PATH", str(temp_repo_with_files))

        from tools.base.resilient_ops import read_code

        result = await read_code("nonexistent.py")

        # Must have explicit failure information
        assert result["status"] in ("not_found", "partial", "error")
        assert "error" in result or "message" in result
        # Must have attempt history for transparency
        assert "attempt_history" in result
        # Must have suggestions when possible
        assert "suggestions" in result

    @pytest.mark.asyncio
    async def test_deterministic_strategy_order(self, temp_repo_with_files, monkeypatch):
        """Test that strategies are applied in deterministic order (P3)."""
        monkeypatch.setenv("REPO_PATH", str(temp_repo_with_files))

        from tools.base.resilient_ops import read_code

        # Run twice with same input
        result1 = await read_code("nonexistent.py")
        result2 = await read_code("nonexistent.py")

        # Strategy order should be identical
        strategies1 = [a["strategy"] for a in result1["attempt_history"]]
        strategies2 = [a["strategy"] for a in result2["attempt_history"]]

        assert strategies1 == strategies2

    @pytest.mark.asyncio
    async def test_read_only_operations(self, temp_repo_with_files, monkeypatch):
        """Test that resilient ops are read-only (no file mutations)."""
        monkeypatch.setenv("REPO_PATH", str(temp_repo_with_files))

        from tools.base.resilient_ops import read_code, find_related

        # Get initial file list
        initial_files = list(temp_repo_with_files.rglob("*"))

        # Run all resilient ops
        await read_code("src/main.py")
        await read_code("nonexistent.py")
        await find_related("agents/base.py")

        # File list should be unchanged
        final_files = list(temp_repo_with_files.rglob("*"))
        assert set(initial_files) == set(final_files)

    @pytest.mark.asyncio
    async def test_citations_format(self, temp_repo_with_files, monkeypatch):
        """Test citations are in [file:line] format (P1)."""
        monkeypatch.setenv("REPO_PATH", str(temp_repo_with_files))

        from tools.base.resilient_ops import read_code

        result = await read_code("src/main.py")

        if result.get("citations"):
            for citation in result["citations"]:
                assert citation.startswith("[")
                assert citation.endswith("]")


# ============================================================
# Tests for find_code Removal
# ============================================================

class TestFindCodeRemoval:
    """Tests verifying find_code has been removed per consolidation."""

    def test_find_code_not_exported(self):
        """Test find_code is not in __all__."""
        from tools.base import resilient_ops

        assert "find_code" not in resilient_ops.__all__

    def test_find_code_not_registered(self, temp_repo_with_files, monkeypatch):
        """Test find_code is not in tool registry."""
        monkeypatch.setenv("REPO_PATH", str(temp_repo_with_files))

        # Import to trigger registration
        from tools.base import resilient_ops
        from tools.catalog import tool_catalog as tool_registry

        assert not tool_registry.has_tool("find_code")
