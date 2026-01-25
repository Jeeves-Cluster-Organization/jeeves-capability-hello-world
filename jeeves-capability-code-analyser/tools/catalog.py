"""
Code Analysis Tool Catalog - Capability-owned tool definitions.

This module provides:
- ToolId: Typed enum for all code analysis tool identifiers
- tool_catalog: CapabilityToolCatalog instance for this capability
- EXPOSED_TOOL_IDS: Tools visible to agents

Constitutional Compliance:
- Avionics R3: No Domain Logic in core - tools owned by capability
- Avionics R4: Swappable Implementations - uses CapabilityToolCatalog from protocols
- Capability Constitution R7: Capability owns its resources

This replaces imports from avionics.tools.catalog which was a layer violation.
"""

from enum import Enum
from typing import FrozenSet, Optional

from protocols import RiskLevel, ToolCategory
from protocols.capability import CapabilityToolCatalog


class ToolId(str, Enum):
    """Typed tool identifiers for code analysis capability.

    All tool references must use these enum values, not raw strings.
    This ensures compile-time checking and prevents name mismatches.
    """

    # ═══════════════════════════════════════════════════════════════════════════
    # PRIMARY SEARCH TOOL - Two-path architecture (Amendment XXII v2)
    # ═══════════════════════════════════════════════════════════════════════════
    SEARCH_CODE = "search_code"

    # ═══════════════════════════════════════════════════════════════════════════
    # COMPOSITE TOOLS (Amendment XVII) - Multi-step workflows with fallbacks
    # ═══════════════════════════════════════════════════════════════════════════
    LOCATE = "locate"
    EXPLORE_SYMBOL_USAGE = "explore_symbol_usage"
    MAP_MODULE = "map_module"
    TRACE_ENTRY_POINT = "trace_entry_point"
    EXPLAIN_CODE_HISTORY = "explain_code_history"

    # ═══════════════════════════════════════════════════════════════════════════
    # RESILIENT TOOLS (Amendment XXI) - Wrapped base tools with retry/fallback
    # ═══════════════════════════════════════════════════════════════════════════
    READ_CODE = "read_code"
    FIND_RELATED = "find_related"

    # ═══════════════════════════════════════════════════════════════════════════
    # STANDALONE TOOLS - Simple tools that don't need wrapping
    # ═══════════════════════════════════════════════════════════════════════════
    GIT_STATUS = "git_status"
    LIST_TOOLS = "list_tools"

    # ═══════════════════════════════════════════════════════════════════════════
    # INTERNAL/BASE TOOLS - Implementation details, not exposed to agents
    # ═══════════════════════════════════════════════════════════════════════════
    # Core traversal
    READ_FILE = "read_file"
    GLOB_FILES = "glob_files"
    GREP_SEARCH = "grep_search"
    TREE_STRUCTURE = "tree_structure"

    # Code parser
    FIND_SYMBOL = "find_symbol"
    GET_FILE_SYMBOLS = "get_file_symbols"
    GET_IMPORTS = "get_imports"
    GET_IMPORTERS = "get_importers"
    PARSE_SYMBOLS = "parse_symbols"
    FIND_REFERENCES = "find_references"
    GET_DEPENDENCIES = "get_dependencies"
    GET_DEPENDENTS = "get_dependents"

    # File navigation
    LIST_FILES = "list_files"
    SEARCH_FILES = "search_files"
    GET_PROJECT_TREE = "get_project_tree"

    # Semantic/RAG
    SEMANTIC_SEARCH = "semantic_search"
    FIND_SIMILAR_FILES = "find_similar_files"
    GET_INDEX_STATS = "get_index_stats"

    # Git
    GIT_LOG = "git_log"
    GIT_BLAME = "git_blame"
    GIT_DIFF = "git_diff"

    # Session
    GET_SESSION_STATE = "get_session_state"
    SAVE_SESSION_STATE = "save_session_state"


# ═══════════════════════════════════════════════════════════════════════════════
# EXPOSED TOOL IDS - Tools visible to agents
# ═══════════════════════════════════════════════════════════════════════════════
EXPOSED_TOOL_IDS: FrozenSet[ToolId] = frozenset({
    # Two-tool architecture: search_code + read_code (Amendment XXII v2)
    ToolId.SEARCH_CODE,
    # Composite tools
    ToolId.LOCATE,
    ToolId.EXPLORE_SYMBOL_USAGE,
    ToolId.MAP_MODULE,
    ToolId.TRACE_ENTRY_POINT,
    ToolId.EXPLAIN_CODE_HISTORY,
    # Resilient tools
    ToolId.READ_CODE,
    ToolId.FIND_RELATED,
    # Standalone tools
    ToolId.GIT_STATUS,
    ToolId.LIST_TOOLS,
})


# ═══════════════════════════════════════════════════════════════════════════════
# CAPABILITY TOOL CATALOG - Singleton instance
# ═══════════════════════════════════════════════════════════════════════════════

# Create capability-scoped catalog
tool_catalog = CapabilityToolCatalog("code_analysis")


def resolve_tool_id(name: str) -> Optional[ToolId]:
    """Resolve string tool name to ToolId.

    Args:
        name: Tool name string (e.g., "locate")

    Returns:
        ToolId if valid, None otherwise
    """
    try:
        return ToolId(name)
    except ValueError:
        return None


def is_exposed_tool(tool_id: ToolId) -> bool:
    """Check if tool is in exposed set.

    Args:
        tool_id: Tool identifier

    Returns:
        True if tool is visible to agents
    """
    return tool_id in EXPOSED_TOOL_IDS


__all__ = [
    "ToolId",
    "EXPOSED_TOOL_IDS",
    "tool_catalog",
    "resolve_tool_id",
    "is_exposed_tool",
]

