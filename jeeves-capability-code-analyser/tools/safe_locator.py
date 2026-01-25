"""Safe Locator - Deterministic fallback search composite tool.

Phase 2/4 Constitutional Compliance - No auto-registration at import time

Per Amendment XVII (Composite Tool Contracts), this tool:
- Orchestrates multiple primitive tools in a deterministic sequence
- Returns attempt_history for transparency
- Aggregates citations from all steps
- Respects context bounds
- Degrades gracefully on step failures

Constitutional Pattern:
- Simple async function (no custom executor infrastructure)
- Calls tools via tool_catalog.get_function(ToolId.XXX)
- Tracks attempts manually
- Returns attempt_history for transparency
"""

import re
from typing import Any, Dict, Optional

from protocols import LoggerProtocol
from .catalog import ToolId, tool_catalog
from protocols import RiskLevel, ToolCategory


async def locate(
    query: str,
    search_type: str = "auto",
    scope: Optional[str] = None,
    max_results: int = 20,
) -> Dict[str, Any]:
    """Locate code elements with deterministic fallback strategy.

    Per Amendment XVII, this composite tool:
    1. Executes a deterministic sequence of search strategies
    2. Returns attempt_history for transparency
    3. Collects citations from all steps
    4. Respects context bounds

    Fallback sequence (for search_type='auto'):
    1. find_symbol(exact=True) - Exact symbol match
    2. find_symbol(exact=False) - Partial symbol match
    3. grep_search(case_sensitive=True) - Exact text search
    4. grep_search(case_sensitive=False) - Case-insensitive text search
    5. semantic_search - Semantic fallback

    Args:
        query: What to find (symbol name, text pattern, etc.)
        search_type: Search strategy - 'symbol', 'text', 'semantic', or 'auto'
        scope: Path prefix to limit search scope
        max_results: Maximum results to return

    Returns:
        Dict with:
        - status: 'success', 'partial', or 'not_found'
        - query: Original query
        - found_via: Method that found results
        - results: List of matches with file, line, match info
        - attempt_history: List of all attempts with method and result
        - citations: Deduplicated [file:line] citations
        - scope_used: Scope that was applied
        - bounded: Whether search was limited by bounds
    """
    attempt_history = []
    all_citations = set()

    # Strategy 1: Exact symbol match
    if search_type in ("auto", "symbol"):
        if tool_catalog.has_tool_id(ToolId.FIND_SYMBOL):
            find_symbol = tool_catalog.get_function(ToolId.FIND_SYMBOL)
            result = await find_symbol(name=query, exact=True, path_prefix=scope)
            attempt_history.append({"strategy": "find_symbol (exact)", "status": result.get("status")})

            if result.get("status") == "success" and result.get("symbols"):
                for sym in result["symbols"][:max_results]:
                    all_citations.add(f"{sym.get('file')}:{sym.get('line', 1)}")

                return {
                    "status": "success",
                    "query": query,
                    "found_via": "find_symbol (exact)",
                    "results": result["symbols"][:max_results],
                    "attempt_history": attempt_history,
                    "citations": sorted(list(all_citations)),
                    "scope_used": scope,
                    "bounded": len(result["symbols"]) > max_results,
                }

    # Strategy 2: Partial symbol match
    if search_type in ("auto", "symbol"):
        if tool_catalog.has_tool_id(ToolId.FIND_SYMBOL):
            find_symbol = tool_catalog.get_function(ToolId.FIND_SYMBOL)
            result = await find_symbol(name=query, exact=False, path_prefix=scope)
            attempt_history.append({"strategy": "find_symbol (partial)", "status": result.get("status")})

            if result.get("status") == "success" and result.get("symbols"):
                for sym in result["symbols"][:max_results]:
                    all_citations.add(f"{sym.get('file')}:{sym.get('line', 1)}")

                return {
                    "status": "success",
                    "query": query,
                    "found_via": "find_symbol (partial)",
                    "results": result["symbols"][:max_results],
                    "attempt_history": attempt_history,
                    "citations": sorted(list(all_citations)),
                    "scope_used": scope,
                    "bounded": len(result["symbols"]) > max_results,
                }

    # Strategy 3: Grep case-sensitive
    if search_type in ("auto", "text"):
        if tool_catalog.has_tool_id(ToolId.GREP_SEARCH):
            grep_search = tool_catalog.get_function(ToolId.GREP_SEARCH)
            pattern = re.escape(query)  # Literal search
            result = await grep_search(pattern=pattern, path=scope, max_results=max_results)
            attempt_history.append({"strategy": "grep_search (case-sensitive)", "status": result.get("status")})

            if result.get("status") == "success" and result.get("matches"):
                for match in result["matches"]:
                    all_citations.add(f"{match.get('file')}:{match.get('line', 1)}")

                return {
                    "status": "success",
                    "query": query,
                    "found_via": "grep_search (case-sensitive)",
                    "results": result["matches"],
                    "attempt_history": attempt_history,
                    "citations": sorted(list(all_citations)),
                    "scope_used": scope,
                    "bounded": False,
                }

    # Strategy 4: Grep case-insensitive
    if search_type in ("auto", "text"):
        if tool_catalog.has_tool_id(ToolId.GREP_SEARCH):
            grep_search = tool_catalog.get_function(ToolId.GREP_SEARCH)
            pattern = f"(?i){re.escape(query)}"  # Case-insensitive
            result = await grep_search(pattern=pattern, path=scope, max_results=max_results)
            attempt_history.append({"strategy": "grep_search (case-insensitive)", "status": result.get("status")})

            if result.get("status") == "success" and result.get("matches"):
                for match in result["matches"]:
                    all_citations.add(f"{match.get('file')}:{match.get('line', 1)}")

                return {
                    "status": "success",
                    "query": query,
                    "found_via": "grep_search (case-insensitive)",
                    "results": result["matches"],
                    "attempt_history": attempt_history,
                    "citations": sorted(list(all_citations)),
                    "scope_used": scope,
                    "bounded": False,
                }

    # Strategy 5: Semantic search
    if search_type in ("auto", "semantic"):
        if tool_catalog.has_tool_id(ToolId.SEMANTIC_SEARCH):
            semantic_search = tool_catalog.get_function(ToolId.SEMANTIC_SEARCH)
            result = await semantic_search(query=query, limit=min(max_results, 10), path_prefix=scope)
            attempt_history.append({"strategy": "semantic_search", "status": result.get("status")})

            # semantic_search returns "files", not "results"
            if result.get("status") == "success" and result.get("files"):
                for res in result["files"]:
                    all_citations.add(f"{res.get('file')}:{res.get('line', 1)}")

                return {
                    "status": "success",
                    "query": query,
                    "found_via": "semantic_search",
                    "results": result["files"],  # Normalize to "results" for consumers
                    "attempt_history": attempt_history,
                    "citations": sorted(list(all_citations)),
                    "scope_used": scope,
                    "bounded": False,
                }

    # All strategies failed
    _logger = get_logger()
    _logger.info(
        "locate_not_found",
        query=query,
        search_type=search_type,
        attempts=len(attempt_history),
    )

    return {
        "status": "not_found",
        "query": query,
        "found_via": None,
        "results": [],
        "attempt_history": attempt_history,
        "citations": [],
        "scope_used": scope,
        "bounded": False,
    }


__all__ = ["locate"]
