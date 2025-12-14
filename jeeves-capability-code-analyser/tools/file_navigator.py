"""File navigation tools for code analysis.

These tools provide file system navigation capabilities for the code analysis agent.
All tools are READ_ONLY risk level since they don't modify any files.

Tools:
- list_files: List files in a directory with filtering
- read_file_with_lines: Read file contents with line numbers
- search_files: Search for patterns across files
- get_project_tree: Get directory structure
"""

import fnmatch
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from jeeves_mission_system.adapters import get_logger
from jeeves_mission_system.contracts import LoggerProtocol
from tools.registry import RiskLevel, tool_registry
from tools.base.path_helpers import (
    get_repo_path,
    resolve_path,
    count_tokens_approx,
    get_excluded_dirs,
    ensure_repo_path_valid,
    repo_path_error_response,
)
# Domain-specific bounds from capability config (per Constitution R6)
from jeeves_capability_code_analyser.config import CodeAnalysisBounds, get_code_analysis_bounds


class FileNavigatorTools:
    """File navigation tools for code analysis.

    Provides capabilities to:
    - List files with pattern filtering
    - Read file contents with line numbers
    - Search across files
    - View project tree structure
    """

    def __init__(self, bounds: Optional[CodeAnalysisBounds] = None, logger: Optional[LoggerProtocol] = None):
        """Initialize file navigator tools.

        Args:
            bounds: Optional code analysis bounds
            logger: Optional logger instance
        """
        self.bounds = bounds or get_code_analysis_bounds()
        self._logger = logger or get_logger()

    async def list_files(
        self,
        path: Optional[str] = None,
        pattern: Optional[str] = None,
        recursive: bool = True,
        max_results: int = 100,
    ) -> Dict[str, Any]:
        """List files in a directory with optional filtering.

        Args:
            path: Directory path relative to repo root. None, empty, or "." for root.
            pattern: Glob pattern to filter files (e.g., "*.py", "*.js")
            recursive: Whether to search recursively
            max_results: Maximum number of files to return

        Returns:
            Dict with:
            - status: "success" or "error"
            - files: List of file paths
            - count: Number of files found
            - truncated: Whether results were truncated

        Constitutional compliance (P3 - Bounded Efficiency):
            Gracefully handles None/empty path by using repo root.
        """
        # Defense-in-depth: handle None explicitly
        if path is None or path == "":
            path = "."

        # Validate repo path exists
        if not ensure_repo_path_valid():
            return repo_path_error_response()

        repo_path = get_repo_path()
        resolved = resolve_path(path, repo_path)

        if resolved is None:
            # Provide helpful hint for common mistakes
            hint = ""
            if path == "/" or path.startswith("/"):
                hint = " Use '.' or '' for repository root, or a relative path like 'src/'"
            return {
                "status": "error",
                "error": f"Path '{path}' is outside repository bounds.{hint}",
            }

        if not resolved.exists():
            return {
                "status": "error",
                "error": f"Directory not found: {path}",
            }

        if not resolved.is_dir():
            return {
                "status": "error",
                "error": f"Not a directory: {path}",
            }

        try:
            excluded = get_excluded_dirs()
            files = []

            if recursive:
                for root, dirs, filenames in os.walk(resolved):
                    # Filter out excluded directories
                    dirs[:] = [d for d in dirs if d not in excluded]

                    for filename in filenames:
                        if pattern is None or fnmatch.fnmatch(filename, pattern):
                            file_path = Path(root) / filename
                            rel_path = file_path.relative_to(repo_path)
                            files.append(str(rel_path))

                            if len(files) >= max_results:
                                break

                    if len(files) >= max_results:
                        break
            else:
                for item in resolved.iterdir():
                    if item.is_file():
                        if pattern is None or fnmatch.fnmatch(item.name, pattern):
                            rel_path = item.relative_to(repo_path)
                            files.append(str(rel_path))

                            if len(files) >= max_results:
                                break

            truncated = len(files) >= max_results

            return {
                "status": "success",
                "files": sorted(files),
                "count": len(files),
                "truncated": truncated,
                "path": path,
                "pattern": pattern,
            }

        except Exception as e:
            self._logger.error("list_files_error", error=str(e), path=path)
            return {
                "status": "error",
                "error": str(e),
            }

    async def read_file_with_lines(
        self,
        file_path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Read file contents with line numbers.

        Args:
            file_path: Path to file relative to repo root
            start_line: Starting line number (1-indexed)
            end_line: Ending line number (inclusive)

        Returns:
            Dict with:
            - status: "success" or "error"
            - content: File content with line numbers
            - path: Resolved file path
            - total_lines: Total lines in file
            - lines_returned: Number of lines returned
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

        try:
            content = resolved.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()
            total_lines = len(lines)

            # Apply line range
            if start_line is not None:
                start_idx = max(0, start_line - 1)
            else:
                start_idx = 0

            if end_line is not None:
                end_idx = min(total_lines, end_line)
            else:
                end_idx = total_lines

            selected_lines = lines[start_idx:end_idx]

            # Format with line numbers
            formatted_lines = []
            for i, line in enumerate(selected_lines, start=start_idx + 1):
                formatted_lines.append(f"{i:>6}: {line}")

            formatted_content = "\n".join(formatted_lines)

            # Check token limit
            tokens = count_tokens_approx(formatted_content)
            truncated = tokens > self.bounds.max_file_slice_tokens

            if truncated:
                # Truncate to fit bounds
                max_lines = int(len(selected_lines) * (self.bounds.max_file_slice_tokens / tokens))
                selected_lines = selected_lines[:max_lines]
                formatted_lines = []
                for i, line in enumerate(selected_lines, start=start_idx + 1):
                    formatted_lines.append(f"{i:>6}: {line}")
                formatted_content = "\n".join(formatted_lines) + "\n[truncated]"

            return {
                "status": "success",
                "content": formatted_content,
                "path": file_path,
                "total_lines": total_lines,
                "lines_returned": len(selected_lines),
                "start_line": start_idx + 1,
                "end_line": start_idx + len(selected_lines),
                "truncated": truncated,
            }

        except Exception as e:
            self._logger.error("read_file_error", error=str(e), path=file_path)
            return {
                "status": "error",
                "error": str(e),
            }

    async def search_files(
        self,
        pattern: str,
        path: str = ".",
        file_types: Optional[List[str]] = None,
        max_results: int = 50,
        context_lines: int = 2,
    ) -> Dict[str, Any]:
        """Search for a pattern across files.

        Args:
            pattern: Regex pattern to search for
            path: Directory to search in (relative to repo root)
            file_types: List of file extensions to search (e.g., [".py", ".js"])
            max_results: Maximum number of matches to return
            context_lines: Number of context lines around matches

        Returns:
            Dict with:
            - status: "success" or "error"
            - matches: List of match results with file, line, and context
            - count: Number of matches found
            - truncated: Whether results were truncated
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

        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            return {
                "status": "error",
                "error": f"Invalid regex pattern: {e}",
            }

        try:
            excluded = get_excluded_dirs()
            matches = []
            files_searched = 0

            for root, dirs, filenames in os.walk(resolved):
                dirs[:] = [d for d in dirs if d not in excluded]

                for filename in filenames:
                    # Filter by file type
                    if file_types:
                        ext = Path(filename).suffix
                        if ext not in file_types:
                            continue

                    file_path = Path(root) / filename

                    try:
                        content = file_path.read_text(encoding="utf-8", errors="replace")
                        lines = content.splitlines()
                        files_searched += 1

                        for i, line in enumerate(lines):
                            if regex.search(line):
                                rel_path = file_path.relative_to(repo_path)

                                # Get context
                                start_ctx = max(0, i - context_lines)
                                end_ctx = min(len(lines), i + context_lines + 1)
                                context = lines[start_ctx:end_ctx]

                                matches.append({
                                    "file": str(rel_path),
                                    "line": i + 1,
                                    "content": line.strip(),
                                    "context": context,
                                    "citation": f"[{rel_path}:{i + 1}]",
                                })

                                if len(matches) >= max_results:
                                    break

                    except Exception:
                        # Skip files that can't be read
                        continue

                    if len(matches) >= max_results:
                        break

                if len(matches) >= max_results:
                    break

            truncated = len(matches) >= max_results

            return {
                "status": "success",
                "matches": matches,
                "count": len(matches),
                "files_searched": files_searched,
                "truncated": truncated,
                "pattern": pattern,
            }

        except Exception as e:
            self._logger.error("search_files_error", error=str(e), pattern=pattern)
            return {
                "status": "error",
                "error": str(e),
            }

    async def get_project_tree(
        self,
        path: str = ".",
        depth: int = 3,
        show_files: bool = True,
        pattern: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get directory tree structure.

        Args:
            path: Root directory (relative to repo root)
            depth: Maximum depth to traverse
            show_files: Whether to include files (not just directories)
            pattern: Glob pattern to filter files

        Returns:
            Dict with:
            - status: "success" or "error"
            - tree: Formatted tree structure
            - dirs_count: Number of directories
            - files_count: Number of files
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

        try:
            excluded = get_excluded_dirs()
            tree_lines = []
            dirs_count = 0
            files_count = 0

            def build_tree(current_path: Path, prefix: str, current_depth: int):
                nonlocal dirs_count, files_count

                if current_depth > depth:
                    return

                try:
                    items = sorted(current_path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
                except PermissionError:
                    return

                # Filter excluded directories
                items = [i for i in items if i.name not in excluded]

                for i, item in enumerate(items):
                    is_last = i == len(items) - 1
                    connector = "└── " if is_last else "├── "

                    if item.is_dir():
                        dirs_count += 1
                        tree_lines.append(f"{prefix}{connector}{item.name}/")

                        extension = "    " if is_last else "│   "
                        build_tree(item, prefix + extension, current_depth + 1)
                    elif show_files:
                        if pattern is None or fnmatch.fnmatch(item.name, pattern):
                            files_count += 1
                            tree_lines.append(f"{prefix}{connector}{item.name}")

            # Start with root
            rel_path = resolved.relative_to(repo_path)
            tree_lines.append(f"{rel_path}/")
            build_tree(resolved, "", 1)

            tree_content = "\n".join(tree_lines)

            # Check token limit
            tokens = count_tokens_approx(tree_content)
            truncated = tokens > self.bounds.max_tree_tokens

            if truncated:
                # Truncate tree
                max_lines = int(len(tree_lines) * (self.bounds.max_tree_tokens / tokens))
                tree_content = "\n".join(tree_lines[:max_lines]) + "\n[truncated]"

            return {
                "status": "success",
                "tree": tree_content,
                "dirs_count": dirs_count,
                "files_count": files_count,
                "path": path,
                "depth": depth,
                "truncated": truncated,
            }

        except Exception as e:
            self._logger.error("get_project_tree_error", error=str(e), path=path)
            return {
                "status": "error",
                "error": str(e),
            }


# Global instance for tool registration
_file_navigator: Optional[FileNavigatorTools] = None


def get_file_navigator() -> FileNavigatorTools:
    """Get or create the file navigator tools instance."""
    global _file_navigator
    if _file_navigator is None:
        _file_navigator = FileNavigatorTools()
    return _file_navigator


def register_file_navigator_tools(
    registry=None,
    bounds: Optional[CodeAnalysisBounds] = None,
) -> Dict[str, Any]:
    """Register file navigator tools with the registry.

    Args:
        registry: Optional tool registry (uses global if None)
        bounds: Optional context bounds configuration

    Returns:
        Dict with registration info
    """
    _logger = get_logger()
    global _file_navigator
    target_registry = registry if registry is not None else tool_registry

    _file_navigator = FileNavigatorTools(bounds=bounds)
    nav = _file_navigator

    # Register list_files
    @target_registry.register(
        name="list_files",
        description="List files in a directory with optional pattern filtering. Returns file paths relative to repo root.",
        parameters={
            "path": "string (optional) - Directory path relative to repo root (default: '.')",
            "pattern": "string (optional) - Glob pattern to filter files (e.g., '*.py')",
            "recursive": "boolean (optional) - Whether to search recursively (default: true)",
            "max_results": "integer (optional) - Maximum number of files to return (default: 100)",
        },
        risk_level=RiskLevel.READ_ONLY,
    )
    async def list_files(
        path: Optional[str] = None,
        pattern: Optional[str] = None,
        recursive: bool = True,
        max_results: int = 100,
    ) -> Dict[str, Any]:
        # Defense-in-depth: handle None/empty path
        effective_path = path if path else "."
        return await nav.list_files(effective_path, pattern, recursive, max_results)

    # Register search_files
    @target_registry.register(
        name="search_files",
        description="Search for a regex pattern across files. Returns matches with [file:line] citations.",
        parameters={
            "pattern": "string (required) - Regex pattern to search for",
            "path": "string (optional) - Directory to search in (default: '.')",
            "file_types": "list (optional) - List of file extensions (e.g., ['.py', '.js'])",
            "max_results": "integer (optional) - Maximum number of matches (default: 50)",
        },
        risk_level=RiskLevel.READ_ONLY,
    )
    async def search_files(
        pattern: str,
        path: Optional[str] = None,
        file_types: Optional[List[str]] = None,
        max_results: int = 50,
    ) -> Dict[str, Any]:
        # Defense-in-depth: handle None/empty path
        effective_path = path if path else "."
        return await nav.search_files(pattern, effective_path, file_types, max_results)

    # Register get_project_tree
    @target_registry.register(
        name="get_project_tree",
        description="Get directory tree structure. Shows files and folders in a tree format.",
        parameters={
            "path": "string (optional) - Root directory (default: '.')",
            "depth": "integer (optional) - Maximum depth to traverse (default: 3)",
            "show_files": "boolean (optional) - Whether to include files (default: true)",
            "pattern": "string (optional) - Glob pattern to filter files",
        },
        risk_level=RiskLevel.READ_ONLY,
    )
    async def get_project_tree(
        path: Optional[str] = None,
        depth: int = 3,
        show_files: bool = True,
        pattern: Optional[str] = None,
    ) -> Dict[str, Any]:
        # Defense-in-depth: handle None/empty path
        effective_path = path if path else "."
        return await nav.get_project_tree(effective_path, depth, show_files, pattern)

    _logger.info(
        "file_navigator_tools_registered",
        tools=["list_files", "search_files", "get_project_tree"],
    )

    return {
        "tools": ["list_files", "search_files", "get_project_tree"],
        "count": 3,
        "instance": nav,
    }


__all__ = [
    "FileNavigatorTools",
    "register_file_navigator_tools",
    "get_file_navigator",
]
