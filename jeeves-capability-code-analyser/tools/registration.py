"""
Tool Registration - Single entry point for all tool registration.

Phase 2 Constitutional Compliance:
- Uses tool_catalog as the SINGLE source of truth
- No auto-registration at import time (Phase 4)
- All tools registered via explicit register_all_tools() call

This module replaces tools/base/registry.py (now deleted).
"""

from typing import Any, Callable, Dict, List, Optional

from typing import Optional
from protocols import RiskLevel, ToolCategory, LoggerProtocol

# Import from capability's own catalog (not from core)
from .catalog import tool_catalog, ToolId


def register_all_tools(logger: Optional[LoggerProtocol] = None) -> Dict[str, Any]:
    """
    Register all capability tools with the capability's tool_catalog.

    This is the SINGLE entry point for tool registration.
    Called at capability bootstrap time, NOT at import time.

    Args:
        logger: Optional logger instance. If not provided, uses structlog.

    Returns:
        Dict with registration results
    """
    if logger is None:
        import structlog
        _logger = structlog.get_logger("tools.registration")
    else:
        _logger = logger

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
    tool_catalog.register(
        tool_id=ToolId.SEARCH_CODE.value,
        func=search_code,
        description="Search for code - ALWAYS searches, never assumes paths exist. Use for symbols, keywords, queries.",
        parameters={"query": "string", "search_type": "string?"},
        category=ToolCategory.UNIFIED.value,
        risk_level=RiskLevel.READ_ONLY.value,
    )
    registered.append("search_code")

    # ═══════════════════════════════════════════════════════════════════════════
    # COMPOSITE TOOLS (Amendment XVII)
    # ═══════════════════════════════════════════════════════════════════════════
    tool_catalog.register(
        tool_id=ToolId.LOCATE.value,
        func=locate,
        description="Locate code elements with deterministic fallback strategy",
        parameters={"query": "string", "search_type": "string?", "scope": "string?"},
        category=ToolCategory.COMPOSITE.value,
        risk_level=RiskLevel.READ_ONLY.value,
    )
    registered.append("locate")

    tool_catalog.register(
        tool_id=ToolId.EXPLORE_SYMBOL_USAGE.value,
        func=explore_symbol_usage,
        description="Find symbol definition and all usages across codebase",
        parameters={"symbol_name": "string", "context_bounds": "ContextBounds", "trace_depth": "integer?", "include_tests": "boolean?"},
        category=ToolCategory.COMPOSITE.value,
        risk_level=RiskLevel.READ_ONLY.value,
    )
    registered.append("explore_symbol_usage")

    tool_catalog.register(
        tool_id=ToolId.MAP_MODULE.value,
        func=map_module,
        description="Map module structure including files, exports, and dependencies",
        parameters={"module_path": "string", "depth": "integer?"},
        category=ToolCategory.COMPOSITE.value,
        risk_level=RiskLevel.READ_ONLY.value,
    )
    registered.append("map_module")

    tool_catalog.register(
        tool_id=ToolId.TRACE_ENTRY_POINT.value,
        func=trace_entry_point,
        description="Trace execution from entry point (HTTP/CLI) to implementation",
        parameters={"entry_point": "string", "max_depth": "integer?"},
        category=ToolCategory.COMPOSITE.value,
        risk_level=RiskLevel.READ_ONLY.value,
    )
    registered.append("trace_entry_point")

    tool_catalog.register(
        tool_id=ToolId.EXPLAIN_CODE_HISTORY.value,
        func=explain_code_history,
        description="Generate narrative of code changes using git history",
        parameters={"path": "string", "since": "string?"},
        category=ToolCategory.COMPOSITE.value,
        risk_level=RiskLevel.READ_ONLY.value,
    )
    registered.append("explain_code_history")

    # ═══════════════════════════════════════════════════════════════════════════
    # RESILIENT TOOLS (Amendment XXI)
    # ═══════════════════════════════════════════════════════════════════════════
    tool_catalog.register(
        tool_id=ToolId.READ_CODE.value,
        func=read_code,
        description="Read file with retry logic and context-aware truncation",
        parameters={"path": "string", "start_line": "integer?", "end_line": "integer?"},
        category=ToolCategory.RESILIENT.value,
        risk_level=RiskLevel.READ_ONLY.value,
    )
    registered.append("read_code")

    tool_catalog.register(
        tool_id=ToolId.FIND_RELATED.value,
        func=find_related,
        description="Find semantically related files using embeddings",
        parameters={"query": "string", "limit": "integer?"},
        category=ToolCategory.RESILIENT.value,
        risk_level=RiskLevel.READ_ONLY.value,
    )
    registered.append("find_related")

    # ═══════════════════════════════════════════════════════════════════════════
    # STANDALONE TOOLS
    # ═══════════════════════════════════════════════════════════════════════════
    tool_catalog.register(
        tool_id=ToolId.GIT_STATUS.value,
        func=git_status,
        description="Show working tree status - modified, staged, untracked files",
        parameters={},
        category=ToolCategory.STANDALONE.value,
        risk_level=RiskLevel.READ_ONLY.value,
    )
    registered.append("git_status")

    tool_catalog.register(
        tool_id=ToolId.LIST_TOOLS.value,
        func=list_tools,
        description="List all available tools and their descriptions",
        parameters={},
        category=ToolCategory.STANDALONE.value,
        risk_level=RiskLevel.READ_ONLY.value,
    )
    registered.append("list_tools")

    # ═══════════════════════════════════════════════════════════════════════════
    # INTERNAL/BASE TOOLS
    # ═══════════════════════════════════════════════════════════════════════════
    tool_catalog.register(
        tool_id=ToolId.READ_FILE.value,
        func=read_file,
        description="Read file contents with line numbers",
        parameters={"path": "string", "start_line": "integer?", "end_line": "integer?"},
        category=ToolCategory.INTERNAL.value,
        risk_level=RiskLevel.READ_ONLY.value,
    )
    registered.append("read_file")

    tool_catalog.register(
        tool_id=ToolId.GLOB_FILES.value,
        func=glob_files,
        description="Find files matching glob pattern",
        parameters={"pattern": "string", "path": "string?"},
        category=ToolCategory.INTERNAL.value,
        risk_level=RiskLevel.READ_ONLY.value,
    )
    registered.append("glob_files")

    tool_catalog.register(
        tool_id=ToolId.GREP_SEARCH.value,
        func=grep_search,
        description="Search for pattern in files using grep",
        parameters={"pattern": "string", "path": "string?", "max_results": "integer?"},
        category=ToolCategory.INTERNAL.value,
        risk_level=RiskLevel.READ_ONLY.value,
    )
    registered.append("grep_search")

    tool_catalog.register(
        tool_id=ToolId.TREE_STRUCTURE.value,
        func=tree_structure,
        description="Get directory tree structure",
        parameters={"path": "string?", "max_depth": "integer?"},
        category=ToolCategory.INTERNAL.value,
        risk_level=RiskLevel.READ_ONLY.value,
    )
    registered.append("tree_structure")

    tool_catalog.register(
        tool_id=ToolId.FIND_SYMBOL.value,
        func=find_symbol,
        description="Find symbol definitions by name",
        parameters={"name": "string", "kind": "string?", "exact": "boolean?"},
        category=ToolCategory.INTERNAL.value,
        risk_level=RiskLevel.READ_ONLY.value,
    )
    registered.append("find_symbol")

    tool_catalog.register(
        tool_id=ToolId.GET_FILE_SYMBOLS.value,
        func=get_file_symbols,
        description="List all symbols defined in a file",
        parameters={"path": "string", "kind": "string?"},
        category=ToolCategory.INTERNAL.value,
        risk_level=RiskLevel.READ_ONLY.value,
    )
    registered.append("get_file_symbols")

    tool_catalog.register(
        tool_id=ToolId.GET_IMPORTS.value,
        func=get_imports,
        description="Get imports for a file",
        parameters={"path": "string"},
        category=ToolCategory.INTERNAL.value,
        risk_level=RiskLevel.READ_ONLY.value,
    )
    registered.append("get_imports")

    tool_catalog.register(
        tool_id=ToolId.GET_IMPORTERS.value,
        func=get_importers,
        description="Find files that import a given module",
        parameters={"module_name": "string", "exact": "boolean?"},
        category=ToolCategory.INTERNAL.value,
        risk_level=RiskLevel.READ_ONLY.value,
    )
    registered.append("get_importers")

    tool_catalog.register(
        tool_id=ToolId.GIT_LOG.value,
        func=git_log,
        description="Get commit history for file or directory",
        parameters={"path": "string?", "n": "integer?", "since": "string?"},
        category=ToolCategory.INTERNAL.value,
        risk_level=RiskLevel.READ_ONLY.value,
    )
    registered.append("git_log")

    tool_catalog.register(
        tool_id=ToolId.GIT_BLAME.value,
        func=git_blame,
        description="Get line attribution for a file",
        parameters={"path": "string", "start_line": "integer?", "end_line": "integer?"},
        category=ToolCategory.INTERNAL.value,
        risk_level=RiskLevel.READ_ONLY.value,
    )
    registered.append("git_blame")

    tool_catalog.register(
        tool_id=ToolId.GIT_DIFF.value,
        func=git_diff,
        description="Show changes between commits or working tree",
        parameters={"path": "string?", "commit1": "string?", "commit2": "string?"},
        category=ToolCategory.INTERNAL.value,
        risk_level=RiskLevel.READ_ONLY.value,
    )
    registered.append("git_diff")

    tool_catalog.register(
        tool_id=ToolId.SEMANTIC_SEARCH.value,
        func=semantic_search,
        description="Search for code by semantic meaning using embeddings",
        parameters={"query": "string", "limit": "integer?", "languages": "string?"},
        category=ToolCategory.INTERNAL.value,
        risk_level=RiskLevel.READ_ONLY.value,
    )
    registered.append("semantic_search")

    tool_catalog.register(
        tool_id=ToolId.FIND_SIMILAR_FILES.value,
        func=find_similar_files,
        description="Find files similar to a given file",
        parameters={"file_path": "string", "limit": "integer?"},
        category=ToolCategory.INTERNAL.value,
        risk_level=RiskLevel.READ_ONLY.value,
    )
    registered.append("find_similar_files")

    tool_catalog.register(
        tool_id=ToolId.GET_INDEX_STATS.value,
        func=get_index_stats,
        description="Get statistics about the code index",
        parameters={},
        category=ToolCategory.INTERNAL.value,
        risk_level=RiskLevel.READ_ONLY.value,
    )
    registered.append("get_index_stats")

    tool_catalog.register(
        tool_id=ToolId.GET_SESSION_STATE.value,
        func=get_session_state,
        description="Get current session state",
        parameters={"key": "string?"},
        category=ToolCategory.INTERNAL.value,
        risk_level=RiskLevel.READ_ONLY.value,
    )
    registered.append("get_session_state")

    tool_catalog.register(
        tool_id=ToolId.SAVE_SESSION_STATE.value,
        func=save_session_state,
        description="Save data to session state",
        parameters={"key": "string", "value": "any"},
        category=ToolCategory.INTERNAL.value,
        risk_level=RiskLevel.WRITE.value,
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
