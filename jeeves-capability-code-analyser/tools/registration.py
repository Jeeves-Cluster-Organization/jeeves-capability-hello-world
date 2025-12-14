"""
Tool Registration - Single entry point for all tool registration.

Phase 2 Constitutional Compliance:
- Uses tool_catalog as the SINGLE source of truth
- No auto-registration at import time (Phase 4)
- All tools registered via explicit register_all_tools() call

This module replaces tools/base/registry.py (now deleted).
"""

from typing import Any, Callable, Dict, List, Optional

from jeeves_protocols import RiskLevel, ToolCategory
from jeeves_mission_system.contracts import (
    tool_catalog,
    ToolId,
    LoggerProtocol,
)
from jeeves_mission_system.adapters import get_logger


def register_all_tools() -> Dict[str, Any]:
    """
    Register all capability tools with the canonical tool_catalog.

    This is the SINGLE entry point for tool registration.
    Called at capability bootstrap time, NOT at import time.

    Returns:
        Dict with registration results
    """
    _logger = get_logger()

    # Import tool functions (no side effects at import)
    from tools.base.code_tools import read_file, glob_files, grep_search, tree_structure
    from tools.base.index_tools import find_symbol, get_file_symbols, get_imports, get_importers
    from tools.base.git_tools import git_log, git_blame, git_diff, git_status
    from tools.base.semantic_tools import semantic_search, find_similar_files, get_index_stats
    from tools.base.session_tools import get_session_state, save_session_state, list_tools
    from tools.safe_locator import locate
    from tools.symbol_explorer import explore_symbol_usage
    from tools.git_historian import explain_code_history
    from tools.module_mapper import map_module
    from tools.flow_tracer import trace_entry_point
    from tools.base.resilient_ops import read_code, find_related
    from tools.unified_analyzer import search_code

    registered = []

    # ═══════════════════════════════════════════════════════════════════════════
    # PRIMARY SEARCH TOOL - Two-Tool Architecture (Amendment XXII v2)
    # ═══════════════════════════════════════════════════════════════════════════
    tool_catalog.register_function(
        tool_id=ToolId.SEARCH_CODE,
        func=search_code,
        description="Search for code - ALWAYS searches, never assumes paths exist. Use for symbols, keywords, queries.",
        parameters={"query": "string", "search_type": "string?"},
        category=ToolCategory.UNIFIED,
        risk_level=RiskLevel.READ_ONLY,
    )
    registered.append("search_code")

    # ═══════════════════════════════════════════════════════════════════════════
    # COMPOSITE TOOLS (Amendment XVII)
    # ═══════════════════════════════════════════════════════════════════════════
    tool_catalog.register_function(
        tool_id=ToolId.LOCATE,
        func=locate,
        description="Locate code elements with deterministic fallback strategy",
        parameters={"query": "string", "search_type": "string?", "scope": "string?"},
        category=ToolCategory.COMPOSITE,
        risk_level=RiskLevel.READ_ONLY,
    )
    registered.append("locate")

    tool_catalog.register_function(
        tool_id=ToolId.EXPLORE_SYMBOL_USAGE,
        func=explore_symbol_usage,
        description="Find symbol definition and all usages across codebase",
        parameters={"symbol_name": "string", "context_bounds": "ContextBounds", "trace_depth": "integer?", "include_tests": "boolean?"},
        category=ToolCategory.COMPOSITE,
        risk_level=RiskLevel.READ_ONLY,
    )
    registered.append("explore_symbol_usage")

    tool_catalog.register_function(
        tool_id=ToolId.MAP_MODULE,
        func=map_module,
        description="Map module structure including files, exports, and dependencies",
        parameters={"module_path": "string", "depth": "integer?"},
        category=ToolCategory.COMPOSITE,
        risk_level=RiskLevel.READ_ONLY,
    )
    registered.append("map_module")

    tool_catalog.register_function(
        tool_id=ToolId.TRACE_ENTRY_POINT,
        func=trace_entry_point,
        description="Trace execution from entry point (HTTP/CLI) to implementation",
        parameters={"entry_point": "string", "max_depth": "integer?"},
        category=ToolCategory.COMPOSITE,
        risk_level=RiskLevel.READ_ONLY,
    )
    registered.append("trace_entry_point")

    tool_catalog.register_function(
        tool_id=ToolId.EXPLAIN_CODE_HISTORY,
        func=explain_code_history,
        description="Generate narrative of code changes using git history",
        parameters={"path": "string", "since": "string?"},
        category=ToolCategory.COMPOSITE,
        risk_level=RiskLevel.READ_ONLY,
    )
    registered.append("explain_code_history")

    # ═══════════════════════════════════════════════════════════════════════════
    # RESILIENT TOOLS (Amendment XXI)
    # ═══════════════════════════════════════════════════════════════════════════
    tool_catalog.register_function(
        tool_id=ToolId.READ_CODE,
        func=read_code,
        description="Read file with retry logic and context-aware truncation",
        parameters={"path": "string", "start_line": "integer?", "end_line": "integer?"},
        category=ToolCategory.RESILIENT,
        risk_level=RiskLevel.READ_ONLY,
    )
    registered.append("read_code")

    tool_catalog.register_function(
        tool_id=ToolId.FIND_RELATED,
        func=find_related,
        description="Find semantically related files using embeddings",
        parameters={"query": "string", "limit": "integer?"},
        category=ToolCategory.RESILIENT,
        risk_level=RiskLevel.READ_ONLY,
    )
    registered.append("find_related")

    # ═══════════════════════════════════════════════════════════════════════════
    # STANDALONE TOOLS
    # ═══════════════════════════════════════════════════════════════════════════
    tool_catalog.register_function(
        tool_id=ToolId.GIT_STATUS,
        func=git_status,
        description="Show working tree status - modified, staged, untracked files",
        parameters={},
        category=ToolCategory.STANDALONE,
        risk_level=RiskLevel.READ_ONLY,
    )
    registered.append("git_status")

    tool_catalog.register_function(
        tool_id=ToolId.LIST_TOOLS,
        func=list_tools,
        description="List all available tools and their descriptions",
        parameters={},
        category=ToolCategory.STANDALONE,
        risk_level=RiskLevel.READ_ONLY,
    )
    registered.append("list_tools")

    # ═══════════════════════════════════════════════════════════════════════════
    # INTERNAL/BASE TOOLS
    # ═══════════════════════════════════════════════════════════════════════════
    tool_catalog.register_function(
        tool_id=ToolId.READ_FILE,
        func=read_file,
        description="Read file contents with line numbers",
        parameters={"path": "string", "start_line": "integer?", "end_line": "integer?"},
        category=ToolCategory.INTERNAL,
        risk_level=RiskLevel.READ_ONLY,
    )
    registered.append("read_file")

    tool_catalog.register_function(
        tool_id=ToolId.GLOB_FILES,
        func=glob_files,
        description="Find files matching glob pattern",
        parameters={"pattern": "string", "path": "string?"},
        category=ToolCategory.INTERNAL,
        risk_level=RiskLevel.READ_ONLY,
    )
    registered.append("glob_files")

    tool_catalog.register_function(
        tool_id=ToolId.GREP_SEARCH,
        func=grep_search,
        description="Search for pattern in files using grep",
        parameters={"pattern": "string", "path": "string?", "max_results": "integer?"},
        category=ToolCategory.INTERNAL,
        risk_level=RiskLevel.READ_ONLY,
    )
    registered.append("grep_search")

    tool_catalog.register_function(
        tool_id=ToolId.TREE_STRUCTURE,
        func=tree_structure,
        description="Get directory tree structure",
        parameters={"path": "string?", "max_depth": "integer?"},
        category=ToolCategory.INTERNAL,
        risk_level=RiskLevel.READ_ONLY,
    )
    registered.append("tree_structure")

    tool_catalog.register_function(
        tool_id=ToolId.FIND_SYMBOL,
        func=find_symbol,
        description="Find symbol definitions by name",
        parameters={"name": "string", "kind": "string?", "exact": "boolean?"},
        category=ToolCategory.INTERNAL,
        risk_level=RiskLevel.READ_ONLY,
    )
    registered.append("find_symbol")

    tool_catalog.register_function(
        tool_id=ToolId.GET_FILE_SYMBOLS,
        func=get_file_symbols,
        description="List all symbols defined in a file",
        parameters={"path": "string", "kind": "string?"},
        category=ToolCategory.INTERNAL,
        risk_level=RiskLevel.READ_ONLY,
    )
    registered.append("get_file_symbols")

    tool_catalog.register_function(
        tool_id=ToolId.GET_IMPORTS,
        func=get_imports,
        description="Get imports for a file",
        parameters={"path": "string"},
        category=ToolCategory.INTERNAL,
        risk_level=RiskLevel.READ_ONLY,
    )
    registered.append("get_imports")

    tool_catalog.register_function(
        tool_id=ToolId.GET_IMPORTERS,
        func=get_importers,
        description="Find files that import a given module",
        parameters={"module_name": "string", "exact": "boolean?"},
        category=ToolCategory.INTERNAL,
        risk_level=RiskLevel.READ_ONLY,
    )
    registered.append("get_importers")

    tool_catalog.register_function(
        tool_id=ToolId.GIT_LOG,
        func=git_log,
        description="Get commit history for file or directory",
        parameters={"path": "string?", "n": "integer?", "since": "string?"},
        category=ToolCategory.INTERNAL,
        risk_level=RiskLevel.READ_ONLY,
    )
    registered.append("git_log")

    tool_catalog.register_function(
        tool_id=ToolId.GIT_BLAME,
        func=git_blame,
        description="Get line attribution for a file",
        parameters={"path": "string", "start_line": "integer?", "end_line": "integer?"},
        category=ToolCategory.INTERNAL,
        risk_level=RiskLevel.READ_ONLY,
    )
    registered.append("git_blame")

    tool_catalog.register_function(
        tool_id=ToolId.GIT_DIFF,
        func=git_diff,
        description="Show changes between commits or working tree",
        parameters={"path": "string?", "commit1": "string?", "commit2": "string?"},
        category=ToolCategory.INTERNAL,
        risk_level=RiskLevel.READ_ONLY,
    )
    registered.append("git_diff")

    tool_catalog.register_function(
        tool_id=ToolId.SEMANTIC_SEARCH,
        func=semantic_search,
        description="Search for code by semantic meaning using embeddings",
        parameters={"query": "string", "limit": "integer?", "languages": "string?"},
        category=ToolCategory.INTERNAL,
        risk_level=RiskLevel.READ_ONLY,
    )
    registered.append("semantic_search")

    tool_catalog.register_function(
        tool_id=ToolId.FIND_SIMILAR_FILES,
        func=find_similar_files,
        description="Find files similar to a given file",
        parameters={"file_path": "string", "limit": "integer?"},
        category=ToolCategory.INTERNAL,
        risk_level=RiskLevel.READ_ONLY,
    )
    registered.append("find_similar_files")

    tool_catalog.register_function(
        tool_id=ToolId.GET_INDEX_STATS,
        func=get_index_stats,
        description="Get statistics about the code index",
        parameters={},
        category=ToolCategory.INTERNAL,
        risk_level=RiskLevel.READ_ONLY,
    )
    registered.append("get_index_stats")

    tool_catalog.register_function(
        tool_id=ToolId.GET_SESSION_STATE,
        func=get_session_state,
        description="Get current session state",
        parameters={"key": "string?"},
        category=ToolCategory.INTERNAL,
        risk_level=RiskLevel.READ_ONLY,
    )
    registered.append("get_session_state")

    tool_catalog.register_function(
        tool_id=ToolId.SAVE_SESSION_STATE,
        func=save_session_state,
        description="Save data to session state",
        parameters={"key": "string", "value": "any"},
        category=ToolCategory.INTERNAL,
        risk_level=RiskLevel.WRITE,
    )
    registered.append("save_session_state")

    _logger.info(
        "tools_registered_to_catalog",
        count=len(registered),
        tools=registered,
    )

    return {
        "registered": registered,
        "count": len(registered),
        "catalog": tool_catalog,
    }


def get_tool_function(tool_name: str) -> Optional[Callable]:
    """
    Get tool function by name from catalog.

    Args:
        tool_name: Tool name string

    Returns:
        Tool function if found, None otherwise
    """
    try:
        tool_id = ToolId(tool_name)
        return tool_catalog.get_function(tool_id)
    except ValueError:
        return None


def has_tool(tool_name: str) -> bool:
    """
    Check if tool exists in catalog.

    Args:
        tool_name: Tool name string

    Returns:
        True if tool exists
    """
    # ToolCatalog.has_tool() now accepts string directly (ToolRegistryProtocol)
    return tool_catalog.has_tool(tool_name)


def list_registered_tools() -> List[str]:
    """
    List all registered tool names.

    Returns:
        List of tool name strings
    """
    return [tid.value for tid in tool_catalog.list_all_ids()]


__all__ = [
    "register_all_tools",
    "get_tool_function",
    "has_tool",
    "list_registered_tools",
]
