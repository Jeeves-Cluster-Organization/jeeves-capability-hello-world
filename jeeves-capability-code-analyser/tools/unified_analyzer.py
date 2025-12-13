"""Unified Analysis Tool - Single entry point for code analysis.

Phase 2/4 Constitutional Compliance - No auto-registration at import time

Per Amendment XXII (Tool Consolidation), this mega-tool:
- Provides a single `analyze` entry point for all code analysis needs
- Internally orchestrates composite tools (explore_symbol_usage, map_module, etc.)
- Reduces plan complexity from N steps to 1 step for most queries
- Auto-detects target type (symbol, module, file, query)
- Returns comprehensive analysis with all relevant context

This replaces multi-step plans like:
    Steps: 2 | Tools: explore_symbol_usage, map_module

With:
    Steps: 1 | Tools: analyze

The tool intelligently routes to the appropriate composite tools based on
the target type and query intent.
"""

import re
from enum import Enum
from typing import Any, Dict, List, Optional

from jeeves_mission_system.adapters import get_logger
from jeeves_mission_system.contracts import ContextBounds, ToolId, tool_catalog
from jeeves_protocols import RiskLevel, OperationStatus, ToolCategory
from tools.robust_tool_base import AttemptRecord, CitationCollector


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
    citations = CitationCollector()
    attempts = []

    result = {
        "target": symbol,
        "target_type": "symbol",
        "definition": None,
        "usages": [],
        "module_context": None,
        "status": "success",
    }

    # Step 1: Find symbol definition and usages via explore_symbol_usage
    if tool_registry.has_tool("explore_symbol_usage"):
        explore = tool_registry.get_tool_function("explore_symbol_usage")
        try:
            explore_result = await explore(symbol_name=symbol, include_call_sites=include_usages)
            attempts.append(AttemptRecord(
                tool="explore_symbol_usage",
                status="success" if explore_result.get("status") == "success" else "partial",
                result_summary=f"Found {len(explore_result.get('usages', []))} usages"
            ))

            if explore_result.get("status") == "success":
                result["definition"] = explore_result.get("definition")
                result["usages"] = explore_result.get("usages", [])

                # Collect citations
                if explore_result.get("definition"):
                    defn = explore_result["definition"]
                    citations.add(defn.get("file", ""), defn.get("line", 0), "definition")
                for usage in explore_result.get("usages", [])[:5]:
                    citations.add(usage.get("file", ""), usage.get("line", 0), "usage")

        except Exception as e:
            _logger.warning("analyze_explore_symbol_error", symbol=symbol, error=str(e))
            attempts.append(AttemptRecord(tool="explore_symbol_usage", status="error", error=str(e)))

    # Step 2: Get module context if we found a definition
    if result["definition"] and tool_registry.has_tool("map_module"):
        defn_file = result["definition"].get("file", "")
        if defn_file:
            # Extract module path (directory containing the file)
            module_path = "/".join(defn_file.split("/")[:-1])
            if module_path:
                map_module = tool_registry.get_tool_function("map_module")
                try:
                    module_result = await map_module(module_path=module_path, depth=1)
                    attempts.append(AttemptRecord(
                        tool="map_module",
                        status="success" if module_result.get("status") == "success" else "partial",
                        result_summary=f"Mapped {module_path}"
                    ))

                    if module_result.get("status") == "success":
                        result["module_context"] = {
                            "path": module_path,
                            "structure": module_result.get("structure"),
                            "exports": module_result.get("exports", [])[:10],
                        }
                except Exception as e:
                    _logger.warning("analyze_map_module_error", module=module_path, error=str(e))
                    attempts.append(AttemptRecord(tool="map_module", status="error", error=str(e)))

    result["attempts"] = [a.__dict__ if hasattr(a, '__dict__') else a for a in attempts]
    result["citations"] = citations.to_list()
    return result


async def _analyze_module(module_path: str) -> Dict[str, Any]:
    """Analyze a module: structure, exports, dependencies."""
    _logger = get_logger()
    citations = CitationCollector()
    attempts = []

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
    if tool_registry.has_tool("map_module"):
        map_module = tool_registry.get_tool_function("map_module")
        try:
            module_result = await map_module(module_path=module_path, depth=2)
            attempts.append(AttemptRecord(
                tool="map_module",
                status="success" if module_result.get("status") == "success" else "partial",
                result_summary=f"Mapped {module_path}"
            ))

            if module_result.get("status") == "success":
                result["structure"] = module_result.get("structure")
                result["exports"] = module_result.get("exports", [])
                result["dependencies"] = module_result.get("dependencies", [])
                result["key_files"] = module_result.get("key_files", [])

                # Add citations for key files
                for f in result["key_files"][:5]:
                    citations.add(f, 1, "key_file")

        except Exception as e:
            _logger.warning("analyze_module_error", module=module_path, error=str(e))
            attempts.append(AttemptRecord(tool="map_module", status="error", error=str(e)))
            result["status"] = "partial"

    result["attempts"] = [a.__dict__ if hasattr(a, '__dict__') else a for a in attempts]
    result["citations"] = citations.to_list()
    return result


async def _analyze_file(file_path: str) -> Dict[str, Any]:
    """Analyze a file: read content, extract symbols."""
    _logger = get_logger()
    citations = CitationCollector()
    attempts = []

    result = {
        "target": file_path,
        "target_type": "file",
        "content": None,
        "symbols": [],
        "imports": [],
        "status": "success",
    }

    # Read the file content
    if tool_registry.has_tool("read_code"):
        read_code = tool_registry.get_tool_function("read_code")
        try:
            read_result = await read_code(path=file_path)
            attempts.append(AttemptRecord(
                tool="read_code",
                status="success" if read_result.get("status") == "success" else "error",
                result_summary=f"Read {file_path}"
            ))

            if read_result.get("status") == "success":
                result["content"] = read_result.get("content")
                result["symbols"] = read_result.get("symbols", [])
                citations.add(file_path, 1, "file_content")

        except Exception as e:
            _logger.warning("analyze_file_error", file=file_path, error=str(e))
            attempts.append(AttemptRecord(tool="read_code", status="error", error=str(e)))
            result["status"] = "error"

    result["attempts"] = [a.__dict__ if hasattr(a, '__dict__') else a for a in attempts]
    result["citations"] = citations.to_list()
    return result


async def _analyze_query(query: str) -> Dict[str, Any]:
    """Analyze a natural language query: locate relevant code."""
    _logger = get_logger()
    citations = CitationCollector()
    attempts = []

    result = {
        "target": query,
        "target_type": "query",
        "matches": [],
        "related_files": [],
        "status": "success",
    }

    # Use locate for finding relevant code
    if tool_registry.has_tool("locate"):
        locate = tool_registry.get_tool_function("locate")
        try:
            locate_result = await locate(query=query)
            attempts.append(AttemptRecord(
                tool="locate",
                status="success" if locate_result.get("status") == "success" else "partial",
                result_summary=f"Found {len(locate_result.get('matches', []))} matches"
            ))

            if locate_result.get("status") == "success":
                result["matches"] = locate_result.get("matches", [])

                for match in result["matches"][:5]:
                    citations.add(match.get("file", ""), match.get("line", 0), "match")

        except Exception as e:
            _logger.warning("analyze_query_error", query=query, error=str(e))
            attempts.append(AttemptRecord(tool="locate", status="error", error=str(e)))

    # Also find related files
    if tool_registry.has_tool("find_related"):
        find_related = tool_registry.get_tool_function("find_related")
        try:
            related_result = await find_related(query=query, max_results=5)
            attempts.append(AttemptRecord(
                tool="find_related",
                status="success" if related_result.get("status") == "success" else "partial",
                result_summary=f"Found {len(related_result.get('files', []))} related files"
            ))

            if related_result.get("status") == "success":
                result["related_files"] = related_result.get("files", [])

        except Exception as e:
            _logger.warning("analyze_query_find_related_error", query=query, error=str(e))
            attempts.append(AttemptRecord(tool="find_related", status="error", error=str(e)))

    result["attempts"] = [a.__dict__ if hasattr(a, '__dict__') else a for a in attempts]
    result["citations"] = citations.to_list()
    return result


async def analyze(
    target: str,
    *,
    target_type: Optional[str] = None,
    include_usages: bool = True,
    include_context: bool = True,
) -> Dict[str, Any]:
    """
    Unified analysis tool - single entry point for all code analysis.

    Automatically detects target type and orchestrates appropriate tools:
    - Symbol (e.g., "CodeAnalysisRuntime"): explore_symbol_usage + map_module
    - Module (e.g., "agents/"): map_module with full depth
    - File (e.g., "agents/planner.py"): read_code + symbol extraction
    - Query (e.g., "how does routing work"): locate + find_related

    Args:
        target: The analysis target (symbol, path, or query)
        target_type: Optional override for type detection ("symbol", "module", "file", "query")
        include_usages: For symbols, include usage sites (default: True)
        include_context: Include surrounding module context (default: True)

    Returns:
        Comprehensive analysis result with:
        - target: The analyzed target
        - target_type: Detected or specified type
        - [type-specific fields]: definition, usages, structure, content, etc.
        - attempts: Tools called and their status
        - citations: File:line references for evidence
        - status: "success", "partial", or "error"
    """
    _logger = get_logger()

    # Detect or use specified target type
    if target_type:
        try:
            detected_type = TargetType(target_type)
        except ValueError:
            detected_type = _detect_target_type(target)
    else:
        detected_type = _detect_target_type(target)

    _logger.info(
        "analyze_start",
        target=target,
        detected_type=detected_type.value,
        include_usages=include_usages,
        include_context=include_context,
    )

    # Route to appropriate analyzer
    if detected_type == TargetType.SYMBOL:
        result = await _analyze_symbol(target, include_usages=include_usages)
    elif detected_type == TargetType.MODULE:
        result = await _analyze_module(target)
    elif detected_type == TargetType.FILE:
        result = await _analyze_file(target)
    else:  # QUERY
        result = await _analyze_query(target)

    _logger.info(
        "analyze_complete",
        target=target,
        target_type=detected_type.value,
        status=result.get("status"),
        attempts_count=len(result.get("attempts", [])),
        citations_count=len(result.get("citations", [])),
    )

    return result


# Registration function (no longer auto-registers on import)
def _register_analyze_tool():
    """Register the unified analyze tool with canonical tool_catalog.

    Per Amendment XXII and Phase 2/4: Only registers with tool_catalog.
    No auto-registration at import time - must be called explicitly.
    """
    # Register with canonical tool_catalog (Decision 1:A compliance)
    if not tool_catalog.has_tool(ToolId.ANALYZE):
        tool_catalog.register_function(
            tool_id=ToolId.ANALYZE,
            func=analyze,
            description=(
                "Unified code analysis - automatically analyzes symbols, modules, files, or queries. "
                "Detects target type and orchestrates appropriate tools internally. "
                "Use this as the primary tool for most analysis tasks."
            ),
            parameters={
                "target": "string",
                "target_type": "string? (optional)",
                "include_usages": "boolean? (optional)",
                "include_context": "boolean? (optional)",
            },
            category=ToolCategory.UNIFIED,
        )


__all__ = ["analyze", "_register_analyze_tool"]
