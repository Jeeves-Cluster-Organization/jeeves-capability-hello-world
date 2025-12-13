"""Resilient Code Operations - Robust abstraction layer for Planner/Traverser.

Phase 2/4 Constitutional Compliance - No auto-registration at import time

Per Amendment XXI, these are part of the 10 tools exposed to agents:
- read_code: Read file with multi-path fallbacks
- find_related: Find related files without requiring reference to exist

Design Principles (Constitution):
- P1: Every result includes [file:line] citations
- P3: Bounded efficiency - max 2 retries per step, deterministic order
- Amendment XVII: Return attempt_history for transparency
- Amendment XIX: Bounded retry with fallback strategies

REMOVED (consolidation):
- find_code: Removed - was just a wrapper around `locate`. Use `locate` directly.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from jeeves_mission_system.adapters import get_logger
from jeeves_mission_system.contracts import LoggerProtocol, ToolId, tool_catalog
from jeeves_protocols import RiskLevel, ToolCategory
from tools.path_helpers import get_repo_path, resolve_path
from tools.robust_tool_base import (
    RobustToolExecutor,
    ToolResult,
    CitationCollector,
    AttemptRecord,
    StrategyResult,
    RetryPolicy,
)


# Extension swap mappings for fuzzy path matching
EXTENSION_SWAPS = {
    ".py": [".pyi", ".pyc"],
    ".pyi": [".py"],
    ".ts": [".tsx", ".js", ".jsx", ".d.ts"],
    ".tsx": [".ts", ".js", ".jsx"],
    ".js": [".jsx", ".ts", ".tsx", ".mjs", ".cjs"],
    ".jsx": [".js", ".ts", ".tsx"],
    ".mjs": [".js", ".cjs"],
    ".cjs": [".js", ".mjs"],
}


# ============================================================
# Strategy Functions for read_code
# ============================================================

async def _strategy_exact_path(
    path: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Strategy 1: Try exact path."""
    if not tool_registry.has_tool("read_file"):
        return {"status": "tool_unavailable"}

    read_file = tool_registry.get_tool_function("read_file")
    result = await read_file(path=path, start_line=start_line, end_line=end_line)

    if result.get("status") == "success":
        return {
            "status": "success",
            "results": [{
                "path": path,
                "file": path,
                "content": result.get("content", ""),
                "line": start_line or 1,
            }],
            "resolved_path": path,
        }

    return {"status": "no_match"}


async def _strategy_extension_swap(
    path: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Strategy 2: Try alternative extensions (.py <-> .pyi, .ts <-> .tsx, etc.)."""
    if not tool_registry.has_tool("read_file"):
        return {"status": "tool_unavailable"}

    read_file = tool_registry.get_tool_function("read_file")
    base, ext = os.path.splitext(path)

    if ext not in EXTENSION_SWAPS:
        return {"status": "no_match"}

    for alt_ext in EXTENSION_SWAPS[ext]:
        alt_path = base + alt_ext
        result = await read_file(path=alt_path, start_line=start_line, end_line=end_line)

        if result.get("status") == "success":
            _logger = get_logger()
            _logger.info(
                "read_code_extension_swap_success",
                original=path,
                resolved=alt_path,
            )
            return {
                "status": "success",
                "results": [{
                    "path": alt_path,
                    "file": alt_path,
                    "content": result.get("content", ""),
                    "line": start_line or 1,
                }],
                "resolved_path": alt_path,
            }

    return {"status": "no_match"}


async def _strategy_glob_filename(
    path: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Strategy 3: Glob search for exact filename anywhere in repo."""
    if not tool_registry.has_tool("glob_files") or not tool_registry.has_tool("read_file"):
        return {"status": "tool_unavailable"}

    glob_files = tool_registry.get_tool_function("glob_files")
    read_file = tool_registry.get_tool_function("read_file")

    filename = os.path.basename(path)
    glob_pattern = f"**/{filename}"
    glob_result = await glob_files(pattern=glob_pattern)
    matches = glob_result.get("files", [])

    if not matches:
        return {"status": "no_match", "matches_found": 0}

    # Try the first match
    found_path = matches[0]
    result = await read_file(path=found_path, start_line=start_line, end_line=end_line)

    if result.get("status") == "success":
        _logger = get_logger()
        _logger.info(
            "read_code_glob_success",
            original=path,
            resolved=found_path,
            total_matches=len(matches),
        )
        return {
            "status": "success",
            "results": [{
                "path": found_path,
                "file": found_path,
                "content": result.get("content", ""),
                "line": start_line or 1,
            }],
            "resolved_path": found_path,
            "other_matches": matches[1:5] if len(matches) > 1 else [],
        }

    return {"status": "no_match", "matches_found": len(matches)}


async def _strategy_glob_stem(
    path: str,
    **kwargs,
) -> Dict[str, Any]:
    """Strategy 4: Glob for stem pattern (provides suggestions only)."""
    if not tool_registry.has_tool("glob_files"):
        return {"status": "tool_unavailable"}

    glob_files = tool_registry.get_tool_function("glob_files")

    filename = os.path.basename(path)
    stem = os.path.splitext(filename)[0]
    stem_pattern = f"**/*{stem}*"
    glob_result = await glob_files(pattern=stem_pattern)
    suggestions = glob_result.get("files", [])[:10]

    if suggestions:
        return {
            "status": "no_match",  # Still no match, but we have suggestions
            "suggestions": suggestions,
        }

    return {"status": "no_match"}


# ============================================================
# read_code Tool Implementation
# ============================================================

async def read_code(
    path: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
) -> Dict[str, Any]:
    """Read file with fallback strategies.

    Per Amendment XVII and XIX, this resilient tool:
    1. Tries exact path
    2. Tries extension swap (.py <-> .pyi, .ts <-> .tsx, etc.)
    3. Globs for exact filename anywhere in repo
    4. Globs for stem pattern (suggestions only)

    Returns attempt_history for transparency and suggestions on failure.

    Args:
        path: Path to file (relative to repo root)
        start_line: Optional starting line (1-indexed)
        end_line: Optional ending line (inclusive)

    Returns:
        Dict with:
        - status: "success" | "not_found"
        - content: File content (if found)
        - resolved_path: Actual path that was read (if found)
        - attempt_history: List of all strategies tried
        - suggestions: Similar files (if not found)
        - citations: [file:line] references
        - message: Human-readable summary
    """
    executor = RobustToolExecutor(
        name="read_code",
        retry_policy=RetryPolicy(max_retries=2),
        max_results=1,
    )

    # Build the fallback chain
    executor.add_strategy("exact_path", _strategy_exact_path)
    executor.add_strategy("extension_swap", _strategy_extension_swap)
    executor.add_strategy("glob_filename", _strategy_glob_filename)
    executor.add_strategy("glob_stem", _strategy_glob_stem)

    # Execute with fallbacks
    result = await executor.execute(
        path=path,
        start_line=start_line,
        end_line=end_line,
    )

    # Transform to read_code specific output format
    output = result.to_dict()

    # Add resolved_path and content for backward compatibility
    if result.status == "success" and result.results:
        output["content"] = result.results[0].get("content", "")
        output["resolved_path"] = result.results[0].get("path", path)
    else:
        output["error"] = f"File not found: {path}"

    # Log loud failure with context
    if result.status != "success":
        _logger = get_logger()
        _logger.warning(
            "read_code_not_found",
            path=path,
            attempts=len(result.attempt_history),
            suggestions=result.suggestions[:3] if result.suggestions else [],
        )

    return output


# ============================================================
# Strategy Functions for find_related
# ============================================================

async def _strategy_content_similarity(
    reference: str,
    limit: int = 5,
    **kwargs,
) -> Dict[str, Any]:
    """Strategy 1: If file exists, use content-based similarity."""
    repo_path = get_repo_path()
    resolved = resolve_path(reference, repo_path)

    if not resolved or not resolved.exists():
        return {"status": "no_match", "reason": "file_not_found"}

    if not tool_registry.has_tool("find_similar_files"):
        return {"status": "tool_unavailable"}

    find_similar = tool_registry.get_tool_function("find_similar_files")
    result = await find_similar(file_path=reference, limit=limit)

    if result.get("status") == "success" and result.get("similar_files"):
        return {
            "status": "success",
            "results": [
                {"file": f.get("file", f.get("path", "")), "relevance": "content_similarity"}
                for f in result["similar_files"]
            ],
        }

    return {"status": "no_match"}


async def _strategy_filename_pattern(
    reference: str,
    limit: int = 5,
    **kwargs,
) -> Dict[str, Any]:
    """Strategy 2: Search by filename pattern."""
    # Check if reference looks like a path
    is_path = "/" in reference or reference.endswith((".py", ".ts", ".js", ".tsx", ".jsx"))
    if not is_path:
        return {"status": "no_match", "reason": "not_a_path"}

    if not tool_registry.has_tool("glob_files"):
        return {"status": "tool_unavailable"}

    glob_files = tool_registry.get_tool_function("glob_files")

    filename = os.path.basename(reference)
    stem = os.path.splitext(filename)[0]
    pattern = f"**/*{stem}*"

    glob_result = await glob_files(pattern=pattern)
    matches = glob_result.get("files", [])

    if matches:
        # Filter out the reference itself if present
        related = [f for f in matches if f != reference][:limit]
        if related:
            return {
                "status": "success",
                "results": [
                    {"file": f, "relevance": "filename_match"}
                    for f in related
                ],
            }

    return {"status": "no_match"}


async def _strategy_semantic_search(
    reference: str,
    limit: int = 5,
    **kwargs,
) -> Dict[str, Any]:
    """Strategy 3: Semantic search using reference as query."""
    if not tool_registry.has_tool("semantic_search"):
        return {"status": "tool_unavailable"}

    semantic_search = tool_registry.get_tool_function("semantic_search")

    # Use the reference (or filename) as the query
    is_path = "/" in reference or reference.endswith((".py", ".ts", ".js", ".tsx", ".jsx"))
    query = os.path.basename(reference) if is_path else reference

    result = await semantic_search(query=query, limit=limit)

    if result.get("status") == "success" and result.get("results"):
        return {
            "status": "success",
            "results": [
                {
                    "file": r.get("file", r.get("path", "")),
                    "relevance": f"semantic (score: {r.get('score', 0):.2f})",
                }
                for r in result["results"]
            ],
        }

    return {"status": "no_match"}


# ============================================================
# find_related Tool Implementation
# ============================================================

async def find_related(
    reference: str,
    limit: int = 5,
) -> Dict[str, Any]:
    """Find files related to a reference (file path or description).

    Per Amendment XVII and XIX, this resilient tool:
    1. If file exists: Uses content-based similarity
    2. Searches by filename pattern
    3. Falls back to semantic search using filename as query

    Unlike find_similar_files, this does NOT require the file to exist.

    Args:
        reference: File path or description to find related files for
        limit: Maximum number of related files to return

    Returns:
        Dict with:
        - status: "success" | "not_found" | "partial"
        - reference: The input reference
        - related_files: List of related files with paths and relevance
        - attempt_history: Strategies tried
        - citations: [file:line] references
        - message: Human-readable summary
    """
    executor = RobustToolExecutor(
        name="find_related",
        retry_policy=RetryPolicy(max_retries=2),
        max_results=limit,
    )

    # Build the fallback chain
    executor.add_strategy("content_similarity", _strategy_content_similarity)
    executor.add_strategy("filename_pattern", _strategy_filename_pattern)
    executor.add_strategy("semantic_search", _strategy_semantic_search)

    # Execute with fallbacks
    result = await executor.execute(
        reference=reference,
        limit=limit,
    )

    # Transform to find_related specific output format
    output = result.to_dict()
    output["reference"] = reference
    output["related_files"] = result.results

    # Log failure with context
    if result.status not in ("success",):
        _logger = get_logger()
        _logger.warning(
            "find_related_no_results",
            reference=reference,
            attempts=len(result.attempt_history),
        )

    return output


# ============================================================
# Deprecated: find_code
# ============================================================
# REMOVED: find_code was just a pass-through wrapper around `locate`.
# Per consolidation, use `locate` directly instead.
# This reduces redundant indirection and aligns with Amendment XXI
# which specifies 5 composite tools (including locate) + 3 resilient tools.


# ============================================================
# Tool Catalog Registration (Decision 1:A compliance)
# ============================================================
def _register_resilient_tools_in_catalog():
    """Register resilient tools with the canonical ToolCatalog.

    Per Decision 1:A: ToolCatalog is the single source of truth.
    Tools must be registered here for Planner to see them in prompts.
    """
    # Register read_code
    if not tool_catalog.has_tool(ToolId.READ_CODE):
        tool_catalog.register_function(
            tool_id=ToolId.READ_CODE,
            func=read_code,
            description=(
                "Read file with robust multi-path fallbacks. "
                "Tries: exact path -> extension swap -> glob filename -> glob stem suggestions."
            ),
            parameters={
                "path": "string (required)",
                "start_line": "integer? (optional)",
                "end_line": "integer? (optional)",
            },
            category=ToolCategory.RESILIENT,
        )

    # Register find_related
    if not tool_catalog.has_tool(ToolId.FIND_RELATED):
        tool_catalog.register_function(
            tool_id=ToolId.FIND_RELATED,
            func=find_related,
            description=(
                "Find related files using semantic similarity and pattern matching. "
                "Works even if reference file doesn't exist."
            ),
            parameters={
                "reference": "string (required)",
                "limit": "integer? (optional, default 10)",
            },
            category=ToolCategory.RESILIENT,
        )


# Auto-register on import
_register_resilient_tools_in_catalog()


# Export the main functions
__all__ = ["read_code", "find_related"]
