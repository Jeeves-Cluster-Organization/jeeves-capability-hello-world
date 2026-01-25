"""Session state tools for code analysis agent.

Phase 2/4 Constitutional Compliance - No auto-registration at import time

These tools manage session state (L4 working memory) for the code analysis agent.
Only the session_write operation is WRITE level; all others are READ_ONLY.

Tools:
- get_session_state: Read current session state
- save_session_state: Save updated session state
"""

import json
from typing import Any, Dict, Optional

from protocols import LoggerProtocol
import structlog
get_logger = structlog.get_logger
from protocols import RiskLevel


# In-memory session store (replaced by database in production)
_session_store: Dict[str, Dict[str, Any]] = {}


def _get_default_state() -> Dict[str, Any]:
    """Return default TraversalState structure."""
    return {
        "query_intent": "",
        "scope_path": None,
        "explored_files": [],
        "explored_symbols": [],
        "pending_files": [],
        "pending_symbols": [],
        "relevant_snippets": [],
        "call_chain": [],
        "current_loop": 0,
        "tokens_used": 0,
        "detected_languages": [],
        "repo_patterns": {},
    }


async def get_session_state(session_id: str) -> Dict[str, Any]:
    """Get current session state.

    Args:
        session_id: Session identifier

    Returns:
        Dict with:
        - status: "success" or "error"
        - state: Current TraversalState
        - is_new: Whether this is a new session
    """
    if not session_id:
        return {
            "status": "error",
            "error": "Session ID is required",
        }

    try:
        # Check if session exists
        if session_id in _session_store:
            return {
                "status": "success",
                "session_id": session_id,
                "state": _session_store[session_id],
                "is_new": False,
            }

        # Create new session with default state
        default_state = _get_default_state()
        _session_store[session_id] = default_state

        return {
            "status": "success",
            "session_id": session_id,
            "state": default_state,
            "is_new": True,
        }

    except Exception as e:
        _logger = get_logger()
        _logger.error("get_session_state_error", session_id=session_id, error=str(e))
        return {
            "status": "error",
            "error": f"Failed to get session state: {e}",
        }


async def save_session_state(
    session_id: str,
    state: Dict[str, Any],
) -> Dict[str, Any]:
    """Save updated session state.

    Args:
        session_id: Session identifier
        state: TraversalState to save

    Returns:
        Dict with:
        - status: "success" or "error"
    """
    if not session_id:
        return {
            "status": "error",
            "error": "Session ID is required",
        }

    if not state:
        return {
            "status": "error",
            "error": "State is required",
        }

    try:
        # Validate state structure
        default_keys = set(_get_default_state().keys())
        state_keys = set(state.keys())

        # Merge with defaults for any missing keys
        merged_state = _get_default_state()
        for key in state_keys:
            if key in default_keys:
                merged_state[key] = state[key]

        # Save to store
        _session_store[session_id] = merged_state

        _logger = get_logger()
        _logger.info(
            "session_state_saved",
            session_id=session_id,
            explored_files_count=len(merged_state.get("explored_files", [])),
            current_loop=merged_state.get("current_loop", 0),
        )

        return {
            "status": "success",
            "session_id": session_id,
        }

    except Exception as e:
        _logger = get_logger()
        _logger.error("save_session_state_error", session_id=session_id, error=str(e))
        return {
            "status": "error",
            "error": f"Failed to save session state: {e}",
        }


async def list_tools() -> Dict[str, Any]:
    """List all available tools for the Planner.

    Returns:
        Dict with:
        - status: "success" or "error"
        - tools: List of tool definitions
    """
    try:
        tools = tool_registry.list_tools()

        # Filter to code analysis tools only
        code_tools = [t for t in tools if t["risk_level"] in ("read_only", "write")]

        return {
            "status": "success",
            "tools": code_tools,
            "count": len(code_tools),
        }

    except Exception as e:
        _logger = get_logger()
        _logger.error("list_tools_error", error=str(e))
        return {
            "status": "error",
            "error": f"Failed to list tools: {e}",
        }


__all__ = ["get_session_state", "save_session_state", "list_tools"]
