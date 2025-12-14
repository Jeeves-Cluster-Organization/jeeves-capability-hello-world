"""Module Mapper - Map module structure, dependencies, and responsibilities.

Phase 2/4 Constitutional Compliance - No auto-registration at import time

Per Amendment XVII (Composite Tool Contracts), this tool:
- Orchestrates multiple primitive tools in a deterministic sequence
- Returns attempt_history for transparency
- Aggregates citations from all steps
- Respects context bounds
- Degrades gracefully on step failures
"""

from typing import Any, Dict, List, Optional
from collections import defaultdict

from jeeves_mission_system.adapters import get_logger
from jeeves_mission_system.contracts import ToolId, tool_catalog,  LoggerProtocol, ContextBounds
from jeeves_protocols import RiskLevel, OperationStatus
from config.tool_profiles import detect_semantic_mismatch


async def _get_tree(module_path: str, depth: int) -> Dict[str, Any]:
    """Get directory tree for the module."""
    _logger = get_logger()
    if not tool_catalog.has_tool_id(ToolId.TREE_STRUCTURE):
        return {"status": "tool_unavailable", "tree": "", "file_count": 0, "dir_count": 0}

    tree_structure = tool_catalog.get_function(ToolId.TREE_STRUCTURE)
    try:
        result = await tree_structure(path=module_path, depth=depth, max_entries=500)
        if result.get("status") == "success":
            return {
                "status": "found",
                "tree": result.get("tree", ""),
                "file_count": result.get("file_count", 0),
                "dir_count": result.get("dir_count", 0),
            }
        return {"status": "no_data", "tree": "", "file_count": 0, "dir_count": 0}
    except Exception as e:
        _logger.warning("module_mapper_tree_error", error=str(e))
        return {"status": "error", "tree": "", "file_count": 0, "dir_count": 0, "error": str(e)}


async def _get_files(module_path: str) -> Dict[str, Any]:
    """Get list of Python files in the module."""
    _logger = get_logger()
    if not tool_catalog.has_tool_id(ToolId.GLOB_FILES):
        return {"status": "tool_unavailable", "files": []}

    glob_files = tool_catalog.get_function(ToolId.GLOB_FILES)
    try:
        pattern = f"{module_path}/**/*.py" if module_path else "**/*.py"
        result = await glob_files(pattern=pattern, max_results=100)
        if result.get("status") == "success":
            return {"status": "found", "files": result.get("files", [])}
        return {"status": "no_data", "files": []}
    except Exception as e:
        _logger.warning("module_mapper_glob_error", error=str(e))
        return {"status": "error", "files": [], "error": str(e)}


async def _get_symbols(file_path: str) -> Dict[str, Any]:
    """Get symbols defined in a file."""
    _logger = get_logger()
    if not tool_catalog.has_tool_id(ToolId.GET_FILE_SYMBOLS):
        return {"status": "tool_unavailable", "symbols": []}

    get_file_symbols = tool_catalog.get_function(ToolId.GET_FILE_SYMBOLS)
    try:
        result = await get_file_symbols(path=file_path, include_body=False)
        if result.get("status") == "success":
            return {"status": "found", "symbols": result.get("symbols", [])}
        return {"status": "no_data", "symbols": []}
    except Exception as e:
        _logger.warning("module_mapper_symbols_error", file=file_path, error=str(e))
        return {"status": "error", "symbols": [], "error": str(e)}


async def _get_imports(file_path: str) -> Dict[str, Any]:
    """Get imports from a file."""
    _logger = get_logger()
    if not tool_catalog.has_tool_id(ToolId.GET_IMPORTS):
        return {"status": "tool_unavailable", "imports": []}

    get_imports = tool_catalog.get_function(ToolId.GET_IMPORTS)
    try:
        result = await get_imports(path=file_path)
        if result.get("status") == "success":
            return {"status": "found", "imports": result.get("imports", [])}
        return {"status": "no_data", "imports": []}
    except Exception as e:
        _logger.warning("module_mapper_imports_error", file=file_path, error=str(e))
        return {"status": "error", "imports": [], "error": str(e)}


async def _get_consumers(module_path: str) -> Dict[str, Any]:
    """Get files that import from this module."""
    _logger = get_logger()
    if not tool_catalog.has_tool_id(ToolId.GET_IMPORTERS):
        return {"status": "tool_unavailable", "consumers": []}

    get_importers = tool_catalog.get_function(ToolId.GET_IMPORTERS)
    try:
        module_name = module_path.replace("/", ".").replace("\\", ".")
        if module_name.endswith(".py"):
            module_name = module_name[:-3]

        result = await get_importers(module_name=module_name)
        if result.get("status") == "success":
            return {"status": "found", "consumers": result.get("importers", [])}
        return {"status": "no_data", "consumers": []}
    except Exception as e:
        _logger.warning("module_mapper_consumers_error", error=str(e))
        return {"status": "error", "consumers": [], "error": str(e)}


def _categorize_symbols(symbols: List[Dict]) -> Dict[str, List[str]]:
    """Categorize symbols by type."""
    categories: Dict[str, List[str]] = {"classes": [], "functions": [], "constants": [], "other": []}

    for sym in symbols:
        name = sym.get("name", "")
        sym_type = sym.get("type", "").lower()

        if sym_type == "class":
            categories["classes"].append(name)
        elif sym_type in ("function", "method", "def"):
            categories["functions"].append(name)
        elif name.isupper():
            categories["constants"].append(name)
        else:
            categories["other"].append(name)

    return categories


def _categorize_imports(imports: List[Dict], module_path: str) -> Dict[str, List[str]]:
    """Categorize imports as internal or external."""
    internal: List[str] = []
    external: List[str] = []
    module_parts = module_path.replace("/", ".").replace("\\", ".").split(".")

    for imp in imports:
        module = imp.get("module", "") if isinstance(imp, dict) else str(imp)
        is_internal = module.startswith(".") or any(part and part in module for part in module_parts)
        if is_internal:
            internal.append(module)
        else:
            external.append(module)

    return {"internal": list(set(internal)), "external": list(set(external))}


def _infer_responsibilities(module_path: str, symbols: Dict[str, List[str]], files: List[str]) -> str:
    """Infer module responsibilities from its structure."""
    parts = []
    module_name = module_path.split("/")[-1].lower()

    patterns = [
        ("agent", "Agent definitions"),
        ("tool", "Tool implementations"),
        ("api", "API endpoints"),
        ("config", "Configuration management"),
        ("test", "Test suites"),
        ("model", "Data models"),
        ("service", "Service layer"),
        ("util", "Shared utilities"),
        ("common", "Shared utilities"),
        ("memory", "Memory/state management"),
    ]

    for pattern, desc in patterns:
        if pattern in module_name:
            parts.append(desc)

    if symbols.get("classes"):
        parts.append(f"{len(symbols['classes'])} classes")
    if symbols.get("functions"):
        parts.append(f"{len(symbols['functions'])} functions")

    return " | ".join(parts) if parts else f"Module with {len(files)} files"


async def map_module(
    module_path: str,
    context_bounds: ContextBounds,
    include_external: bool = False,
    summary_style: str = "compact",
) -> Dict[str, Any]:
    """Map a module's structure, dependencies, and responsibilities.

    Pipeline:
    0. Validate module_path is a directory/module, not a single file
    1. tree_structure(path=module_path) -> file list
    2. glob_files(pattern=*.py) -> Python files
    3. For each file: get_file_symbols() -> symbols
    4. For each file: get_imports() -> dependencies
    5. get_importers(module_name) -> consumers
    6. Build dependency graph and responsibility summary

    Args:
        module_path: Path to module/directory to map
        context_bounds: Context bounds configuration (from AppContext)
        include_external: Include external dependencies
        summary_style: Output style ("compact", "detailed", "full")
    """
    # SEMANTIC VALIDATION: Detect if module_path is actually a single file
    _logger = get_logger()
    is_mismatch, reason, suggested_tool = detect_semantic_mismatch(
        tool_name="map_module",
        param_name="module_path",
        param_value=module_path,
    )
    if is_mismatch:
        _logger.warning(
            "map_module_invalid_params",
            module_path=module_path,
            reason=reason,
            suggested_tool=suggested_tool,
        )
        return {
            "status": OperationStatus.INVALID_PARAMETERS.value,
            "error": reason,
            "message": f"'{module_path}' is a single file, not a module/directory. "
                       "Use read_code to read file contents, or provide a directory path like 'agents/'.",
            "suggested_tool": suggested_tool,
            "suggested_params": {"path": module_path},
            "module": module_path,
            "files": [],  # ALWAYS a list
            "file_count": 0,  # Separate count field
            "symbols": {},
            "dependencies": {},
            "consumers": [],
            "attempt_history": [],  # ALWAYS a list (Amendment XVII)
            "citations": [],
        }

    bounds = context_bounds
    attempt_history = []
    all_citations = set()
    bounded = False
    step = 0

    module_path = module_path.rstrip("/")

    # Step 1: Get module tree structure
    step += 1
    attempt_history.append({"step": step, "strategy": "tree_structure", "result": "pending", "params": {"path": module_path}})

    tree_result = await _get_tree(module_path, depth=3)
    attempt_history[-1]["result"] = tree_result["status"]
    if tree_result.get("error"):
        attempt_history[-1]["error"] = tree_result["error"]

    tree_text = tree_result.get("tree", "")
    file_count = tree_result.get("file_count", 0)
    dir_count = tree_result.get("dir_count", 0)

    # Step 2: Get file list
    step += 1
    attempt_history.append({"step": step, "strategy": "glob_files", "result": "pending", "params": {"pattern": f"{module_path}/**/*.py"}})

    files_result = await _get_files(module_path)
    attempt_history[-1]["result"] = files_result["status"]

    files = files_result.get("files", [])

    # Limit files based on bounds
    max_files = min(len(files), bounds.max_files_per_query // 2)
    if len(files) > max_files:
        bounded = True
        files = files[:max_files]

    # Step 3: Get symbols from each file
    all_symbols: List[Dict] = []
    for file_path in files:
        step += 1
        attempt_history.append({"step": step, "strategy": "get_file_symbols", "result": "pending", "params": {"path": file_path}})

        sym_result = await _get_symbols(file_path)
        attempt_history[-1]["result"] = sym_result["status"]

        for sym in sym_result.get("symbols", []):
            sym["file"] = file_path
            all_symbols.append(sym)
            all_citations.add(f"{file_path}:{sym.get('line', 1)}")

        if len(all_symbols) >= bounds.max_symbols_in_summary:
            bounded = True
            break

    symbol_categories = _categorize_symbols(all_symbols)

    # Step 4: Get imports from each file
    all_imports: List[Dict] = []
    internal_deps: Dict[str, List[str]] = defaultdict(list)

    for file_path in files[:20]:  # Limit import analysis
        step += 1
        attempt_history.append({"step": step, "strategy": "get_imports", "result": "pending", "params": {"path": file_path}})

        imp_result = await _get_imports(file_path)
        attempt_history[-1]["result"] = imp_result["status"]

        file_imports = imp_result.get("imports", [])
        all_imports.extend(file_imports)

        categorized = _categorize_imports(file_imports, module_path)
        for dep in categorized["internal"]:
            internal_deps[file_path].append(dep)

    import_categories = _categorize_imports(all_imports, module_path)

    # Step 5: Get consumers
    step += 1
    attempt_history.append({"step": step, "strategy": "get_importers", "result": "pending", "params": {"module": module_path}})

    consumers_result = await _get_consumers(module_path)
    attempt_history[-1]["result"] = consumers_result["status"]

    consumers = consumers_result.get("consumers", [])

    # Infer responsibilities
    responsibilities = _infer_responsibilities(module_path, symbol_categories, files)

    # Build dependency graph for graph style
    dep_graph = None
    if summary_style == "graph":
        dep_graph = {
            "internal": dict(internal_deps),
            "external": import_categories["external"] if include_external else [],
            "consumers": consumers,
        }

    # Determine status
    if files or all_symbols:
        status = "success"
    elif any(h.get("result") == "error" for h in attempt_history):
        status = "partial"
    else:
        status = "success"

    _logger.info(
        "map_module_completed",
        module=module_path,
        file_count=len(files),
        symbol_count=len(all_symbols),
        consumer_count=len(consumers),
    )

    # Per contracts/code_analysis: normalize field names
    # - files: ALWAYS a list (truncated in compact mode)
    # - file_count: the total count
    # - attempt_history: ALWAYS a list (per Amendment XVII)
    return {
        "status": status,
        "module": module_path,
        "files": files if summary_style == "detailed" else files[:10],  # ALWAYS a list
        "file_count": len(files),  # Separate count field
        "dir_count": dir_count,
        "tree": tree_text if summary_style == "detailed" else None,
        "symbols": symbol_categories,
        "symbol_count": len(all_symbols),
        "internal_deps": dict(internal_deps) if summary_style == "detailed" else import_categories["internal"],
        "external_deps": import_categories["external"] if include_external else [],
        "consumers": consumers,
        "consumer_count": len(consumers),
        "responsibilities": responsibilities,
        "dep_graph": dep_graph,
        "attempt_history": attempt_history,
        "citations": sorted(list(all_citations))[:bounds.max_matches_in_summary],
        "bounded": bounded,
    }


__all__ = ["map_module"]
