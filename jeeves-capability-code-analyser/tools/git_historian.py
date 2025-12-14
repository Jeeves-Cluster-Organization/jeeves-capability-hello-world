"""Git Historian - Explain code evolution through git attempt_history.

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
from jeeves_protocols import RiskLevel


async def _get_blame(path: str, start_line: Optional[int], end_line: Optional[int]) -> Dict[str, Any]:
    """Get git blame information for a file/range."""
    _logger = get_logger()
    if not tool_catalog.has_tool_id(ToolId.GIT_BLAME):
        return {"status": "tool_unavailable", "blame": []}

    git_blame = tool_catalog.get_function(ToolId.GIT_BLAME)
    try:
        result = await git_blame(path=path, start_line=start_line, end_line=end_line)
        if result.get("status") == "success":
            return {"status": "found", "blame": result.get("blame", [])}
        return {"status": "no_data", "blame": []}
    except Exception as e:
        _logger.warning("git_historian_blame_error", error=str(e))
        return {"status": "error", "blame": [], "error": str(e)}


async def _get_log(path: str, n: int, since: Optional[str]) -> Dict[str, Any]:
    """Get commit attempt_history for a file."""
    _logger = get_logger()
    if not tool_catalog.has_tool_id(ToolId.GIT_LOG):
        return {"status": "tool_unavailable", "commits": []}

    git_log = tool_catalog.get_function(ToolId.GIT_LOG)
    try:
        result = await git_log(path=path, n=n, since=since)
        if result.get("status") == "success":
            return {"status": "found", "commits": result.get("commits", [])}
        return {"status": "no_data", "commits": []}
    except Exception as e:
        _logger.warning("git_historian_log_error", error=str(e))
        return {"status": "error", "commits": [], "error": str(e)}


async def _get_diff(path: str, commit1: str, commit2: Optional[str]) -> Dict[str, Any]:
    """Get diff for a specific commit on a file."""
    _logger = get_logger()
    if not tool_catalog.has_tool_id(ToolId.GIT_DIFF):
        return {"status": "tool_unavailable", "diff": ""}

    git_diff = tool_catalog.get_function(ToolId.GIT_DIFF)
    try:
        result = await git_diff(path=path, commit1=commit1, commit2=commit2, stat=False)
        if result.get("status") == "success":
            return {
                "status": "found",
                "diff": result.get("diff", ""),
                "insertions": result.get("insertions"),
                "deletions": result.get("deletions"),
            }
        return {"status": "no_data", "diff": ""}
    except Exception as e:
        _logger.warning("git_historian_diff_error", error=str(e))
        return {"status": "error", "diff": "", "error": str(e)}


def _compute_ownership(blame_entries: List[Dict]) -> Dict[str, float]:
    """Compute code ownership percentages from blame data."""
    author_lines: Dict[str, int] = defaultdict(int)
    total_lines = len(blame_entries)

    if total_lines == 0:
        return {}

    for entry in blame_entries:
        author = entry.get("author", "unknown")
        author_lines[author] += 1

    return {
        author: round((count / total_lines) * 100, 1)
        for author, count in sorted(author_lines.items(), key=lambda x: -x[1])
    }


async def explain_code_history(
    path: str,
    context_bounds: ContextBounds,
    line_range: Optional[str] = None,
    depth: str = "recent",
) -> Dict[str, Any]:
    """Explain why code looks the way it does via git attempt_history.

    Pipeline:
    1. git_blame(path, line_range) -> author attribution
    2. git_log(path, n=10) -> recent commits
    3. For significant commits: git_diff(commit1, commit2, path) -> changes
    4. Aggregate into narrative structure

    Args:
        path: File path to analyze attempt_history for
        context_bounds: Context bounds configuration (from AppContext)
        line_range: Optional line range in format "start-end"
        depth: Analysis depth - "recent", "full", or "summary"
    """
    bounds = context_bounds
    attempt_history = []
    all_citations = set()
    bounded = False
    step = 0

    # Parse line range
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    if line_range:
        parts = line_range.split("-")
        if len(parts) == 2:
            try:
                start_line = int(parts[0])
                end_line = int(parts[1])
            except ValueError:
                pass

    # Step 1: Get blame information
    step += 1
    attempt_history.append({
        "step": step,
        "strategy": "git_blame",
        "result": "pending",
        "params": {"path": path, "start_line": start_line, "end_line": end_line},
    })

    blame_result = await _get_blame(path, start_line, end_line)
    attempt_history[-1]["result"] = blame_result["status"]
    if blame_result.get("error"):
        attempt_history[-1]["error"] = blame_result["error"]

    blame_entries = blame_result.get("blame", [])
    current_owners = _compute_ownership(blame_entries)

    # Step 2: Get commit attempt_history
    n_commits = 10 if depth == "recent" else (50 if depth == "full" else 20)
    n_commits = min(n_commits, bounds.max_commits_in_summary)

    step += 1
    attempt_history.append({"step": step, "strategy": "git_log", "result": "pending", "params": {"path": path, "n": n_commits}})

    log_result = await _get_log(path, n=n_commits, since=None)
    attempt_history[-1]["result"] = log_result["status"]
    if log_result.get("error"):
        attempt_history[-1]["error"] = log_result["error"]

    commits = log_result.get("commits", [])

    # Add git commit citations
    for commit in commits[:5]:
        commit_hash = commit.get("hash", "")
        if commit_hash:
            all_citations.add(f"git:{commit_hash}")

    # Step 3: Get diffs for key commits (if depth allows)
    key_changes = []
    if depth in ("full", "key_changes") and commits:
        significant_commits = commits[:3]  # Top 3 most recent

        for commit in significant_commits:
            commit_hash = commit.get("hash", "")

            step += 1
            attempt_history.append({"step": step, "strategy": "git_diff", "result": "pending", "params": {"path": path, "commit": commit_hash}})

            diff_result = await _get_diff(path=path, commit1=f"{commit_hash}^", commit2=commit_hash)
            attempt_history[-1]["result"] = diff_result["status"]

            if diff_result["status"] == "found":
                diff_summary = ""
                ins = diff_result.get("insertions")
                dels = diff_result.get("deletions")
                if ins is not None and dels is not None:
                    diff_summary = f"+{ins}/-{dels} lines"
                elif diff_result.get("diff"):
                    diff_lines = diff_result["diff"].split("\n")
                    add_lines = sum(1 for l in diff_lines if l.startswith("+") and not l.startswith("+++"))
                    del_lines = sum(1 for l in diff_lines if l.startswith("-") and not l.startswith("---"))
                    diff_summary = f"+{add_lines}/-{del_lines} lines"

                key_changes.append({
                    "commit": commit_hash[:8],
                    "date": commit.get("date", ""),
                    "author": commit.get("author_email", commit.get("author_name", "")),
                    "message": commit.get("message", ""),
                    "diff_summary": diff_summary,
                })

    # Add file citation
    if line_range:
        all_citations.add(f"{path}:{line_range}")
    else:
        all_citations.add(path)

    # Build summary
    total_commits = len(commits)
    top_owner = list(current_owners.keys())[0] if current_owners else "unknown"
    top_pct = current_owners.get(top_owner, 0) if current_owners else 0

    if total_commits > 0:
        oldest = commits[-1] if commits else {}
        newest = commits[0] if commits else {}
        summary = (
            f"This file has {total_commits} commits in the analyzed attempt_history. "
            f"Primary author: {top_owner} ({top_pct}% of lines). "
            f"Most recent change: {newest.get('date', 'unknown')} - {newest.get('message', 'no message')[:50]}"
        )
    else:
        summary = f"No commit attempt_history found for {path}"

    # Determine status
    if commits or blame_entries:
        status = "success"
    elif any(h.get("result") == "error" for h in attempt_history):
        status = "partial"
    else:
        status = "success"

    _logger = get_logger()
    _logger.info(
        "explain_code_history_completed",
        path=path,
        commits=len(commits),
        key_changes=len(key_changes),
        owners=len(current_owners),
    )

    return {
        "status": status,
        "file": path,
        "line_range": line_range,
        "summary": summary,
        "key_changes": key_changes,
        "all_commits": commits,
        "commit_count": len(commits),
        "current_owners": current_owners,
        "blame_entries": blame_entries[:20] if depth == "full" else [],
        "attempt_history": attempt_history,
        "citations": sorted(list(all_citations)),
        "bounded": bounded,
    }


__all__ = ["explain_code_history"]
