"""Flow Tracer - Trace execution flow from entry points to implementation.

Phase 2/4 Constitutional Compliance - No auto-registration at import time

Per Amendment XVII (Composite Tool Contracts), this tool:
- Orchestrates multiple primitive tools in a deterministic sequence
- Returns attempt_history for transparency
- Aggregates citations from all steps
- Respects context bounds
- Degrades gracefully on step failures
"""

import re
from typing import Any, Dict, List, Optional

from jeeves_protocols import LoggerProtocol
from .catalog import ToolId, tool_catalog
from jeeves_protocols import RiskLevel
# Domain-specific bounds from capability config (per Constitution R6)
from jeeves_capability_code_analyser.config import CodeAnalysisBounds

# Framework-specific patterns for entry point detection
FRAMEWORK_PATTERNS = {
    "fastapi": {
        "route": r'@(app|router)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
        "import": r'from\s+fastapi\s+import|import\s+fastapi',
        "name": "FastAPI",
    },
    "flask": {
        "route": r'@(app|blueprint|bp)\.route\s*\(\s*["\']([^"\']+)["\']',
        "import": r'from\s+flask\s+import|import\s+flask',
        "name": "Flask",
    },
    "django": {
        "route": r'path\s*\(\s*["\']([^"\']+)["\']',
        "import": r'from\s+django|import\s+django',
        "name": "Django",
    },
    "click": {
        "command": r'@click\.command\(\s*["\']?([^"\']*)?["\']?\)',
        "import": r'import\s+click|from\s+click\s+import',
        "name": "Click",
    },
    "typer": {
        "command": r'@app\.command\(\s*["\']?([^"\']*)?["\']?\)',
        "import": r'import\s+typer|from\s+typer\s+import',
        "name": "Typer",
    },
}


async def _detect_framework() -> Dict[str, Any]:
    """Detect which web/CLI framework is used in the project."""
    if not tool_catalog.has_tool_id(ToolId.GREP_SEARCH):
        return {"status": "tool_unavailable", "frameworks": [], "primary": None}

    grep_search = tool_catalog.get_function(ToolId.GREP_SEARCH)
    detected = []

    for fid, patterns in FRAMEWORK_PATTERNS.items():
        try:
            result = await grep_search(pattern=patterns["import"], max_results=1)
            if result.get("status") == "success" and result.get("matches"):
                detected.append({
                    "id": fid,
                    "name": patterns["name"],
                    "evidence_file": result["matches"][0].get("file", ""),
                })
        except Exception:
            pass

    return {
        "status": "found" if detected else "no_match",
        "frameworks": detected,
        "primary": detected[0] if detected else None,
    }


async def _find_entry_points(entry_type: str, pattern: str, framework: Optional[Dict]) -> Dict[str, Any]:
    """Find entry point definitions."""
    if not tool_catalog.has_tool_id(ToolId.GREP_SEARCH):
        return {"status": "tool_unavailable", "entry_points": []}

    grep_search = tool_catalog.get_function(ToolId.GREP_SEARCH)
    entry_points = []

    if entry_type == "http_route":
        search_patterns = []
        if framework and framework.get("id") in FRAMEWORK_PATTERNS:
            route_pattern = FRAMEWORK_PATTERNS[framework["id"]].get("route")
            if route_pattern:
                search_patterns.append(route_pattern)
        search_patterns.append(re.escape(pattern))

        for search_pat in search_patterns:
            try:
                result = await grep_search(pattern=search_pat, max_results=20)
                if result.get("status") == "success":
                    for match in result.get("matches", []):
                        if pattern in match.get("match", "") or pattern in match.get("context", ""):
                            entry_points.append({
                                "file": match["file"],
                                "line": match["line"],
                                "match": match.get("match", ""),
                                "type": "http_route",
                            })
            except Exception:
                pass

    elif entry_type == "cli_command":
        search_pattern = f"command.*{re.escape(pattern)}|def\\s+{re.escape(pattern)}"
        try:
            result = await grep_search(pattern=search_pattern, max_results=20)
            if result.get("status") == "success":
                for match in result.get("matches", []):
                    entry_points.append({
                        "file": match["file"],
                        "line": match["line"],
                        "match": match.get("match", ""),
                        "type": "cli_command",
                    })
        except Exception:
            pass

    elif entry_type == "event_handler":
        search_pattern = f"on_{re.escape(pattern)}|handle_{re.escape(pattern)}|@.*{re.escape(pattern)}"
        try:
            result = await grep_search(pattern=search_pattern, max_results=20)
            if result.get("status") == "success":
                for match in result.get("matches", []):
                    entry_points.append({
                        "file": match["file"],
                        "line": match["line"],
                        "match": match.get("match", ""),
                        "type": "event_handler",
                    })
        except Exception:
            pass

    else:  # Generic function search
        search_pattern = f"def\\s+{re.escape(pattern)}|class\\s+{re.escape(pattern)}"
        try:
            result = await grep_search(pattern=search_pattern, max_results=20)
            if result.get("status") == "success":
                for match in result.get("matches", []):
                    entry_points.append({
                        "file": match["file"],
                        "line": match["line"],
                        "match": match.get("match", ""),
                        "type": "function",
                    })
        except Exception:
            pass

    return {"status": "found" if entry_points else "no_match", "entry_points": entry_points}


async def _trace_calls(file_path: str, start_line: int) -> Dict[str, Any]:
    """Trace function calls from a starting point."""
    _logger = get_logger()
    if not tool_catalog.has_tool_id(ToolId.READ_FILE):
        return {"status": "tool_unavailable", "calls": []}

    read_file = tool_catalog.get_function(ToolId.READ_FILE)
    try:
        result = await read_file(path=file_path, start_line=start_line, end_line=start_line + 50, max_tokens=2000)
        if result.get("status") != "success":
            return {"status": "no_data", "calls": []}

        content = result.get("content", "")
        keywords = {"if", "while", "for", "with", "return", "yield", "raise", "assert", "except", "class", "def"}
        builtins = {"print", "len", "str", "int", "list", "dict", "set", "range"}
        call_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s*\('

        calls = []
        for match in re.finditer(call_pattern, content):
            call_name = match.group(1)
            base_name = call_name.split(".")[0]
            if base_name not in keywords and base_name not in builtins:
                calls.append({"name": call_name, "file": file_path, "context": match.group(0)[:50]})

        return {"status": "found" if calls else "no_match", "calls": calls[:20]}
    except Exception as e:
        _logger.warning("flow_tracer_read_error", error=str(e))
        return {"status": "error", "calls": [], "error": str(e)}


async def _resolve_target(call_name: str) -> Dict[str, Any]:
    """Resolve where a called function is defined."""
    if not tool_catalog.has_tool_id(ToolId.FIND_SYMBOL):
        return {"status": "tool_unavailable", "target": None}

    find_symbol = tool_catalog.get_function(ToolId.FIND_SYMBOL)
    symbol_to_find = call_name.split(".")[-1]  # Get method/function name

    try:
        result = await find_symbol(name=symbol_to_find, exact=True)
        if result.get("status") == "success" and result.get("symbols"):
            sym = result["symbols"][0]
            return {
                "status": "found",
                "target": {
                    "file": sym.get("file", ""),
                    "line": sym.get("line", 0),
                    "name": sym.get("name", symbol_to_find),
                    "type": sym.get("type", ""),
                },
            }
    except Exception:
        pass

    return {"status": "no_match", "target": None}


def _build_flow_diagram(entry_points: List[Dict], call_chains: List[Dict]) -> str:
    """Build a simplified execution flow diagram."""
    if not entry_points:
        return "No entry points found"

    lines = ["Execution Flow:", ""]

    for i, chain in enumerate(call_chains):
        ep = chain["entry_point"]
        calls = chain.get("calls", [])

        lines.append(f"Entry Point {i+1}: {ep['type']}")
        lines.append(f"  └─ {ep['file']}:{ep['line']}")

        for j, call in enumerate(calls[:5]):
            connector = "├─" if j < len(calls) - 1 else "└─"
            lines.append(f"     {connector}▸ {call['callee_name']}")
            lines.append(f"        ({call['callee_file']}:{call['callee_line']})")

        if len(calls) > 5:
            lines.append(f"       ... and {len(calls) - 5} more calls")
        lines.append("")

    return "\n".join(lines)


async def trace_entry_point(
    entry_type: str,
    pattern: str,
    context_bounds: CodeAnalysisBounds,
    max_depth: int = 5,
) -> Dict[str, Any]:
    """Trace execution flow from an entry point to implementation.

    Pipeline:
    1. Detect framework (Flask, FastAPI, Django, Click, etc.)
    2. Find entry point definition via framework-specific patterns
    3. Trace call chain using read_file + symbol analysis
    4. Build execution flow graph

    Args:
        entry_type: Type of entry point (http_route, cli_command, event_handler, function)
        pattern: Pattern to search for entry point
        context_bounds: Context bounds configuration (from AppContext)
        max_depth: Maximum call chain depth to trace
    """
    bounds = context_bounds
    attempt_history = []
    all_citations = set()
    bounded = False
    step = 0

    # Step 1: Detect framework
    step += 1
    attempt_history.append({"step": step, "strategy": "framework_detection", "result": "pending", "params": {"purpose": "detect_framework"}})

    framework_result = await _detect_framework()
    attempt_history[-1]["result"] = framework_result["status"]

    framework = framework_result.get("primary")
    frameworks_found = framework_result.get("frameworks", [])

    # Step 2: Find entry points
    step += 1
    attempt_history.append({"step": step, "strategy": "find_entry_points", "result": "pending", "params": {"entry_type": entry_type, "pattern": pattern}})

    entry_result = await _find_entry_points(entry_type, pattern, framework)
    attempt_history[-1]["result"] = entry_result["status"]

    entry_points = entry_result.get("entry_points", [])

    # Add citations for entry points
    for ep in entry_points:
        all_citations.add(f"{ep['file']}:{ep['line']}")

    # Step 3: Trace call chain from each entry point
    call_chains = []

    for ep in entry_points[:3]:  # Limit to first 3 entry points
        step += 1
        attempt_history.append({"step": step, "strategy": "trace_calls", "result": "pending", "params": {"file": ep["file"], "line": ep["line"]}})

        trace_result = await _trace_calls(ep["file"], ep["line"])
        attempt_history[-1]["result"] = trace_result["status"]

        calls = trace_result.get("calls", [])

        # Step 4: Resolve call targets
        resolved_calls = []
        for call in calls[:10]:
            target_result = await _resolve_target(call["name"])
            if target_result["status"] == "found" and target_result.get("target"):
                target = target_result["target"]
                resolved_calls.append({
                    "caller_file": ep["file"],
                    "caller_line": ep["line"],
                    "callee_name": call["name"],
                    "callee_file": target["file"],
                    "callee_line": target["line"],
                })
                all_citations.add(f"{target['file']}:{target['line']}")

            if len(resolved_calls) >= bounds.max_call_chain_length:
                bounded = True
                break

        call_chains.append({"entry_point": ep, "calls": resolved_calls})

    # Build execution flow
    execution_flow = _build_flow_diagram(entry_points, call_chains)

    # Determine status
    if entry_points:
        status = "success"
    elif any(h.get("result") == "error" for h in attempt_history):
        status = "partial"
    else:
        status = "success"

    _logger = get_logger()
    _logger.info(
        "trace_entry_point_completed",
        entry_type=entry_type,
        pattern=pattern,
        entry_points_found=len(entry_points),
        call_chains=len(call_chains),
    )

    return {
        "status": status,
        "entry_type": entry_type,
        "pattern": pattern,
        "framework": framework,
        "frameworks_detected": frameworks_found,
        "entry_points": entry_points,
        "entry_point_count": len(entry_points),
        "call_chains": call_chains,
        "execution_flow": execution_flow,
        "attempt_history": attempt_history,
        "citations": sorted(list(all_citations)),
        "bounded": bounded,
    }


__all__ = ["trace_entry_point"]
