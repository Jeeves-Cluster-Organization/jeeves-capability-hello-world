"""Code Analysis Tools - Two-path architecture for robust code exploration.

Phase 2/4 Constitutional Compliance - No auto-registration at import time

TWO-TOOL ARCHITECTURE:
1. search_code(query) - Always searches. Never assumes paths exist.
   Use for: symbols, keywords, natural language queries, directory exploration
   Returns: matches with file:line citations

2. read_code(path) - Reads a confirmed file path.
   Use ONLY after search_code returns a valid path.
   Returns: file content with symbols

This replaces the single `analyze` tool which was prone to LLM hallucination
of file paths. With two explicit paths:
- Planner MUST search first, THEN read
- No guessing of file paths
- Search results provide the paths for read_code
"""

import re
from enum import Enum
from typing import Any, Dict, List, Optional

from jeeves_mission_system.adapters import get_logger
from jeeves_mission_system.contracts import ToolId, tool_catalog,  ContextBounds, ToolId, tool_catalog
from jeeves_protocols import RiskLevel, OperationStatus, ToolCategory


class TargetType(Enum):
    """Detected type of analysis target."""
    SYMBOL = "symbol"      # Function, class, variable name
    MODULE = "module"      # Directory path (e.g., agents/, tools/)
    FILE = "file"          # File path (e.g., agents/planner.py)
    QUERY = "query"        # Natural language query


def _detect_target_type(target: str) -> TargetType:
    """Detect the type of target based on patterns.

    Args:
        target: The analysis target string

    Returns:
        Detected TargetType
    """
    target = target.strip()

    # File path patterns
    if target.endswith(('.py', '.js', '.ts', '.go', '.rs', '.java', '.cpp', '.c', '.h')):
        return TargetType.FILE

    # Directory/module patterns (ends with / or contains only path-like chars)
    if target.endswith('/') or re.match(r'^[a-zA-Z0-9_/.-]+/$', target):
        return TargetType.MODULE

    # Path without extension but looks like directory
    if '/' in target and not ' ' in target and not target.endswith(('.py', '.js', '.ts')):
        # Could be module path like "agents/traverser"
        return TargetType.MODULE

    # Symbol patterns: CamelCase, snake_case, or simple identifier
    if re.match(r'^[A-Z][a-zA-Z0-9]*$', target):  # CamelCase class
        return TargetType.SYMBOL
    if re.match(r'^[a-z_][a-z0-9_]*$', target):   # snake_case function/var
        return TargetType.SYMBOL
    if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', target):  # General identifier
        return TargetType.SYMBOL

    # Default to query for natural language
    return TargetType.QUERY


async def _analyze_symbol(symbol: str, include_usages: bool = True) -> Dict[str, Any]:
    """Analyze a symbol: find definition, usages, and containing module."""
    _logger = get_logger()
    all_citations = set()
    attempt_history = []

    result = {
        "target": symbol,
        "target_type": "symbol",
        "definition": None,
        "usages": [],
        "module_context": None,
        "status": "success",
    }

    # Step 1: Find symbol definition and usages via explore_symbol_usage
    if tool_catalog.has_tool_id(ToolId.EXPLORE_SYMBOL_USAGE):
        explore = tool_catalog.get_function(ToolId.EXPLORE_SYMBOL_USAGE)
        try:
            # Create context bounds for exploration
            context_bounds = ContextBounds(max_files=50, max_tokens=8000)
            explore_result = await explore(
                symbol_name=symbol,
                context_bounds=context_bounds,
                include_tests=include_usages,  # Use include_tests (actual param), not include_call_sites
            )
            attempt_history.append({
                "tool": "explore_symbol_usage",
                "status": "success" if explore_result.get("status") == "success" else "partial",
                "result_summary": f"Found {len(explore_result.get('usages', []))} usages"
            })

            if explore_result.get("status") == "success":
                result["definition"] = explore_result.get("definition")
                result["usages"] = explore_result.get("usages", [])

                # Collect citations
                if explore_result.get("definition"):
                    defn = explore_result["definition"]
                    all_citations.add(f"{defn.get('file', '')}:{defn.get('line', 0)}")
                for usage in explore_result.get("usages", [])[:5]:
                    all_citations.add(f"{usage.get('file', '')}:{usage.get('line', 0)}")

        except Exception as e:
            _logger.warning("analyze_explore_symbol_error", symbol=symbol, error=str(e))
            attempt_history.append({"tool": "explore_symbol_usage", "status": "error", "error": str(e)})

    # Step 2: Get module context if we found a definition
    if result["definition"] and tool_catalog.has_tool_id(ToolId.MAP_MODULE):
        defn_file = result["definition"].get("file", "")
        if defn_file:
            # Extract module path (directory containing the file)
            module_path = "/".join(defn_file.split("/")[:-1])
            if module_path:
                map_module = tool_catalog.get_function(ToolId.MAP_MODULE)
                try:
                    module_result = await map_module(module_path=module_path, depth=1)
                    attempt_history.append({
                        "tool": "map_module",
                        "status": "success" if module_result.get("status") == "success" else "partial",
                        "result_summary": f"Mapped {module_path}"
                    })

                    if module_result.get("status") == "success":
                        result["module_context"] = {
                            "path": module_path,
                            "structure": module_result.get("structure"),
                            "exports": module_result.get("exports", [])[:10],
                        }
                except Exception as e:
                    _logger.warning("analyze_map_module_error", module=module_path, error=str(e))
                    attempt_history.append({"tool": "map_module", "status": "error", "error": str(e)})

    result["attempt_history"] = attempt_history
    result["citations"] = sorted(list(all_citations))
    return result


async def _analyze_module(module_path: str) -> Dict[str, Any]:
    """Analyze a module: structure, exports, dependencies."""
    _logger = get_logger()
    all_citations = set()
    attempt_history = []

    # Normalize path
    module_path = module_path.rstrip('/')

    result = {
        "target": module_path,
        "target_type": "module",
        "structure": None,
        "exports": [],
        "dependencies": [],
        "key_files": [],
        "status": "success",
    }

    # Use map_module for comprehensive module analysis
    if tool_catalog.has_tool_id(ToolId.MAP_MODULE):
        map_module = tool_catalog.get_function(ToolId.MAP_MODULE)
        try:
            module_result = await map_module(module_path=module_path, depth=2)
            attempt_history.append({
                "tool": "map_module",
                "status": "success" if module_result.get("status") == "success" else "partial",
                "result_summary": f"Mapped {module_path}"
            })

            if module_result.get("status") == "success":
                result["structure"] = module_result.get("structure")
                result["exports"] = module_result.get("exports", [])
                result["dependencies"] = module_result.get("dependencies", [])
                result["key_files"] = module_result.get("key_files", [])

                # Add citations for key files
                for f in result["key_files"][:5]:
                    all_citations.add(f"{f}:1")

        except Exception as e:
            _logger.warning("analyze_module_error", module=module_path, error=str(e))
            attempt_history.append({"tool": "map_module", "status": "error", "error": str(e)})
            result["status"] = "partial"

    result["attempt_history"] = attempt_history
    result["citations"] = sorted(list(all_citations))
    return result


async def _analyze_file(file_path: str) -> Dict[str, Any]:
    """Analyze a file: read content, extract symbols.

    Falls back to searching if file doesn't exist (handles LLM hallucinated paths).
    """
    _logger = get_logger()
    all_citations = set()
    attempt_history = []

    result = {
        "target": file_path,
        "target_type": "file",
        "content": None,
        "symbols": [],
        "imports": [],
        "status": "success",
    }

    file_found = False

    # Read the file content
    if tool_catalog.has_tool_id(ToolId.READ_CODE):
        read_code = tool_catalog.get_function(ToolId.READ_CODE)
        try:
            read_result = await read_code(path=file_path)
            attempt_history.append({
                "tool": "read_code",
                "status": "success" if read_result.get("status") == "success" else "not_found",
                "result_summary": f"Read {file_path}"
            })

            if read_result.get("status") == "success":
                result["content"] = read_result.get("content")
                result["symbols"] = read_result.get("symbols", [])
                all_citations.add(f"{file_path}:1")
                file_found = True

        except Exception as e:
            _logger.warning("analyze_file_error", file=file_path, error=str(e))
            attempt_history.append({"tool": "read_code", "status": "error", "error": str(e)})

    # FALLBACK: If file not found, extract filename and search for it
    if not file_found:
        import os
        filename = os.path.basename(file_path)
        stem = os.path.splitext(filename)[0]  # e.g., "Jeeves" from "Jeeves.py"

        _logger.info("analyze_file_fallback_to_search", original_path=file_path, search_term=stem)

        # Try to find files matching the stem
        if tool_catalog.has_tool_id(ToolId.LOCATE):
            locate = tool_catalog.get_function(ToolId.LOCATE)
            try:
                locate_result = await locate(query=stem)
                attempt_history.append({
                    "tool": "locate",
                    "status": "success" if locate_result.get("status") == "success" else "partial",
                    "result_summary": f"Searched for '{stem}'"
                })

                if locate_result.get("status") == "success" and locate_result.get("matches"):
                    result["matches"] = locate_result.get("matches", [])
                    result["fallback_search"] = stem
                    for match in result["matches"][:5]:
                        all_citations.add(f"{match.get('file', '')}:{match.get('line', 0)}")

            except Exception as e:
                _logger.warning("analyze_file_fallback_error", search_term=stem, error=str(e))
                attempt_history.append({"tool": "locate", "status": "error", "error": str(e)})

        # If still nothing found, mark as not_found
        if not result.get("matches"):
            result["status"] = "not_found"
            result["error"] = f"File '{file_path}' not found. Searched for '{stem}' but found no matches."

    result["attempt_history"] = attempt_history
    result["citations"] = sorted(list(all_citations))
    return result


async def _analyze_query(query: str) -> Dict[str, Any]:
    """Analyze a natural language query: locate relevant code."""
    _logger = get_logger()
    all_citations = set()
    attempt_history = []

    result = {
        "target": query,
        "target_type": "query",
        "matches": [],
        "related_files": [],
        "status": "success",
    }

    # Use locate for finding relevant code
    if tool_catalog.has_tool_id(ToolId.LOCATE):
        locate = tool_catalog.get_function(ToolId.LOCATE)
        try:
            locate_result = await locate(query=query)
            attempt_history.append({
                "tool": "locate",
                "status": "success" if locate_result.get("status") == "success" else "partial",
                "result_summary": f"Found {len(locate_result.get('matches', []))} matches"
            })

            if locate_result.get("status") == "success":
                result["matches"] = locate_result.get("matches", [])

                for match in result["matches"][:5]:
                    all_citations.add(f"{match.get('file', '')}:{match.get('line', 0)}")

        except Exception as e:
            _logger.warning("analyze_query_error", query=query, error=str(e))
            attempt_history.append({"tool": "locate", "status": "error", "error": str(e)})

    # Also find related files
    if tool_catalog.has_tool_id(ToolId.FIND_RELATED):
        find_related = tool_catalog.get_function(ToolId.FIND_RELATED)
        try:
            related_result = await find_related(reference=query, limit=5)
            attempt_history.append({
                "tool": "find_related",
                "status": "success" if related_result.get("status") == "success" else "partial",
                "result_summary": f"Found {len(related_result.get('files', []))} related files"
            })

            if related_result.get("status") == "success":
                result["related_files"] = related_result.get("files", [])

        except Exception as e:
            _logger.warning("analyze_query_find_related_error", query=query, error=str(e))
            attempt_history.append({"tool": "find_related", "status": "error", "error": str(e)})

    result["attempt_history"] = attempt_history
    result["citations"] = sorted(list(all_citations))
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# PRIMARY EXPOSED TOOLS - Two-path architecture
# ═══════════════════════════════════════════════════════════════════════════════

async def search_code(
    query: str,
    *,
    search_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search for code - ALWAYS searches, never assumes paths exist.

    This is the PRIMARY tool for finding code. Use it for:
    - Symbol names: "Jeeves", "CodeAnalysisService", "build_planner_context"
    - Keywords: "authentication", "database connection"
    - Natural language: "how does routing work", "where are errors handled"
    - Directory exploration: "agents/", "tools/"

    The tool will search the codebase and return matches with file:line citations.
    NEVER invent file paths - this tool finds them for you.

    Args:
        query: What to search for (symbol, keyword, or natural language)
        search_type: Optional hint - "symbol", "module", or "query" (auto-detected if not provided)

    Returns:
        Dict with:
        - query: The search query
        - matches: List of matches with file, line, context
        - related_files: Semantically related files
        - citations: file:line references
        - status: "success", "partial", or "error"
    """
    _logger = get_logger()

    # Auto-detect search type if not provided
    if search_type:
        try:
            detected_type = TargetType(search_type)
        except ValueError:
            detected_type = _detect_target_type(query)
    else:
        detected_type = _detect_target_type(query)

    _logger.info(
        "search_code_start",
        query=query,
        detected_type=detected_type.value,
    )

    # Route based on detected type - but ALWAYS search, never read directly
    if detected_type == TargetType.SYMBOL:
        result = await _analyze_symbol(query, include_usages=True)
    elif detected_type == TargetType.MODULE:
        result = await _analyze_module(query)
    elif detected_type == TargetType.FILE:
        # For file-like queries, extract the key term and search
        # DO NOT try to read - search instead
        import os
        stem = os.path.splitext(os.path.basename(query))[0]
        _logger.info("search_code_file_to_search", original=query, search_term=stem)
        result = await _analyze_query(stem)
        result["original_query"] = query
        result["search_term"] = stem
    else:  # QUERY
        result = await _analyze_query(query)

    _logger.info(
        "search_code_complete",
        query=query,
        status=result.get("status"),
        matches_count=len(result.get("matches", [])),
        citations_count=len(result.get("citations", [])),
    )

    return result


__all__ = ["search_code"]
