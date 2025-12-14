"""Code Analysis Context Bounds - Domain-specific resource limits.

Per Constitution R6 (Domain Config Ownership):
    Capability OWNS domain-specific configuration.
    Core provides generic ContextBounds (LLM/pipeline limits).
    Capability provides CodeAnalysisBounds (code analysis limits).

These bounds control resource usage during code analysis:
- File limits: How many files to read per query
- Search limits: How many results to return
- Token limits: Code token budgets
- Pipeline limits: Loop and chain limits

Usage:
    from jeeves_capability_code_analyser.config import CodeAnalysisBounds, get_code_analysis_bounds

    # Get singleton (registered at startup)
    bounds = get_code_analysis_bounds()

    # Or create custom bounds
    bounds = CodeAnalysisBounds(max_files_per_query=100)
"""

from dataclasses import dataclass, field
from typing import Optional

# Module-level singleton for registered bounds
_registered_bounds: Optional["CodeAnalysisBounds"] = None


@dataclass
class CodeAnalysisBounds:
    """Context bounds specific to code analysis capability.

    These are domain-specific limits that control code analysis behavior.
    Separate from core ContextBounds which handles LLM/pipeline limits.

    Constitutional Reference:
        - Mission System Constitution: Lines 203-208 define these limits
        - Capability Constitution R6: Domain Config Ownership
    """

    # ─── File Limits ───
    max_files_per_query: int = 50
    """Maximum files to read in a single query."""

    max_file_slice_tokens: int = 4000
    """Maximum tokens per file slice (for read_code truncation)."""

    max_tree_tokens: int = 2000
    """Maximum tokens for tree structure output."""

    # ─── Search Limits ───
    max_grep_results: int = 50
    """Maximum grep/search results to return."""

    max_symbols_in_summary: int = 30
    """Maximum symbols to include in module summary."""

    max_matches_in_summary: int = 100
    """Maximum matches to include in citation list."""

    # ─── Token Limits ───
    max_total_code_tokens: int = 12000
    """Total code token budget per query (for synthesizer context)."""

    # ─── Pipeline Limits ───
    max_loops: int = 3
    """Maximum planner-critic feedback loops."""

    max_call_chain_length: int = 20
    """Maximum depth for call chain tracing."""

    max_commits_in_summary: int = 50
    """Maximum commits to include in git history summary."""

    # ─── Traversal Limits (used by TraversalState) ───
    max_explored_files: int = 100
    """Maximum files to track in explored set."""

    max_explored_symbols: int = 200
    """Maximum symbols to track in explored set."""

    max_pending_files: int = 50
    """Maximum files in pending queue."""

    max_relevant_snippets: int = 50
    """Maximum relevant code snippets to store."""

    def to_dict(self) -> dict:
        """Convert to dictionary for dict-based access patterns.

        Used by TraversalState which uses self._bounds.get() pattern.
        """
        return {
            "max_files_per_query": self.max_files_per_query,
            "max_file_slice_tokens": self.max_file_slice_tokens,
            "max_tree_tokens": self.max_tree_tokens,
            "max_grep_results": self.max_grep_results,
            "max_symbols_in_summary": self.max_symbols_in_summary,
            "max_matches_in_summary": self.max_matches_in_summary,
            "max_total_code_tokens": self.max_total_code_tokens,
            "max_loops": self.max_loops,
            "max_call_chain_length": self.max_call_chain_length,
            "max_commits_in_summary": self.max_commits_in_summary,
            "max_explored_files": self.max_explored_files,
            "max_explored_symbols": self.max_explored_symbols,
            "max_pending_files": self.max_pending_files,
            "max_relevant_snippets": self.max_relevant_snippets,
        }


# Default bounds instance
DEFAULT_CODE_ANALYSIS_BOUNDS = CodeAnalysisBounds()


def get_code_analysis_bounds() -> CodeAnalysisBounds:
    """Get the registered CodeAnalysisBounds instance.

    Returns the bounds registered via set_code_analysis_bounds(),
    or DEFAULT_CODE_ANALYSIS_BOUNDS if none registered.

    Usage:
        bounds = get_code_analysis_bounds()
        max_files = bounds.max_files_per_query
    """
    global _registered_bounds
    return _registered_bounds or DEFAULT_CODE_ANALYSIS_BOUNDS


def set_code_analysis_bounds(bounds: CodeAnalysisBounds) -> None:
    """Register CodeAnalysisBounds instance.

    Called at capability bootstrap to set custom bounds.

    Args:
        bounds: CodeAnalysisBounds instance to register
    """
    global _registered_bounds
    _registered_bounds = bounds


def reset_code_analysis_bounds() -> None:
    """Reset to default bounds (for testing)."""
    global _registered_bounds
    _registered_bounds = None
