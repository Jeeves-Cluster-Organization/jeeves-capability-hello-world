"""Code index tools - symbol lookup and import tracking.

Phase 2/4 Constitutional Compliance - No auto-registration at import time

These tools provide index-powered code navigation for fast lookups on large repos.
Requires code_index table to be populated by the indexer service.

Tools:
- find_symbol: Look up symbol definitions by name
- get_file_symbols: List all symbols in a file
- get_imports: Get imports for a file
- get_importers: Find files that import a given module

Language Support:
Uses language_config for consistent handling across all supported languages.
Python uses AST parsing; other languages use regex patterns from config.
"""

import ast
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from jeeves_mission_system.adapters import get_logger
from jeeves_mission_system.contracts import LoggerProtocol
from jeeves_protocols import RiskLevel
from tools.base.path_helpers import (
    get_repo_path,
    resolve_path,
    get_code_extensions,
    get_excluded_dirs,
    ensure_repo_path_valid,
    repo_path_error_response,
    get_language_config_from_registry,
)
from jeeves_capability_code_analyser.config import LanguageId


# Local aliases for backward compatibility
_get_repo_path = get_repo_path
_resolve_path = resolve_path
_ensure_repo_path_valid = ensure_repo_path_valid
_repo_path_error_response = repo_path_error_response


class PythonSymbolExtractor(ast.NodeVisitor):
    """Extract symbols from Python AST."""

    def __init__(self, source_code: str = ""):
        self.symbols: List[Dict[str, Any]] = []
        self.imports: List[str] = []
        self.source_code = source_code

    def _extract_body(self, node: ast.AST, max_chars: int = 500) -> str:
        """Extract source code for a node.

        Args:
            node: The AST node to extract source from
            max_chars: Maximum characters to return (default: 500)

        Returns:
            The source code segment, truncated if necessary
        """
        if not self.source_code:
            return ""
        try:
            body = ast.get_source_segment(self.source_code, node) or ""
            if len(body) > max_chars:
                return body[:max_chars] + "..."
            return body
        except Exception:
            return ""

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.symbols.append({
            "name": node.name,
            "kind": "class",
            "line": node.lineno,
            "end_line": node.end_lineno or node.lineno,
            "body": self._extract_body(node),
        })
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.symbols.append({
            "name": node.name,
            "kind": "function",
            "line": node.lineno,
            "end_line": node.end_lineno or node.lineno,
            "body": self._extract_body(node),
        })
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.symbols.append({
            "name": node.name,
            "kind": "async_function",
            "line": node.lineno,
            "end_line": node.end_lineno or node.lineno,
            "body": self._extract_body(node),
        })
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(alias.name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            self.imports.append(node.module)


def _extract_python_symbols(filepath: Path) -> Dict[str, Any]:
    """Extract symbols and imports from a Python file."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=str(filepath))
        extractor = PythonSymbolExtractor(source_code=content)
        extractor.visit(tree)
        return {
            "symbols": extractor.symbols,
            "imports": extractor.imports,
        }
    except SyntaxError as e:
        _logger = get_logger()
        _logger.warning("python_parse_error", file=str(filepath), error=str(e))
        return {"symbols": [], "imports": []}
    except Exception as e:
        _logger = get_logger()
        _logger.error("symbol_extraction_error", file=str(filepath), error=str(e))
        return {"symbols": [], "imports": []}


def _extract_typescript_symbols(filepath: Path) -> Dict[str, Any]:
    """Extract symbols from TypeScript/JavaScript files using regex."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()

        symbols = []
        imports = []

        # Patterns for TypeScript/JavaScript
        class_pattern = re.compile(r'^\s*(?:export\s+)?(?:abstract\s+)?class\s+(\w+)')
        func_pattern = re.compile(r'^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)')
        arrow_pattern = re.compile(r'^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(')
        interface_pattern = re.compile(r'^\s*(?:export\s+)?interface\s+(\w+)')
        type_pattern = re.compile(r'^\s*(?:export\s+)?type\s+(\w+)\s*=')
        import_pattern = re.compile(r'^\s*import\s+.*?from\s+[\'"]([^\'"]+)[\'"]')

        for i, line in enumerate(lines, start=1):
            # Check for class
            match = class_pattern.match(line)
            if match:
                symbols.append({"name": match.group(1), "kind": "class", "line": i, "end_line": i})
                continue

            # Check for function
            match = func_pattern.match(line)
            if match:
                symbols.append({"name": match.group(1), "kind": "function", "line": i, "end_line": i})
                continue

            # Check for arrow function
            match = arrow_pattern.match(line)
            if match:
                symbols.append({"name": match.group(1), "kind": "function", "line": i, "end_line": i})
                continue

            # Check for interface
            match = interface_pattern.match(line)
            if match:
                symbols.append({"name": match.group(1), "kind": "interface", "line": i, "end_line": i})
                continue

            # Check for type
            match = type_pattern.match(line)
            if match:
                symbols.append({"name": match.group(1), "kind": "type", "line": i, "end_line": i})
                continue

            # Check for import
            match = import_pattern.match(line)
            if match:
                imports.append(match.group(1))

        return {"symbols": symbols, "imports": imports}

    except Exception as e:
        _logger = get_logger()
        _logger.error("typescript_extraction_error", file=str(filepath), error=str(e))
        return {"symbols": [], "imports": []}


def _extract_symbols_generic(filepath: Path) -> Dict[str, Any]:
    """Extract symbols using language-agnostic regex patterns.

    Uses patterns from language_config for consistent handling
    across Go, Rust, Java, C/C++, Ruby, PHP, etc.
    """
    config = get_language_config_from_registry()
    patterns = config.get_symbol_patterns(str(filepath))

    if not any(patterns.values()):
        return {"symbols": [], "imports": []}

    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()

        symbols = []
        imports = []

        class_re = re.compile(patterns["class"]) if patterns.get("class") else None
        func_re = re.compile(patterns["function"]) if patterns.get("function") else None
        import_re = re.compile(patterns["import"]) if patterns.get("import") else None

        for i, line in enumerate(lines, start=1):
            # Check for class/struct/type
            if class_re:
                match = class_re.match(line)
                if match:
                    symbols.append({
                        "name": match.group(1),
                        "kind": "class",
                        "line": i,
                        "end_line": i,
                    })
                    continue

            # Check for function
            if func_re:
                match = func_re.match(line)
                if match:
                    symbols.append({
                        "name": match.group(1),
                        "kind": "function",
                        "line": i,
                        "end_line": i,
                    })
                    continue

            # Check for import
            if import_re:
                match = import_re.match(line)
                if match:
                    imports.append(match.group(1))

        return {"symbols": symbols, "imports": imports}

    except Exception as e:
        _logger = get_logger()
        _logger.error("generic_extraction_error", file=str(filepath), error=str(e))
        return {"symbols": [], "imports": []}


def _extract_symbols(filepath: Path) -> Dict[str, Any]:
    """Extract symbols based on file extension.

    Uses language_config to determine the appropriate extraction method:
    - Python: AST parsing (most accurate)
    - TypeScript/JavaScript: Specialized regex
    - Other languages: Generic regex from language_config
    """
    config = get_language_config_from_registry()
    lang_id = config.get_language_for_file(str(filepath))

    if lang_id is None:
        return {"symbols": [], "imports": []}

    # Python: Use AST for accuracy
    if lang_id == LanguageId.PYTHON:
        return _extract_python_symbols(filepath)

    # TypeScript/JavaScript: Use specialized extractor
    if lang_id in {LanguageId.TYPESCRIPT, LanguageId.JAVASCRIPT}:
        return _extract_typescript_symbols(filepath)

    # All other languages: Use generic regex extractor
    return _extract_symbols_generic(filepath)


async def find_symbol(
    name: str,
    kind: Optional[str] = None,
    exact: bool = False,
    max_results: int = 50,
    path_prefix: Optional[str] = None,
    include_body: bool = False,
) -> Dict[str, Any]:
    """Find symbol definitions by name.

    Args:
        name: Symbol name to search for
        kind: Filter by kind ('class', 'function', 'interface', 'type') or comma-separated list
        exact: Require exact name match (default: False)
        max_results: Maximum number of results (default: 50)
        path_prefix: Filter to files under this path prefix (optional)
        include_body: Include symbol body preview in results (default: False)

    Returns:
        Dict with:
        - status: "success" or "error"
        - symbols: List of matching symbols with file, line info
        - count: Number of matches
    """
    # Validate repo path exists
    if not _ensure_repo_path_valid():
        return _repo_path_error_response()

    repo_path = _get_repo_path()
    repo = Path(repo_path)

    if not name:
        return {
            "status": "error",
            "error": "Symbol name is required",
        }

    try:
        matches = []
        config = get_language_config_from_registry()
        excluded_dirs = config.exclude_dirs
        code_extensions = config.code_extensions

        # Parse kind filter (can be comma-separated)
        kind_filter = None
        if kind:
            kind_filter = set(k.strip().lower() for k in kind.split(","))

        # Clamp max_results to safe range
        result_limit = max(10, min(max_results, 500))

        for root, dirs, files in os.walk(repo):
            # Prune excluded directories
            dirs[:] = [d for d in dirs if d not in excluded_dirs]

            for filename in files:
                filepath = Path(root) / filename
                rel_path = str(filepath.relative_to(repo))

                # Apply path prefix filter
                if path_prefix and not rel_path.startswith(path_prefix.rstrip("/")):
                    continue

                if filepath.suffix.lower() not in code_extensions:
                    continue

                extraction = _extract_symbols(filepath)

                for symbol in extraction["symbols"]:
                    # Filter by kind if specified
                    if kind_filter and symbol["kind"].lower() not in kind_filter:
                        continue

                    # Match name
                    if exact:
                        if symbol["name"] != name:
                            continue
                    else:
                        if name.lower() not in symbol["name"].lower():
                            continue

                    match_info = {
                        "name": symbol["name"],
                        "kind": symbol["kind"],
                        "file": rel_path,
                        "line": symbol["line"],
                        "end_line": symbol.get("end_line", symbol["line"]),
                    }

                    # Include body if requested (truncated for response size)
                    if include_body and "body" in symbol:
                        body = symbol["body"][:200]
                        if len(symbol.get("body", "")) > 200:
                            body += "..."
                        match_info["body"] = body

                    matches.append(match_info)

        # Sort: exact matches first, then by file path
        matches.sort(key=lambda x: (0 if x["name"] == name else 1, x["file"], x["line"]))

        # Limit results
        truncated = len(matches) > result_limit
        matches = matches[:result_limit]

        return {
            "status": "success",
            "symbols": matches,
            "count": len(matches),
            "truncated": truncated,
            "search_name": name,
            "search_kind": kind,
            "path_prefix": path_prefix,
        }

    except Exception as e:
        _logger = get_logger()
        _logger.error("find_symbol_error", name=name, error=str(e))
        return {
            "status": "error",
            "error": f"Failed to search symbols: {e}",
        }


async def get_file_symbols(
    path: str,
    kind: Optional[str] = None,
    include_imports: bool = True,
    include_body: bool = False,
    name_pattern: Optional[str] = None,
) -> Dict[str, Any]:
    """List all symbols defined in a file.

    Args:
        path: Path to file relative to repo root
        kind: Filter by symbol kind (optional, comma-separated)
        include_imports: Include import information (default: True)
        include_body: Include symbol body preview (default: False)
        name_pattern: Filter symbols by name pattern (optional)

    Returns:
        Dict with:
        - status: "success" or "error"
        - symbols: List of symbols with name, kind, line info
        - imports: List of imported modules (if include_imports=True)
    """
    # Validate repo path exists
    if not _ensure_repo_path_valid():
        return _repo_path_error_response()

    repo_path = _get_repo_path()
    resolved = _resolve_path(path, repo_path)

    if resolved is None:
        return {
            "status": "error",
            "error": f"Path '{path}' is outside repository bounds",
        }

    if not resolved.exists():
        return {
            "status": "error",
            "error": f"File not found: {path}",
        }

    if not resolved.is_file():
        return {
            "status": "error",
            "error": f"Not a file: {path}",
        }

    try:
        extraction = _extract_symbols(resolved)

        # Parse kind filter (can be comma-separated)
        kind_filter = None
        if kind:
            kind_filter = set(k.strip().lower() for k in kind.split(","))

        # Filter and format symbols
        symbols = []
        for sym in extraction["symbols"]:
            # Apply kind filter
            if kind_filter and sym["kind"].lower() not in kind_filter:
                continue
            # Apply name pattern filter
            if name_pattern and name_pattern.lower() not in sym["name"].lower():
                continue

            sym_info = {
                "name": sym["name"],
                "kind": sym["kind"],
                "line": sym["line"],
                "end_line": sym.get("end_line", sym["line"]),
            }

            # Include body if requested (truncated for response size)
            if include_body and "body" in sym:
                body = sym["body"][:300]
                if len(sym.get("body", "")) > 300:
                    body += "..."
                sym_info["body"] = body

            symbols.append(sym_info)

        result = {
            "status": "success",
            "path": str(resolved.relative_to(repo_path)),
            "symbols": symbols,
            "symbol_count": len(symbols),
        }

        # Include imports if requested
        if include_imports:
            result["imports"] = extraction["imports"]
            result["import_count"] = len(extraction["imports"])

        return result

    except Exception as e:
        _logger = get_logger()
        _logger.error("get_file_symbols_error", path=path, error=str(e))
        return {
            "status": "error",
            "error": f"Failed to extract symbols: {e}",
        }


async def get_imports(path: str) -> Dict[str, Any]:
    """Get list of imports for a file.

    Args:
        path: Path to file relative to repo root

    Returns:
        Dict with:
        - status: "success" or "error"
        - imports: List of imported modules
        - categorized: Dict grouping imports by type (stdlib, local, external)
    """
    # Validate repo path exists
    if not _ensure_repo_path_valid():
        return _repo_path_error_response()

    repo_path = _get_repo_path()
    resolved = _resolve_path(path, repo_path)

    if resolved is None:
        return {
            "status": "error",
            "error": f"Path '{path}' is outside repository bounds",
        }

    if not resolved.exists():
        return {
            "status": "error",
            "error": f"File not found: {path}",
        }

    try:
        extraction = _extract_symbols(resolved)
        imports = extraction["imports"]

        # Categorize imports (Python-specific)
        stdlib_modules = {
            "os", "sys", "re", "json", "typing", "collections", "itertools",
            "functools", "pathlib", "datetime", "time", "math", "random",
            "hashlib", "subprocess", "asyncio", "abc", "dataclasses", "enum",
            "contextlib", "unittest", "logging", "argparse", "io", "copy",
        }

        categorized = {
            "stdlib": [],
            "local": [],
            "external": [],
        }

        repo = Path(repo_path)
        for imp in imports:
            # Check if local import (relative or project module)
            parts = imp.split(".")
            first_part = parts[0]

            # Check if it's a local module by looking for it in the repo
            potential_path = repo / first_part
            potential_file = repo / f"{first_part}.py"

            if potential_path.exists() or potential_file.exists():
                categorized["local"].append(imp)
            elif first_part in stdlib_modules:
                categorized["stdlib"].append(imp)
            else:
                categorized["external"].append(imp)

        return {
            "status": "success",
            "path": str(resolved.relative_to(repo_path)),
            "imports": imports,
            "categorized": categorized,
            "count": len(imports),
        }

    except Exception as e:
        _logger = get_logger()
        _logger.error("get_imports_error", path=path, error=str(e))
        return {
            "status": "error",
            "error": f"Failed to get imports: {e}",
        }


async def get_importers(
    module_name: str,
    exact: bool = False,
    max_results: int = 100,
    path_prefix: Optional[str] = None,
    include_line_info: bool = False,
) -> Dict[str, Any]:
    """Find files that import a given module.

    Args:
        module_name: Module name to search for
        exact: Require exact module match (default: False)
        max_results: Maximum number of results (default: 100)
        path_prefix: Filter to files under this path prefix (optional)
        include_line_info: Include import line numbers (default: False)

    Returns:
        Dict with:
        - status: "success" or "error"
        - importers: List of files that import this module
        - count: Number of importing files
    """
    # Validate repo path exists
    if not _ensure_repo_path_valid():
        return _repo_path_error_response()

    repo_path = _get_repo_path()
    repo = Path(repo_path)

    if not module_name:
        return {
            "status": "error",
            "error": "Module name is required",
        }

    try:
        importers = []
        config = get_language_config_from_registry()
        excluded_dirs = config.exclude_dirs
        code_extensions = config.code_extensions

        # Clamp max_results to safe range
        result_limit = max(10, min(max_results, 500))

        for root, dirs, files in os.walk(repo):
            # Prune excluded directories
            dirs[:] = [d for d in dirs if d not in excluded_dirs]

            for filename in files:
                filepath = Path(root) / filename
                rel_path = str(filepath.relative_to(repo))

                # Apply path prefix filter
                if path_prefix and not rel_path.startswith(path_prefix.rstrip("/")):
                    continue

                if filepath.suffix.lower() not in code_extensions:
                    continue

                extraction = _extract_symbols(filepath)

                for imp in extraction["imports"]:
                    if exact:
                        match = imp == module_name
                    else:
                        match = module_name.lower() in imp.lower()

                    if match:
                        if include_line_info:
                            # Try to find the line number (basic search)
                            try:
                                content = filepath.read_text(encoding="utf-8", errors="replace")
                                line_num = None
                                for i, line in enumerate(content.splitlines(), 1):
                                    if "import" in line and imp in line:
                                        line_num = i
                                        break
                                importers.append({
                                    "file": rel_path,
                                    "import": imp,
                                    "line": line_num,
                                })
                            except Exception:
                                importers.append({"file": rel_path, "import": imp})
                        else:
                            importers.append(rel_path)
                        break

        # Sort by path (handle both string and dict formats)
        if importers and isinstance(importers[0], dict):
            importers.sort(key=lambda x: x["file"])
        else:
            importers.sort()

        # Limit results
        truncated = len(importers) > result_limit
        importers = importers[:result_limit]

        return {
            "status": "success",
            "module_name": module_name,
            "importers": importers,
            "count": len(importers),
            "truncated": truncated,
            "path_prefix": path_prefix,
        }

    except Exception as e:
        _logger = get_logger()
        _logger.error("get_importers_error", module=module_name, error=str(e))
        return {
            "status": "error",
            "error": f"Failed to find importers: {e}",
        }


__all__ = ["find_symbol", "get_file_symbols", "get_imports", "get_importers"]
