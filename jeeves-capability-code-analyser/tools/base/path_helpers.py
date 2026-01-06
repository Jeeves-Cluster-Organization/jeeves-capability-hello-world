"""Centralized path helpers for code analysis tools.

This module provides shared path utilities used by:
- code_tools.py
- index_tools.py
- git_tools.py

Centralizing these prevents code duplication and ensures consistent
security checks across all file operations.

Uses language_config from registry (constitutional pattern).
Config MUST be registered at capability bootstrap via:
    runtime.config_registry.register(ConfigKeys.LANGUAGE_CONFIG, get_language_config())
"""

import os
import warnings
from pathlib import Path
from typing import Optional, Set, Tuple

from jeeves_capability_code_analyser.config import LanguageConfig
from jeeves_mission_system.contracts import get_config_registry, ConfigKeys
from jeeves_capability_code_analyser.logging import get_logger

# Cache for repo path validation status
_repo_path_validated: bool = False
_repo_path_valid: bool = False


def get_language_config_from_registry() -> LanguageConfig:
    """Get language config from the global config registry.

    Config MUST be registered at capability bootstrap.
    Raises if config not found in registry.

    Returns:
        LanguageConfig instance

    Raises:
        RuntimeError: If language_config not registered in registry
    """
    registry = get_config_registry()
    config = registry.get(ConfigKeys.LANGUAGE_CONFIG)
    if config is None:
        raise RuntimeError(
            "language_config not found in registry. "
            "Ensure register_capability_configs() is called at bootstrap."
        )
    return config


def reset_repo_path_cache() -> None:
    """Reset the repo path validation cache.

    Call this when REPO_PATH environment variable changes (e.g., in tests)
    to force re-validation on next access.
    """
    global _repo_path_validated, _repo_path_valid
    _repo_path_validated = False
    _repo_path_valid = False


def get_repo_path() -> str:
    """Get the repository path from environment or default.

    Returns:
        Path to repository root (from REPO_PATH env var or /workspace)

    Note:
        Use validate_repo_path() to check if the path exists before operations.
    """
    return os.environ.get("REPO_PATH", "/workspace")


def validate_repo_path() -> Tuple[bool, str]:
    """Validate that the repository path exists and is accessible.

    Returns:
        Tuple of (is_valid, error_message).
        If valid, error_message is empty string.

    Example:
        is_valid, error = validate_repo_path()
        if not is_valid:
            logger.error("repo_path_invalid", error=error)
    """
    global _repo_path_validated, _repo_path_valid

    repo_path = get_repo_path()
    path = Path(repo_path)

    if not path.exists():
        _repo_path_validated = True
        _repo_path_valid = False
        error_msg = (
            f"REPO_PATH '{repo_path}' does not exist. "
            f"Set REPO_PATH environment variable to a valid directory."
        )
        get_logger().error("repo_path_not_found", path=repo_path)
        return False, error_msg

    if not path.is_dir():
        _repo_path_validated = True
        _repo_path_valid = False
        error_msg = f"REPO_PATH '{repo_path}' is not a directory."
        get_logger().error("repo_path_not_directory", path=repo_path)
        return False, error_msg

    # Check if readable
    try:
        list(path.iterdir())
    except PermissionError:
        _repo_path_validated = True
        _repo_path_valid = False
        error_msg = f"REPO_PATH '{repo_path}' is not readable (permission denied)."
        get_logger().error("repo_path_permission_denied", path=repo_path)
        return False, error_msg

    _repo_path_validated = True
    _repo_path_valid = True
    get_logger().debug("repo_path_validated", path=repo_path)
    return True, ""


def ensure_repo_path_valid() -> bool:
    """Ensure repo path is valid, logging warning if not.

    Returns:
        True if repo path is valid, False otherwise.

    This is a convenience wrapper that logs the error and can be used
    as a guard at the start of tool functions.
    """
    global _repo_path_validated, _repo_path_valid

    # Use cached result if available
    if _repo_path_validated:
        return _repo_path_valid

    is_valid, error_msg = validate_repo_path()
    if not is_valid:
        get_logger().warning("repo_path_validation_failed", error=error_msg)
    return is_valid


def repo_path_error_response() -> dict:
    """Return a standardized error response for invalid REPO_PATH.

    Use this at the start of tool functions to avoid code duplication:

        if not ensure_repo_path_valid():
            return repo_path_error_response()

    Returns:
        Dict with status="error" and descriptive error message.
    """
    repo_path = get_repo_path()
    return {
        "status": "error",
        "error": f"REPO_PATH '{repo_path}' does not exist or is not accessible. "
                 f"Set REPO_PATH environment variable to a valid directory.",
    }


def is_safe_path(path: str, repo_path: str) -> bool:
    """Check if path is within the allowed repository.

    Args:
        path: Path to check
        repo_path: Repository root path

    Returns:
        True if path is within repo bounds, False otherwise
    """
    try:
        resolved = Path(path).resolve()
        repo_resolved = Path(repo_path).resolve()
        return str(resolved).startswith(str(repo_resolved))
    except (ValueError, OSError):
        return False


def resolve_path(path: Optional[str], repo_path: str) -> Optional[Path]:
    """Resolve path relative to repo, return None if unsafe.

    Args:
        path: Path to resolve (can be relative, absolute, empty, or None).
              None or empty string returns repo root.
        repo_path: Repository root path

    Returns:
        Resolved Path within repo bounds, or None if outside bounds

    Note:
        Paths starting with "/" are treated as relative to repo root, not filesystem root.
        This handles LLM-generated paths like "/" or "/agents/" correctly.

    Constitutional compliance (P3 - Bounded Efficiency):
        Gracefully handles None/empty inputs by returning repo root.
    """
    if not path:
        return Path(repo_path)

    # Normalize path: strip leading slashes and treat as relative to repo
    # This handles LLM-generated paths like "/" or "/agents/" correctly
    normalized = path.lstrip("/")
    if not normalized:
        # Path was just "/" - return repo root
        return Path(repo_path)

    # Always treat as relative to repo, even if it looked like an absolute path
    full_path = Path(repo_path) / normalized

    resolved = full_path.resolve()
    repo_resolved = Path(repo_path).resolve()

    if not str(resolved).startswith(str(repo_resolved)):
        return None

    return resolved


def count_tokens_approx(text: str) -> int:
    """Approximate token count (1 token ~= 4 chars).

    Args:
        text: Text to count tokens for

    Returns:
        Approximate token count
    """
    return len(text) // 4


# Default directories to exclude from code analysis
DEFAULT_EXCLUDED_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
}

# Default code file extensions
DEFAULT_CODE_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
}


def get_excluded_dirs(config: Optional[LanguageConfig] = None) -> Set[str]:
    """Get directories to exclude based on language config.

    Args:
        config: Optional LanguageConfig. Uses registry config if None.

    Returns:
        Set of directory names to exclude
    """
    if config is None:
        config = get_language_config_from_registry()
    return config.exclude_dirs


def get_code_extensions(config: Optional[LanguageConfig] = None) -> Set[str]:
    """Get code file extensions based on language config.

    Args:
        config: Optional LanguageConfig. Uses registry config if None.

    Returns:
        Set of file extensions (with leading dot)
    """
    if config is None:
        config = get_language_config_from_registry()
    return config.code_extensions


def should_process_file(
    filepath: Path,
    config: Optional[LanguageConfig] = None
) -> bool:
    """Check if a file should be processed based on language config.

    Args:
        filepath: Path to check
        config: Optional LanguageConfig. Uses registry config if None.

    Returns:
        True if file should be processed
    """
    if config is None:
        config = get_language_config_from_registry()

    # Check extension
    if not config.supports_file(str(filepath)):
        return False

    # Check path components for excluded dirs
    for part in filepath.parts:
        if config.should_exclude_dir(part):
            return False

    return True
