"""Symbol Explorer - Trace symbol usages across codebase.

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
from typing import Any, Dict, List

from jeeves_mission_system.adapters import get_logger
from jeeves_mission_system.contracts import LoggerProtocol, ToolId, tool_catalog
from jeeves_protocols import RiskLevel, OperationStatus
from config.tool_profiles import detect_semantic_mismatch
# Domain-specific bounds from capability config (per Constitution R6)
from jeeves_capability_code_analyser.config import CodeAnalysisBounds


async def explore_symbol_usage(
    symbol_name: str,
    context_bounds: CodeAnalysisBounds,
    trace_depth: int = 3,
    include_tests: bool = False,
) -> Dict[str, Any]:
    """Trace all usages of a symbol across the codebase.

    Pipeline:
    1. Validate symbol_name is semantically valid (not a file path)
    2. find_symbol(exact=True) -> definitions
    3. If no exact match: find_symbol(exact=False)
    4. grep_search for call sites across codebase
    5. Build usage list

    Args:
        symbol_name: Symbol name to explore (class/function name)
        context_bounds: Code analysis bounds (from capability config)
        trace_depth: Depth of trace (default 3)
        include_tests: Include test files in search

    Returns:
        Dict with:
        - status: 'success', 'invalid_parameters', or 'not_found'
        - symbol: Symbol name
        - definitions: List of definition locations
        - usages: List of usage locations
        - attempt_history: List of all attempts
        - citations: Deduplicated [file:line] citations
    """
    _logger = get_logger()
    attempt_history = []
    all_citations = set()

    # SEMANTIC VALIDATION: Detect if symbol_name is actually a file path
    is_mismatch, reason, suggested_tool = detect_semantic_mismatch(
        tool_name="explore_symbol_usage",
        param_name="symbol_name",
        param_value=symbol_name,
    )
    if is_mismatch:
        _logger.warning(
            "explore_symbol_usage_invalid_params",
            symbol_name=symbol_name,
            reason=reason,
            suggested_tool=suggested_tool,
        )
        return {
            "status": OperationStatus.INVALID_PARAMETERS.value,
            "error": reason,
            "message": f"'{symbol_name}' is not a valid symbol name. "
                       "Symbols are class/function names like 'CoreEnvelope' or 'process_request'.",
            "suggested_tool": suggested_tool,
            "suggested_params": {"path": symbol_name} if suggested_tool == "read_code" else {"module_path": symbol_name},
            "symbol": symbol_name,
            "definitions": [],
            "usages": [],
            "attempt_history": [],
            "citations": [],
        }

    # Step 1: Find definitions (exact match)
    definitions = []
    if tool_catalog.has_tool_id(ToolId.FIND_SYMBOL):
        find_symbol = tool_catalog.get_function(ToolId.FIND_SYMBOL)
        result = await find_symbol(name=symbol_name, exact=True, include_body=False)
        attempt_history.append({"step": "find_symbol (exact)", "status": result.get("status")})

        if result.get("status") == "success" and result.get("symbols"):
            for sym in result["symbols"]:
                definitions.append({
                    "file": sym.get("file", ""),
                    "line": sym.get("line", 0),
                    "name": sym.get("name", symbol_name),
                    "type": sym.get("type", "unknown"),
                })
                all_citations.add(f"{sym.get('file')}:{sym.get('line', 1)}")

    # Step 2: If no exact match, try partial
    if not definitions and tool_catalog.has_tool_id(ToolId.FIND_SYMBOL):
        find_symbol = tool_catalog.get_function(ToolId.FIND_SYMBOL)
        result = await find_symbol(name=symbol_name, exact=False, include_body=False)
        attempt_history.append({"step": "find_symbol (partial)", "status": result.get("status")})

        if result.get("status") == "success" and result.get("symbols"):
            for sym in result["symbols"]:
                definitions.append({
                    "file": sym.get("file", ""),
                    "line": sym.get("line", 0),
                    "name": sym.get("name", symbol_name),
                    "type": sym.get("type", "unknown"),
                })
                all_citations.add(f"{sym.get('file')}:{sym.get('line', 1)}")

    # Step 3: Find usages via grep
    usages = []
    if tool_catalog.has_tool_id(ToolId.GREP_SEARCH):
        grep_search = tool_catalog.get_function(ToolId.GREP_SEARCH)
        pattern = rf"\b{re.escape(symbol_name)}\b"  # Word boundary for exact symbol
        result = await grep_search(
            pattern=pattern,
            max_results=context_bounds.max_grep_results if context_bounds else 50
        )
        attempt_history.append({"step": "grep_search (usages)", "status": result.get("status")})

        if result.get("status") == "success" and result.get("matches"):
            for match in result["matches"]:
                file_path = match.get("file", "")

                # Skip test files if not included
                if not include_tests and "/test" in file_path:
                    continue

                usages.append({
                    "file": file_path,
                    "line": match.get("line", 0),
                    "context": match.get("match", ""),
                })
                all_citations.add(f"{file_path}:{match.get('line', 1)}")

    # Return results
    if definitions or usages:
        return {
            "status": "success",
            "symbol": symbol_name,
            "definitions": definitions,
            "usages": usages,
            "attempt_history": attempt_history,
            "citations": sorted(list(all_citations)),
            "bounded": len(usages) >= (context_bounds.max_grep_results if context_bounds else 50),
        }
    else:
        _logger.info("explore_symbol_usage_not_found", symbol=symbol_name)
        return {
            "status": "not_found",
            "symbol": symbol_name,
            "definitions": [],
            "usages": [],
            "attempt_history": attempt_history,
            "citations": [],
            "message": f"No definitions or usages found for symbol '{symbol_name}'",
        }


__all__ = ["explore_symbol_usage"]
