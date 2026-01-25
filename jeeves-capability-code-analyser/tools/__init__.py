"""Code analysis tools module.

Phase 2 Constitutional Compliance:
- Uses tool_catalog as the SINGLE source of truth (not tool_registry)
- No auto-registration at import time (Phase 4)
- Registration happens via explicit register_all_tools() call

Architecture: File Navigator -> Code Parser -> Semantic Search (L5 Graph)
             -> Unified Analyzer (single entry point)
             -> Composite Tools (internal orchestration)
"""

from typing import Optional, List, Dict, Any

from protocols import LoggerProtocol, ToolCategory, PersistenceProtocol
from mission_system.contracts_core import ContextBounds

# Import from capability's own catalog
from tools.catalog import tool_catalog, ToolId, EXPOSED_TOOL_IDS

from tools.registration import (
    register_all_tools,
    get_tool_function,
    has_tool,
    list_registered_tools,
)
from tools.base.path_helpers import validate_repo_path, get_repo_path

# Import from base module - single source of truth
from tools.base import ToolInitializationError, validate_tool_dependencies


def initialize_all_tools(
    db: Optional[PersistenceProtocol] = None,
    skip_validation: bool = False,
    logger: Optional[LoggerProtocol] = None,
) -> Dict[str, Any]:
    """
    Initialize and register all available tools for code analysis.
    SINGLE CANONICAL PATH per Constitution.

    Phase 2: Uses tool_catalog (single registry).
    Phase 4: Explicit registration (no import-time side effects).

    Args:
        db: Database client instance (optional for tools that don't need it)
        skip_validation: Skip dependency validation (for testing only)
        logger: Optional logger instance. If not provided, uses structlog.

    Returns:
        dict: Tool registration results
    """
    if logger is None:
        import structlog
        _logger = structlog.get_logger("tools")
    else:
        _logger = logger

    # Validate dependencies first
    validation = validate_tool_dependencies(db)

    if not skip_validation and not validation["all_valid"]:
        _logger.warning(
            "tool_initialization_proceeding_with_invalid_deps",
            message="Some tools may return errors when called"
        )

    _logger.info(
        "initializing_tools",
        mode="code_analysis",
        repo_path=validation["repo_path"],
        repo_path_valid=validation["repo_path_valid"],
        db_valid=validation["db_valid"],
    )

    # Register all tools with the capability's tool_catalog
    registration_result = register_all_tools(logger=_logger)

    _logger.info(
        "tools_initialized",
        count=registration_result["count"],
        mode="code_analysis"
    )

    return {
        "registration": registration_result,
        "validation": validation,
        "catalog": tool_catalog,
    }


# Tool names for validation
CODE_ANALYSIS_TOOLS = [
    # Core traversal tools
    "read_file",
    "glob_files",
    "grep_search",
    "tree_structure",
    # Index tools
    "find_symbol",
    "get_file_symbols",
    "get_imports",
    "get_importers",
    # Git tools
    "git_log",
    "git_blame",
    "git_diff",
    "git_status",
    # Session tools
    "get_session_state",
    "save_session_state",
    "list_tools",
    # Semantic search tools
    "semantic_search",
    "find_similar_files",
    "get_index_stats",
]

# ═══════════════════════════════════════════════════════════════════════════
# EXPOSED TOOLS - Visible to agents
# ═══════════════════════════════════════════════════════════════════════════
EXPOSED_TOOLS = [
    "search_code",   # Primary: searches for code, never assumes paths exist
    "read_code",     # Direct file reading with retry
    "find_related",  # Semantic search for related files
    "git_status",    # Current repo state
    "list_tools",    # Tool discovery
]

# ═══════════════════════════════════════════════════════════════════════════
# INTERNAL TOOLS - Used by exposed tools, not directly visible to agents
# ═══════════════════════════════════════════════════════════════════════════
INTERNAL_TOOLS = [
    "locate",
    "explore_symbol_usage",
    "explain_code_history",
    "map_module",
    "trace_entry_point",
]


def get_code_analysis_tools_for_llm() -> str:
    """Get formatted tool list for LLM context using tool_catalog."""
    return tool_catalog.generate_prompt_section()


def get_code_analysis_tool_names() -> List[str]:
    """Get list of code analysis tool names that are registered."""
    return [t for t in CODE_ANALYSIS_TOOLS if has_tool(t)]


__all__ = [
    # Tool Initialization (Constitutional SINGLE PATH)
    "initialize_all_tools",
    "validate_tool_dependencies",
    "ToolInitializationError",
    # Tool catalog access (Phase 2: Single registry)
    "tool_catalog",
    "get_tool_function",
    "has_tool",
    "list_registered_tools",
    "register_all_tools",
    # Constants
    "CODE_ANALYSIS_TOOLS",
    "EXPOSED_TOOLS",
    "INTERNAL_TOOLS",
    # Registration
    "get_code_analysis_tools_for_llm",
    "get_code_analysis_tool_names",
]
