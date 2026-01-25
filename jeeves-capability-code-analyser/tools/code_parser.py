"""Code parser tools for code analysis.

These tools provide code parsing capabilities using REGEX (not AST) for
multi-language support (Python, JavaScript, Go, etc.).

Tools:
- parse_symbols: Extract functions/classes from a file
- find_references: Text search for symbol usages
- get_dependencies: Extract imports and store in graph
- get_dependents: Reverse lookup - what imports a module

IMPORTANT: Uses Regex-based parsing for multi-language support.
           Does NOT use the ast module.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from protocols import LoggerProtocol
import structlog
get_logger = structlog.get_logger
from tools.registry import RiskLevel, tool_registry
from tools.base.path_helpers import (
    get_repo_path,
    resolve_path,
    get_excluded_dirs,
    ensure_repo_path_valid,
    repo_path_error_response,
)
# Constitutional imports - from mission_system contracts layer
from mission_system.contracts import ContextBounds


# Regex patterns for different languages
SYMBOL_PATTERNS = {
    # Python patterns
    ".py": {
        "function": r"^\s*(?:async\s+)?def\s+(\w+)\s*\(",
        "class": r"^\s*class\s+(\w+)\s*[\(:]",
        "import": r"^(?:from\s+([\w.]+)\s+)?import\s+([\w.,\s]+)",
        "variable": r"^(\w+)\s*=\s*",
    },
    # JavaScript/TypeScript patterns
    ".js": {
        "function": r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[\w$]+)\s*=>|(\w+)\s*:\s*(?:async\s+)?function)",
        "class": r"class\s+(\w+)",
        "import": r"(?:import\s+(?:{[^}]+}|\w+|\*\s+as\s+\w+)\s+from\s+['\"]([^'\"]+)['\"]|require\s*\(\s*['\"]([^'\"]+)['\"]\s*\))",
        "variable": r"(?:const|let|var)\s+(\w+)\s*=",
    },
    ".ts": {
        "function": r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[\w$]+)\s*=>|(\w+)\s*:\s*(?:async\s+)?function)",
        "class": r"(?:class|interface)\s+(\w+)",
        "import": r"import\s+(?:{[^}]+}|\w+|\*\s+as\s+\w+)\s+from\s+['\"]([^'\"]+)['\"]",
        "variable": r"(?:const|let|var)\s+(\w+)\s*[=:]",
    },
    # Go patterns
    ".go": {
        "function": r"func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(",
        "class": r"type\s+(\w+)\s+struct",
        "import": r"import\s+(?:\(\s*([^)]+)\s*\)|\"([^\"]+)\")",
        "variable": r"(?:var|const)\s+(\w+)\s+",
    },
}


class CodeParserTools:
    """Code parser tools using Regex-based parsing.

    IMPORTANT: Does NOT use Python's ast module.
    Uses regex patterns for multi-language support.

    Provides capabilities to:
    - Parse symbols (functions, classes) from source files
    - Find references to symbols across the codebase
    - Extract import dependencies from files
    - Query reverse dependencies (what imports a module)
    """

    def __init__(
        self,
        bounds: Optional[ContextBounds] = None,
        logger: Optional[LoggerProtocol] = None,
    ):
        """Initialize code parser tools.

        Args:
            bounds: Optional context bounds configuration
            logger: Optional logger instance
        """
        self.bounds = bounds or ContextBounds()
        self._logger = logger or get_logger()

    def _get_patterns_for_file(self, file_path: str) -> Optional[Dict[str, str]]:
        """Get regex patterns for a file based on extension."""
        ext = Path(file_path).suffix.lower()
        return SYMBOL_PATTERNS.get(ext)

    def _extract_matches(
        self,
        content: str,
        pattern: str,
        lines: List[str],
    ) -> List[Dict[str, Any]]:
        """Extract all regex matches with line numbers."""
        matches = []
        regex = re.compile(pattern, re.MULTILINE)

        for i, line in enumerate(lines, start=1):
            for match in regex.finditer(line):
                # Get first non-None group
                name = None
                for group in match.groups():
                    if group:
                        name = group.strip()
                        break

                if name:
                    matches.append({
                        "name": name,
                        "line": i,
                        "column": match.start() + 1,
                        "text": line.strip(),
                    })

        return matches

    async def parse_symbols(
        self,
        file_path: str,
    ) -> Dict[str, Any]:
        """Extract functions and classes from a file using regex.

        Args:
            file_path: Path to file relative to repo root

        Returns:
            Dict with:
            - status: "success" or "error"
            - functions: List of function definitions
            - classes: List of class definitions
            - variables: List of top-level variables
            - language: Detected language
        """
        # Validate repo path exists
        if not ensure_repo_path_valid():
            return repo_path_error_response()

        repo_path = get_repo_path()
        resolved = resolve_path(file_path, repo_path)

        if resolved is None:
            return {
                "status": "error",
                "error": f"Path '{file_path}' is outside repository bounds",
            }

        if not resolved.exists():
            return {
                "status": "error",
                "error": f"File not found: {file_path}",
            }

        if not resolved.is_file():
            return {
                "status": "error",
                "error": f"Not a file: {file_path}",
            }

        patterns = self._get_patterns_for_file(file_path)
        if patterns is None:
            ext = Path(file_path).suffix
            return {
                "status": "error",
                "error": f"Unsupported file type: {ext}. Supported: {list(SYMBOL_PATTERNS.keys())}",
            }

        try:
            content = resolved.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()

            functions = []
            classes = []
            variables = []

            # Extract functions
            if "function" in patterns:
                for match in self._extract_matches(content, patterns["function"], lines):
                    functions.append({
                        "name": match["name"],
                        "line": match["line"],
                        "citation": f"[{file_path}:{match['line']}]",
                    })

            # Extract classes
            if "class" in patterns:
                for match in self._extract_matches(content, patterns["class"], lines):
                    classes.append({
                        "name": match["name"],
                        "line": match["line"],
                        "citation": f"[{file_path}:{match['line']}]",
                    })

            # Extract variables (limited to first 20)
            if "variable" in patterns:
                for match in self._extract_matches(content, patterns["variable"], lines)[:20]:
                    variables.append({
                        "name": match["name"],
                        "line": match["line"],
                        "citation": f"[{file_path}:{match['line']}]",
                    })

            # Detect language from extension
            ext = Path(file_path).suffix.lower()
            language_map = {
                ".py": "python",
                ".js": "javascript",
                ".ts": "typescript",
                ".go": "go",
            }
            language = language_map.get(ext, "unknown")

            return {
                "status": "success",
                "file": file_path,
                "language": language,
                "functions": functions,
                "classes": classes,
                "variables": variables,
                "total_symbols": len(functions) + len(classes) + len(variables),
            }

        except Exception as e:
            self._logger.error("parse_symbols_error", error=str(e), path=file_path)
            return {
                "status": "error",
                "error": str(e),
            }

    async def find_references(
        self,
        symbol: str,
        path: str = ".",
        file_types: Optional[List[str]] = None,
        max_results: int = 50,
    ) -> Dict[str, Any]:
        """Find references to a symbol across the codebase.

        Args:
            symbol: Symbol name to search for
            path: Directory to search in (relative to repo root)
            file_types: List of file extensions (e.g., [".py", ".js"])
            max_results: Maximum number of references to return

        Returns:
            Dict with:
            - status: "success" or "error"
            - references: List of references with file, line, and context
            - count: Number of references found
        """
        # Validate repo path exists
        if not ensure_repo_path_valid():
            return repo_path_error_response()

        repo_path = get_repo_path()
        resolved = resolve_path(path, repo_path)

        if resolved is None:
            return {
                "status": "error",
                "error": f"Path '{path}' is outside repository bounds",
            }

        if not resolved.exists():
            return {
                "status": "error",
                "error": f"Directory not found: {path}",
            }

        # Default to common code file types
        if file_types is None:
            file_types = [".py", ".js", ".ts", ".go", ".java", ".rb", ".rs"]

        try:
            excluded = get_excluded_dirs()
            references = []
            files_searched = 0

            # Create word boundary pattern for the symbol
            pattern = re.compile(r'\b' + re.escape(symbol) + r'\b')

            for root, dirs, filenames in os.walk(resolved):
                dirs[:] = [d for d in dirs if d not in excluded]

                for filename in filenames:
                    ext = Path(filename).suffix.lower()
                    if ext not in file_types:
                        continue

                    file_path = Path(root) / filename

                    try:
                        content = file_path.read_text(encoding="utf-8", errors="replace")
                        lines = content.splitlines()
                        files_searched += 1

                        for i, line in enumerate(lines, start=1):
                            if pattern.search(line):
                                rel_path = file_path.relative_to(repo_path)
                                references.append({
                                    "file": str(rel_path),
                                    "line": i,
                                    "content": line.strip(),
                                    "citation": f"[{rel_path}:{i}]",
                                })

                                if len(references) >= max_results:
                                    break

                    except Exception:
                        continue

                    if len(references) >= max_results:
                        break

                if len(references) >= max_results:
                    break

            truncated = len(references) >= max_results

            return {
                "status": "success",
                "symbol": symbol,
                "references": references,
                "count": len(references),
                "files_searched": files_searched,
                "truncated": truncated,
            }

        except Exception as e:
            self._logger.error("find_references_error", error=str(e), symbol=symbol)
            return {
                "status": "error",
                "error": str(e),
            }

    async def get_dependencies(
        self,
        file_path: str,
    ) -> Dict[str, Any]:
        """Extract imports/dependencies from a file.

        Args:
            file_path: Path to file relative to repo root

        Returns:
            Dict with:
            - status: "success" or "error"
            - imports: List of imported modules
            - count: Number of imports found
        """
        # Validate repo path exists
        if not ensure_repo_path_valid():
            return repo_path_error_response()

        repo_path = get_repo_path()
        resolved = resolve_path(file_path, repo_path)

        if resolved is None:
            return {
                "status": "error",
                "error": f"Path '{file_path}' is outside repository bounds",
            }

        if not resolved.exists():
            return {
                "status": "error",
                "error": f"File not found: {file_path}",
            }

        patterns = self._get_patterns_for_file(file_path)
        if patterns is None or "import" not in patterns:
            ext = Path(file_path).suffix
            return {
                "status": "error",
                "error": f"Import extraction not supported for: {ext}",
            }

        try:
            content = resolved.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()

            imports = []
            ext = Path(file_path).suffix.lower()
            import_pattern = patterns["import"]

            regex = re.compile(import_pattern, re.MULTILINE)

            for i, line in enumerate(lines, start=1):
                for match in regex.finditer(line):
                    # Handle different group patterns
                    groups = match.groups()
                    module_name = None

                    if ext == ".py":
                        # Python: from X import Y or import X
                        from_module = groups[0] if len(groups) > 0 else None
                        import_names = groups[1] if len(groups) > 1 else None

                        if from_module:
                            module_name = from_module
                        elif import_names:
                            # Split on comma and take first module
                            module_name = import_names.split(",")[0].strip().split()[0]
                    else:
                        # JS/Go: Take first non-None group
                        for group in groups:
                            if group:
                                module_name = group.strip()
                                break

                    if module_name:
                        imports.append({
                            "module": module_name,
                            "line": i,
                            "full_line": line.strip(),
                            "citation": f"[{file_path}:{i}]",
                        })

            return {
                "status": "success",
                "file": file_path,
                "imports": imports,
                "count": len(imports),
            }

        except Exception as e:
            self._logger.error("get_dependencies_error", error=str(e), path=file_path)
            return {
                "status": "error",
                "error": str(e),
            }

    async def get_dependents(
        self,
        module_name: str,
        path: str = ".",
        file_types: Optional[List[str]] = None,
        max_results: int = 50,
    ) -> Dict[str, Any]:
        """Find files that import/depend on a module.

        This is a reverse lookup - what files import the given module.

        Args:
            module_name: Name of the module to find dependents for
            path: Directory to search in (relative to repo root)
            file_types: List of file extensions to search
            max_results: Maximum number of dependents to return

        Returns:
            Dict with:
            - status: "success" or "error"
            - dependents: List of files that import this module
            - count: Number of dependents found
        """
        # Validate repo path exists
        if not ensure_repo_path_valid():
            return repo_path_error_response()

        repo_path = get_repo_path()
        resolved = resolve_path(path, repo_path)

        if resolved is None:
            return {
                "status": "error",
                "error": f"Path '{path}' is outside repository bounds",
            }

        if not resolved.exists():
            return {
                "status": "error",
                "error": f"Directory not found: {path}",
            }

        # Default to code files with import support
        if file_types is None:
            file_types = [".py", ".js", ".ts", ".go"]

        try:
            excluded = get_excluded_dirs()
            dependents = []
            files_searched = 0

            for root, dirs, filenames in os.walk(resolved):
                dirs[:] = [d for d in dirs if d not in excluded]

                for filename in filenames:
                    ext = Path(filename).suffix.lower()
                    if ext not in file_types:
                        continue

                    file_path = Path(root) / filename
                    patterns = SYMBOL_PATTERNS.get(ext)

                    if patterns is None or "import" not in patterns:
                        continue

                    try:
                        content = file_path.read_text(encoding="utf-8", errors="replace")
                        lines = content.splitlines()
                        files_searched += 1

                        import_pattern = patterns["import"]
                        regex = re.compile(import_pattern, re.MULTILINE)

                        for i, line in enumerate(lines, start=1):
                            for match in regex.finditer(line):
                                # Check if this import references our module
                                if module_name in line:
                                    rel_path = file_path.relative_to(repo_path)
                                    dependents.append({
                                        "file": str(rel_path),
                                        "line": i,
                                        "import_line": line.strip(),
                                        "citation": f"[{rel_path}:{i}]",
                                    })

                                    if len(dependents) >= max_results:
                                        break

                    except Exception:
                        continue

                    if len(dependents) >= max_results:
                        break

                if len(dependents) >= max_results:
                    break

            truncated = len(dependents) >= max_results

            return {
                "status": "success",
                "module": module_name,
                "dependents": dependents,
                "count": len(dependents),
                "files_searched": files_searched,
                "truncated": truncated,
            }

        except Exception as e:
            self._logger.error("get_dependents_error", error=str(e), module=module_name)
            return {
                "status": "error",
                "error": str(e),
            }


# Global instance
_code_parser: Optional[CodeParserTools] = None


def get_code_parser() -> CodeParserTools:
    """Get the code parser tools instance."""
    global _code_parser
    if _code_parser is None:
        _code_parser = CodeParserTools()
    return _code_parser


def register_code_parser_tools(
    registry=None,
    bounds: Optional[ContextBounds] = None,
) -> Dict[str, Any]:
    """Register code parser tools with the registry.

    Args:
        registry: Optional tool registry (uses global if None)
        bounds: Optional context bounds configuration

    Returns:
        Dict with registration info
    """
    global _code_parser
    target_registry = registry if registry is not None else tool_registry

    _code_parser = CodeParserTools(
        bounds=bounds,
    )
    parser = _code_parser

    # Register parse_symbols
    @target_registry.register(
        name="parse_symbols",
        description="Extract functions and classes from a file using regex. Supports Python, JS, TS, Go.",
        parameters={
            "file_path": "string (required) - Path to file relative to repo root",
        },
        risk_level=RiskLevel.READ_ONLY,
    )
    async def parse_symbols(file_path: str) -> Dict[str, Any]:
        return await parser.parse_symbols(file_path)

    # Register find_references
    @target_registry.register(
        name="find_references",
        description="Find all references to a symbol across the codebase. Returns [file:line] citations.",
        parameters={
            "symbol": "string (required) - Symbol name to search for",
            "path": "string (optional) - Directory to search in (default: '.')",
            "file_types": "list (optional) - File extensions to search (e.g., ['.py', '.js'])",
            "max_results": "integer (optional) - Maximum results (default: 50)",
        },
        risk_level=RiskLevel.READ_ONLY,
    )
    async def find_references(
        symbol: str,
        path: str = ".",
        file_types: Optional[List[str]] = None,
        max_results: int = 50,
    ) -> Dict[str, Any]:
        return await parser.find_references(symbol, path, file_types, max_results)

    # Register get_dependencies
    @target_registry.register(
        name="get_dependencies",
        description="Extract imports from a file. Returns list of imported modules with citations.",
        parameters={
            "file_path": "string (required) - Path to file relative to repo root",
        },
        risk_level=RiskLevel.READ_ONLY,
    )
    async def get_dependencies(
        file_path: str,
    ) -> Dict[str, Any]:
        return await parser.get_dependencies(file_path)

    # Register get_dependents
    @target_registry.register(
        name="get_dependents",
        description="Find files that import a module. Reverse dependency lookup.",
        parameters={
            "module_name": "string (required) - Module name to find dependents for",
            "path": "string (optional) - Directory to search in (default: '.')",
            "file_types": "list (optional) - File extensions to search",
            "max_results": "integer (optional) - Maximum results (default: 50)",
        },
        risk_level=RiskLevel.READ_ONLY,
    )
    async def get_dependents(
        module_name: str,
        path: str = ".",
        file_types: Optional[List[str]] = None,
        max_results: int = 50,
    ) -> Dict[str, Any]:
        return await parser.get_dependents(module_name, path, file_types, max_results)

    _logger = get_logger()
    _logger.info(
        "code_parser_tools_registered",
        tools=["parse_symbols", "find_references", "get_dependencies", "get_dependents"],
    )

    return {
        "tools": ["parse_symbols", "find_references", "get_dependencies", "get_dependents"],
        "count": 4,
        "instance": parser,
    }


__all__ = [
    "CodeParserTools",
    "register_code_parser_tools",
    "get_code_parser",
    "SYMBOL_PATTERNS",
]
