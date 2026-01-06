"""Tool base module - core tool implementations.

Phase 2 Constitutional Compliance:
- Uses tool_catalog as the SINGLE source of truth
- No auto-registration at import time (Phase 4)
- Registration happens via tools/registration.py

This module exports tool functions that are registered by tools/registration.py.
"""

from typing import Any, Dict, Optional

from jeeves_protocols import PersistenceProtocol
import structlog
def get_logger(name=None):
    return structlog.get_logger(name) if name else structlog.get_logger()
from tools.catalog import tool_catalog
from .path_helpers import validate_repo_path, get_repo_path


class ToolInitializationError(Exception):
    """Raised when tool initialization fails due to missing dependencies."""
    pass


def validate_tool_dependencies(db: Optional[PersistenceProtocol] = None) -> Dict[str, Any]:
    """
    Validate all tool dependencies before initialization.

    Args:
        db: Optional database client to validate

    Returns:
        Dict with validation results
    """
    result = {
        "repo_path_valid": False,
        "repo_path": get_repo_path(),
        "repo_path_error": None,
        "db_valid": False,
        "db_error": None,
        "all_valid": False,
    }

    # Validate repo path
    _logger = get_logger()
    repo_valid, repo_error = validate_repo_path()
    result["repo_path_valid"] = repo_valid
    if not repo_valid:
        result["repo_path_error"] = repo_error
        _logger.warning(
            "tool_dependency_repo_path_invalid",
            repo_path=result["repo_path"],
            error=repo_error
        )

    # Validate database client
    if db is None:
        result["db_error"] = "Database client is None"
        _logger.warning("tool_dependency_db_none")
    else:
        if hasattr(db, 'fetch_one') and hasattr(db, 'insert'):
            result["db_valid"] = True
        else:
            result["db_error"] = "Database client missing required methods"
            _logger.warning("tool_dependency_db_interface_invalid")

    result["all_valid"] = result["repo_path_valid"] and result["db_valid"]
    return result


__all__ = [
    "tool_catalog",
    "validate_tool_dependencies",
    "ToolInitializationError",
]
