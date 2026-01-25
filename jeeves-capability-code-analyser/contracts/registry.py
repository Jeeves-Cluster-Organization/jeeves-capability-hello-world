"""
Tool Result Schema Registry for Code Analysis Vertical.

This is the Proto-3 local registry - a simple mapping from tool names
to their result TypedDicts. Later, this can be promoted to a global
schema registry with minimal refactoring.

Usage:
    from mission_system.contracts.code_analysis.registry import (
        TOOL_RESULT_SCHEMAS,
        get_schema_for_tool,
        is_composite_tool,
    )

    # Get schema for a tool
    schema = get_schema_for_tool("locate")

    # Check if tool requires attempt_history
    if is_composite_tool("map_module"):
        assert "attempt_history" in result
"""

from typing import Dict, FrozenSet, Optional, Type

from .schemas import (
    BaseToolResult,
    FileListResult,
    SymbolSearchResult,
    GrepSearchResult,
    SemanticSearchResult,
    ModuleMapResult,
    SymbolExplorerResult,
    LocateResult,
    ReadCodeResult,
    FindRelatedResult,
    TreeStructureResult,
)


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

TOOL_RESULT_SCHEMAS: Dict[str, Type] = {
    # ─── BASE TOOLS (Internal) ───
    "glob_files": FileListResult,
    "list_files": FileListResult,
    "tree_structure": TreeStructureResult,
    "find_symbol": SymbolSearchResult,
    "get_file_symbols": SymbolSearchResult,
    "parse_symbols": SymbolSearchResult,
    "grep_search": GrepSearchResult,
    "semantic_search": SemanticSearchResult,
    "find_similar_files": SemanticSearchResult,
    "read_file": ReadCodeResult,  # Base read_file uses same schema

    # ─── COMPOSITE TOOLS (Exposed to agents) ───
    "locate": LocateResult,
    "explore_symbol_usage": SymbolExplorerResult,
    "map_module": ModuleMapResult,
    "trace_entry_point": LocateResult,  # Uses same structure as locate
    "explain_code_history": BaseToolResult,  # TODO: Define specific schema

    # ─── RESILIENT TOOLS (Exposed to agents) ───
    "read_code": ReadCodeResult,
    "find_related": FindRelatedResult,

    # ─── STANDALONE TOOLS ───
    "git_status": BaseToolResult,
    "list_tools": BaseToolResult,
}


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL CATEGORIES
# ═══════════════════════════════════════════════════════════════════════════════

# Composite tools MUST return attempt_history (Amendment XVII)
COMPOSITE_TOOLS: FrozenSet[str] = frozenset({
    "locate",
    "explore_symbol_usage",
    "map_module",
    "trace_entry_point",
    "explain_code_history",
})

# Resilient tools MUST return attempt_history (Amendment XIX)
RESILIENT_TOOLS: FrozenSet[str] = frozenset({
    "read_code",
    "find_related",
})

# Tools that MUST have attempt_history (union of composite and resilient)
TOOLS_REQUIRING_ATTEMPT_HISTORY: FrozenSet[str] = COMPOSITE_TOOLS | RESILIENT_TOOLS


# ═══════════════════════════════════════════════════════════════════════════════
# REGISTRY HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def get_schema_for_tool(tool_name: str) -> Optional[Type]:
    """Get the TypedDict schema for a tool.

    Args:
        tool_name: Name of the tool

    Returns:
        TypedDict class if registered, None otherwise
    """
    return TOOL_RESULT_SCHEMAS.get(tool_name)


def is_composite_tool(tool_name: str) -> bool:
    """Check if a tool is a composite tool (requires attempt_history).

    Args:
        tool_name: Name of the tool

    Returns:
        True if tool is composite
    """
    return tool_name in COMPOSITE_TOOLS


def is_resilient_tool(tool_name: str) -> bool:
    """Check if a tool is a resilient tool (requires attempt_history).

    Args:
        tool_name: Name of the tool

    Returns:
        True if tool is resilient
    """
    return tool_name in RESILIENT_TOOLS


def requires_attempt_history(tool_name: str) -> bool:
    """Check if a tool must include attempt_history.

    Per Amendment XVII and XIX, composite and resilient tools
    MUST return attempt_history.

    Args:
        tool_name: Name of the tool

    Returns:
        True if attempt_history is required
    """
    return tool_name in TOOLS_REQUIRING_ATTEMPT_HISTORY


def list_registered_tools() -> list:
    """List all tools with registered schemas.

    Returns:
        List of tool names
    """
    return list(TOOL_RESULT_SCHEMAS.keys())
