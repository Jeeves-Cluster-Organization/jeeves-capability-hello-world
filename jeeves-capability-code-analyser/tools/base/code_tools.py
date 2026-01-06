"""Code analysis tools - read-only file operations.

Phase 2/4 Constitutional Compliance:
- No auto-registration at import time
- Tools are plain functions registered by tools/registration.py
- Uses tool_catalog as single source of truth

Tools:
- read_file: Read file contents with optional line ranges
- glob_files: Find files matching a glob pattern
- grep_search: Search file contents with regex
- tree_structure: Show directory tree structure
"""

import asyncio
import fnmatch
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from jeeves_protocols import LoggerProtocol
from jeeves_capability_code_analyser.logging import get_logger
from .path_helpers import (
    get_repo_path,
    is_safe_path,
    resolve_path,
    count_tokens_approx,
    get_excluded_dirs,
    ensure_repo_path_valid,
    repo_path_error_response,
    get_language_config_from_registry,
)


# Local aliases for backward compatibility
_get_repo_path = get_repo_path
_is_safe_path = is_safe_path
_resolve_path = resolve_path
_count_tokens_approx = count_tokens_approx


async def read_file(
    path: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    max_tokens: int = 8000,
    include_line_numbers: bool = True,
) -> Dict[str, Any]:
    """Read file contents with optional line range.

    Args:
        path: Path to file relative to repo root
        start_line: Starting line number (1-indexed, optional)
        end_line: Ending line number (inclusive, optional)
        max_tokens: Maximum tokens before truncating (default: 8000)
        include_line_numbers: Include line numbers in output (default: True)

    Returns:
        Dict with:
        - status: "success" or "error"
        - content: File content with line numbers
        - path: Resolved file path
        - total_lines: Total lines in file
        - lines_returned: Number of lines returned
        - truncated: Whether content was truncated
    """
    # Validate repo path exists
    if not ensure_repo_path_valid():
        return repo_path_error_response()

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
        # Read file content
        content = resolved.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        total_lines = len(lines)

        # Apply line range if specified
        if start_line is not None or end_line is not None:
            start_idx = (start_line - 1) if start_line else 0
            end_idx = end_line if end_line else total_lines

            # Clamp to valid range
            start_idx = max(0, min(start_idx, total_lines))
            end_idx = max(0, min(end_idx, total_lines))

            lines = lines[start_idx:end_idx]
            line_offset = start_idx
        else:
            line_offset = 0

        # Format with optional line numbers
        formatted_lines = []
        max_token_count = max(1000, min(max_tokens, 8000))  # Clamp to safe range (18K-24K context budget)
        current_tokens = 0
        truncated = False

        for i, line in enumerate(lines, start=line_offset + 1):
            if include_line_numbers:
                formatted_line = f"{i:6d}\t{line}"
            else:
                formatted_line = line
            line_tokens = _count_tokens_approx(formatted_line)

            if current_tokens + line_tokens > max_token_count:
                truncated = True
                formatted_lines.append(f"[... truncated at {max_token_count} tokens ...]")
                break

            formatted_lines.append(formatted_line)
            current_tokens += line_tokens

        result_content = "\n".join(formatted_lines)

        # Get relative path for display
        rel_path = str(resolved.relative_to(Path(repo_path)))

        return {
            "status": "success",
            "content": result_content,
            "path": rel_path,
            "total_lines": total_lines,
            "lines_returned": len(formatted_lines) - (1 if truncated else 0),
            "start_line": line_offset + 1,
            "end_line": line_offset + len(formatted_lines) - (1 if truncated else 0),
            "truncated": truncated,
            "max_tokens_used": max_token_count,
        }

    except Exception as e:
        _logger = get_logger()
        _logger.error("read_file_error", path=path, error=str(e))
        return {
            "status": "error",
            "error": f"Failed to read file: {e}",
        }


async def glob_files(
    pattern: str,
    max_results: int = 100,
) -> Dict[str, Any]:
    """Find files matching a glob pattern.

    Args:
        pattern: Glob pattern (e.g., '**/*.py', 'src/**/*.ts')
        max_results: Maximum results to return (default: 100)

    Returns:
        Dict with:
        - status: "success" or "error"
        - files: List of matching file paths
        - count: Number of matches
        - truncated: Whether results were truncated
    """
    # Validate repo path exists
    if not ensure_repo_path_valid():
        return repo_path_error_response()

    repo_path = _get_repo_path()
    repo = Path(repo_path)

    try:
        # Use pathlib glob
        matches = list(repo.glob(pattern))

        # Filter to files only and exclude directories based on language config
        config = get_language_config_from_registry()
        excluded_dirs = config.exclude_dirs

        files = []
        for match in matches:
            if not match.is_file():
                continue

            # Check if any part of path is in excluded dirs
            parts = match.relative_to(repo).parts
            if any(part in excluded_dirs for part in parts):
                continue

            files.append(str(match.relative_to(repo)))

            if len(files) >= max_results:
                break

        truncated = len(matches) > max_results

        return {
            "status": "success",
            "files": files,
            "count": len(files),
            "truncated": truncated,
            "pattern": pattern,
        }

    except Exception as e:
        _logger = get_logger()
        _logger.error("glob_files_error", pattern=pattern, error=str(e))
        return {
            "status": "error",
            "error": f"Failed to glob files: {e}",
        }


async def grep_search(
    pattern: str,
    path: Optional[str] = None,
    file_types: Optional[str] = None,
    max_results: int = 50,
    context_lines: int = 2,
) -> Dict[str, Any]:
    """Search file contents with regex pattern.

    Args:
        pattern: Regex pattern to search for
        path: Path to search in (defaults to repo root)
        file_types: Comma-separated file extensions (e.g., 'py,ts,js')
        max_results: Maximum results to return (default: 50)
        context_lines: Lines of context around match (default: 2)

    Returns:
        Dict with:
        - status: "success" or "error"
        - matches: List of match objects with file, line, content
        - count: Number of matches
        - truncated: Whether results were truncated
    """
    # Validate repo path exists
    if not ensure_repo_path_valid():
        repo_path = _get_repo_path()
        return {
            "status": "error",
            "error": f"REPO_PATH '{repo_path}' does not exist or is not accessible. "
                     f"Set REPO_PATH environment variable to a valid directory.",
        }

    repo_path = _get_repo_path()
    search_path = _resolve_path(path, repo_path) if path else Path(repo_path)

    if search_path is None:
        return {
            "status": "error",
            "error": f"Path '{path}' is outside repository bounds",
        }

    try:
        # Compile regex
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            return {
                "status": "error",
                "error": f"Invalid regex pattern: {e}",
            }

        # Build file type filter
        extensions = None
        if file_types:
            extensions = set(f".{ext.strip().lstrip('.')}" for ext in file_types.split(","))

        # Search files
        matches = []
        files_searched = 0
        config = get_language_config_from_registry()
        excluded_dirs = config.exclude_dirs

        def should_search_file(filepath: Path) -> bool:
            """Check if file should be searched."""
            if not filepath.is_file():
                return False
            if extensions and filepath.suffix not in extensions:
                return False
            # Skip binary files
            if filepath.suffix in {".pyc", ".pyo", ".so", ".dll", ".exe", ".bin"}:
                return False
            return True

        def search_in_file(filepath: Path) -> List[Dict]:
            """Search for pattern in a single file."""
            try:
                content = filepath.read_text(encoding="utf-8", errors="replace")
                lines = content.splitlines()
                file_matches = []

                for i, line in enumerate(lines):
                    if regex.search(line):
                        # Get context
                        start = max(0, i - context_lines)
                        end = min(len(lines), i + context_lines + 1)

                        context_block = []
                        for j in range(start, end):
                            prefix = ">" if j == i else " "
                            context_block.append(f"{j+1:6d}{prefix} {lines[j]}")

                        file_matches.append({
                            "file": str(filepath.relative_to(repo_path)),
                            "line": i + 1,
                            "match": line.strip(),
                            "context": "\n".join(context_block),
                        })

                return file_matches
            except Exception:
                return []

        # Walk directory tree
        if search_path.is_file():
            if should_search_file(search_path):
                matches.extend(search_in_file(search_path))
        else:
            for root, dirs, files in os.walk(search_path):
                # Prune excluded directories
                dirs[:] = [d for d in dirs if d not in excluded_dirs]

                for filename in files:
                    filepath = Path(root) / filename

                    if should_search_file(filepath):
                        files_searched += 1
                        file_matches = search_in_file(filepath)
                        matches.extend(file_matches)

                        if len(matches) >= max_results:
                            break

                if len(matches) >= max_results:
                    break

        truncated = len(matches) >= max_results
        matches = matches[:max_results]

        return {
            "status": "success",
            "matches": matches,
            "count": len(matches),
            "files_searched": files_searched,
            "truncated": truncated,
            "pattern": pattern,
        }

    except Exception as e:
        _logger = get_logger()
        _logger.error("grep_search_error", pattern=pattern, error=str(e))
        return {
            "status": "error",
            "error": f"Failed to search: {e}",
        }


async def tree_structure(
    path: Optional[str] = None,
    depth: int = 3,
    show_hidden: bool = False,
    max_entries: int = 1000,
    file_types: Optional[str] = None,
) -> Dict[str, Any]:
    """Show directory tree structure.

    Args:
        path: Path to show tree for (defaults to repo root)
        depth: Maximum depth to traverse (default: 3)
        show_hidden: Include hidden files/folders (default: False)
        max_entries: Maximum entries before truncating (default: 1000)
        file_types: Comma-separated file extensions to filter (optional)

    Returns:
        Dict with:
        - status: "success" or "error"
        - tree: Formatted tree string
        - file_count: Number of files
        - dir_count: Number of directories
    """
    # Validate repo path exists
    if not ensure_repo_path_valid():
        return repo_path_error_response()

    repo_path = _get_repo_path()
    tree_path = _resolve_path(path, repo_path) if path else Path(repo_path)

    if tree_path is None:
        return {
            "status": "error",
            "error": f"Path '{path}' is outside repository bounds",
        }

    if not tree_path.exists():
        return {
            "status": "error",
            "error": f"Path does not exist: {path or ''}",
        }

    try:
        config = get_language_config_from_registry()
        excluded_dirs = config.exclude_dirs

        # Parse file type filter if provided
        type_filter = None
        if file_types:
            type_filter = set(f".{ext.strip().lstrip('.')}" for ext in file_types.split(","))

        lines = []
        file_count = 0
        dir_count = 0
        max_lines = max(100, min(max_entries, 2000))  # Clamp to safe range (18K-24K context budget)

        def format_tree(current_path: Path, prefix: str, current_depth: int) -> None:
            nonlocal file_count, dir_count

            if current_depth > depth or len(lines) >= max_lines:
                return

            try:
                entries = sorted(current_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            except PermissionError:
                return

            # Filter entries
            filtered = []
            for entry in entries:
                if not show_hidden and entry.name.startswith("."):
                    continue
                if entry.is_dir() and entry.name in excluded_dirs:
                    continue
                # Apply file type filter (directories always pass to allow traversal)
                if type_filter and entry.is_file():
                    if entry.suffix.lower() not in type_filter:
                        continue
                filtered.append(entry)

            for i, entry in enumerate(filtered):
                if len(lines) >= max_lines:
                    lines.append(f"{prefix}... [truncated at {max_lines} entries]")
                    return

                is_last = i == len(filtered) - 1
                connector = "└── " if is_last else "├── "

                if entry.is_dir():
                    lines.append(f"{prefix}{connector}{entry.name}/")
                    dir_count += 1

                    if current_depth < depth:
                        extension = "    " if is_last else "│   "
                        format_tree(entry, prefix + extension, current_depth + 1)
                else:
                    lines.append(f"{prefix}{connector}{entry.name}")
                    file_count += 1

        # Start with root
        rel_path = str(tree_path.relative_to(repo_path)) if tree_path != Path(repo_path) else "."
        lines.append(f"{rel_path}/")
        format_tree(tree_path, "", 1)

        return {
            "status": "success",
            "tree": "\n".join(lines),
            "file_count": file_count,
            "dir_count": dir_count,
            "path": rel_path,
            "depth": depth,
        }

    except Exception as e:
        _logger = get_logger()
        _logger.error("tree_structure_error", path=path, error=str(e))
        return {
            "status": "error",
            "error": f"Failed to generate tree: {e}",
        }
