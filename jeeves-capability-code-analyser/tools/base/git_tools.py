"""Git-aware tools for code analysis.

Phase 2/4 Constitutional Compliance - No auto-registration at import time

These tools provide git integration for understanding code history and changes.
All tools are READ_ONLY as they only read git information.

Tools:
- git_log: Get commit history for a file or directory
- git_blame: Get line attribution for a file
- git_diff: Show changes between commits or working tree
"""

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from jeeves_protocols import LoggerProtocol
import structlog
get_logger = structlog.get_logger
from jeeves_protocols import RiskLevel
from tools.base.path_helpers import (
    get_repo_path,
    resolve_path,
    ensure_repo_path_valid,
    repo_path_error_response,
)


def _run_git_command(args: List[str], cwd: str, timeout: int = 30) -> Dict[str, Any]:
    """Run a git command and return result.

    Args:
        args: Git command arguments (without 'git' prefix)
        cwd: Working directory
        timeout: Command timeout in seconds

    Returns:
        Dict with status, output, and error
    """
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.returncode != 0:
            return {
                "status": "error",
                "error": result.stderr.strip() or f"Git command failed with code {result.returncode}",
            }

        return {
            "status": "success",
            "output": result.stdout,
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "error": f"Git command timed out after {timeout}s",
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "error": "Git is not installed or not in PATH",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Git command failed: {e}",
        }


async def git_log(
    path: Optional[str] = None,
    n: int = 10,
    oneline: bool = False,
    since: Optional[str] = None,
) -> Dict[str, Any]:
    """Get commit history for a file or directory.

    Args:
        path: Path to file/directory (defaults to repo root)
        n: Number of commits to show (default: 10)
        oneline: Use one-line format (default: False)
        since: Show commits after date (e.g., '2024-01-01', '1 week ago')

    Returns:
        Dict with:
        - status: "success" or "error"
        - commits: List of commit info (hash, author, date, message)
        - log: Raw git log output
    """
    # Validate repo path exists
    if not _ensure_repo_path_valid():
        return _repo_path_error_response()

    repo_path = _get_repo_path()

    # Validate path if provided
    if path:
        resolved = _resolve_path(path, repo_path)
        if resolved is None:
            return {
                "status": "error",
                "error": f"Path '{path}' is outside repository bounds",
            }

    # Build git log command
    args = ["log", f"-{n}"]

    if oneline:
        args.append("--oneline")
    else:
        args.append("--format=%H%n%an%n%ae%n%ad%n%s%n---COMMIT---")

    if since:
        args.append(f"--since={since}")

    if path:
        args.append("--")
        args.append(path)

    result = _run_git_command(args, repo_path)

    if result["status"] != "success":
        return result

    output = result["output"]

    # Parse commits if not oneline format
    commits = []
    if not oneline and output.strip():
        commit_blocks = output.strip().split("---COMMIT---")
        for block in commit_blocks:
            block = block.strip()
            if not block:
                continue

            lines = block.split("\n")
            if len(lines) >= 5:
                commits.append({
                    "hash": lines[0],
                    "author_name": lines[1],
                    "author_email": lines[2],
                    "date": lines[3],
                    "message": lines[4],
                })
    elif oneline:
        for line in output.strip().split("\n"):
            if line:
                parts = line.split(" ", 1)
                if len(parts) == 2:
                    commits.append({
                        "hash": parts[0],
                        "message": parts[1],
                    })

    return {
        "status": "success",
        "commits": commits,
        "count": len(commits),
        "log": output if oneline else None,
        "path": path,
    }


async def git_blame(
    path: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
) -> Dict[str, Any]:
    """Get line attribution for a file.

    Args:
        path: Path to file relative to repo root
        start_line: Starting line number (optional)
        end_line: Ending line number (optional)

    Returns:
        Dict with:
        - status: "success" or "error"
        - blame: List of blame info per line
        - output: Raw git blame output
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

    # Build git blame command
    args = ["blame", "--porcelain"]

    if start_line and end_line:
        args.append(f"-L{start_line},{end_line}")
    elif start_line:
        args.append(f"-L{start_line},")
    elif end_line:
        args.append(f"-L,{end_line}")

    args.append(path)

    result = _run_git_command(args, repo_path)

    if result["status"] != "success":
        return result

    output = result["output"]

    # Parse porcelain blame output
    blame_entries = []
    current_entry = {}
    line_content = None

    for line in output.split("\n"):
        if not line:
            continue

        if line.startswith("\t"):
            # This is the actual line content
            line_content = line[1:]
            if current_entry:
                current_entry["content"] = line_content
                blame_entries.append(current_entry)
                current_entry = {}
        elif " " in line:
            parts = line.split(" ", 1)
            key = parts[0]
            value = parts[1] if len(parts) > 1 else ""

            if len(key) == 40:  # SHA
                if current_entry:
                    blame_entries.append(current_entry)
                current_entry = {"commit": key, "line": int(value.split()[1]) if value else 0}
            elif key == "author":
                current_entry["author"] = value
            elif key == "author-time":
                current_entry["timestamp"] = int(value)
            elif key == "summary":
                current_entry["summary"] = value

    if current_entry:
        blame_entries.append(current_entry)

    # Simplify for output
    simplified = []
    for entry in blame_entries:
        simplified.append({
            "line": entry.get("line", 0),
            "commit": entry.get("commit", "")[:8],
            "author": entry.get("author", ""),
            "summary": entry.get("summary", ""),
            "content": entry.get("content", ""),
        })

    return {
        "status": "success",
        "blame": simplified,
        "count": len(simplified),
        "path": path,
    }


async def git_diff(
    path: Optional[str] = None,
    commit1: Optional[str] = None,
    commit2: Optional[str] = None,
    stat: bool = False,
) -> Dict[str, Any]:
    """Show changes between commits or working tree.

    Args:
        path: Path to file/directory to diff (optional)
        commit1: First commit (defaults to HEAD)
        commit2: Second commit (defaults to working tree)
        stat: Show diffstat instead of full diff (default: False)

    Returns:
        Dict with:
        - status: "success" or "error"
        - diff: Diff output
        - files_changed: Number of files changed (if stat=True)
    """
    # Validate repo path exists
    if not _ensure_repo_path_valid():
        return _repo_path_error_response()

    repo_path = _get_repo_path()

    # Validate path if provided
    if path:
        resolved = _resolve_path(path, repo_path)
        if resolved is None:
            return {
                "status": "error",
                "error": f"Path '{path}' is outside repository bounds",
            }

    # Build git diff command
    args = ["diff"]

    if stat:
        args.append("--stat")

    if commit1:
        args.append(commit1)
        if commit2:
            args.append(commit2)

    if path:
        args.append("--")
        args.append(path)

    result = _run_git_command(args, repo_path)

    if result["status"] != "success":
        return result

    output = result["output"]

    # Parse stat output if requested
    files_changed = None
    insertions = None
    deletions = None

    if stat and output:
        # Last line has summary
        lines = output.strip().split("\n")
        if lines:
            summary = lines[-1]
            import re
            match = re.search(r'(\d+) files? changed', summary)
            if match:
                files_changed = int(match.group(1))
            match = re.search(r'(\d+) insertions?', summary)
            if match:
                insertions = int(match.group(1))
            match = re.search(r'(\d+) deletions?', summary)
            if match:
                deletions = int(match.group(1))

    # Truncate diff if too long
    max_lines = 500  # Increased to reduce trimmed outputs
    lines = output.split("\n")
    truncated = len(lines) > max_lines
    if truncated:
        output = "\n".join(lines[:max_lines]) + f"\n\n... [truncated, {len(lines) - max_lines} more lines]"

    return {
        "status": "success",
        "diff": output,
        "files_changed": files_changed,
        "insertions": insertions,
        "deletions": deletions,
        "truncated": truncated,
        "path": path,
        "commit1": commit1,
        "commit2": commit2,
    }


async def git_status() -> Dict[str, Any]:
    """Show working tree status.

    Returns:
        Dict with:
        - status: "success" or "error"
        - modified: List of modified files
        - staged: List of staged files
        - untracked: List of untracked files
        - branch: Current branch name
    """
    # Validate repo path exists
    if not _ensure_repo_path_valid():
        return _repo_path_error_response()

    repo_path = _get_repo_path()

    # Get branch
    branch_result = _run_git_command(["branch", "--show-current"], repo_path)
    branch = branch_result.get("output", "").strip() if branch_result["status"] == "success" else "unknown"

    # Get status
    result = _run_git_command(["status", "--porcelain=v2", "--branch"], repo_path)

    if result["status"] != "success":
        return result

    output = result["output"]

    modified = []
    staged = []
    untracked = []

    for line in output.split("\n"):
        if not line:
            continue

        if line.startswith("# "):
            # Branch info line
            continue

        if line.startswith("1 "):
            # Changed entry
            parts = line.split(" ", 8)
            if len(parts) >= 9:
                xy = parts[1]
                filepath = parts[8]

                if xy[0] != ".":
                    staged.append(filepath)
                if xy[1] != ".":
                    modified.append(filepath)

        elif line.startswith("2 "):
            # Renamed entry
            parts = line.split("\t")
            if len(parts) >= 2:
                staged.append(f"{parts[0].split()[-1]} -> {parts[1]}")

        elif line.startswith("? "):
            # Untracked
            untracked.append(line[2:])

    return {
        "status": "success",
        "branch": branch,
        "modified": modified,
        "staged": staged,
        "untracked": untracked,
        "clean": len(modified) == 0 and len(staged) == 0 and len(untracked) == 0,
    }


__all__ = ["git_log", "git_blame", "git_diff", "git_status"]
