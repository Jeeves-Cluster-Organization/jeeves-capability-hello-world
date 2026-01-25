"""App Bootstrap - Optional vertical registration.

Verticals are registered based on configuration or environment.
The core can start with zero verticals.

No magic, no import side-effects. Call bootstrap_all_verticals() at startup.

IMPORTANT: Host app code uses only jeeves_protocols public API.

ADR-001 Decision 3: All bootstrap functions receive AppContext for DI.
"""
import os
from typing import List, TYPE_CHECKING

from avionics.logging import get_current_logger

if TYPE_CHECKING:
    from protocols import AppContextProtocol


def get_enabled_verticals() -> List[str]:
    """
    Get list of enabled verticals from environment.

    Returns empty list if no verticals configured (core-only mode).

    Environment:
        ENABLED_VERTICALS: Comma-separated list of vertical IDs
                          (default: "code_analysis")
                          (empty string: core-only mode)

    Examples:
        ENABLED_VERTICALS="code_analysis"           # Default
        ENABLED_VERTICALS=""                        # Core-only mode
        ENABLED_VERTICALS="code_analysis,other"     # Multiple verticals
    """
    enabled = os.getenv("ENABLED_VERTICALS", "code_analysis")
    if not enabled:
        return []
    return [v.strip() for v in enabled.split(",") if v.strip()]


def bootstrap_vertical(vertical_id: str) -> None:
    """Bootstrap a single vertical by ID.

    Args:
        vertical_id: Vertical identifier (e.g., "code_analysis")

    Raises:
        ValueError: If vertical ID is unknown
    """
    _logger = get_current_logger()
    if vertical_id == "code_analysis":
        # Code analysis app is standalone, no bootstrap needed
        _logger.info("code_analysis_app_standalone",
                    message="Code analysis app is standalone, no vertical registration needed")
    else:
        _logger.warning("unknown_vertical", vertical_id=vertical_id)
        raise ValueError(f"Unknown vertical ID: {vertical_id}")


def bootstrap_all_verticals(app_context: "AppContextProtocol") -> None:
    """
    Register all enabled verticals.

    Reads ENABLED_VERTICALS environment variable (comma-separated).
    If not set or empty, core starts with zero verticals.

    This enforces Constitution Rule 1: "Core must not import verticals."
    The core can start independently without any vertical.

    Args:
        app_context: AppContext with vertical registry (ADR-001 Decision 3)

    Environment:
        ENABLED_VERTICALS: Comma-separated vertical IDs (default: "code_analysis")

    Examples:
        ENABLED_VERTICALS="code_analysis"  # Default
        ENABLED_VERTICALS=""               # Core-only mode
        ENABLED_VERTICALS="code_analysis,other_vertical"  # Multiple
    """
    _logger = get_current_logger()
    enabled = get_enabled_verticals()

    if not enabled:
        _logger.info("core_only_mode", message="No verticals enabled, core running standalone")
        return

    _logger.info("bootstrapping_verticals", enabled_verticals=enabled)

    for vertical_id in enabled:
        # Skip if already registered (idempotent)
        if app_context.is_vertical_registered(vertical_id):
            _logger.debug("vertical_already_registered", vertical_id=vertical_id)
            continue
        bootstrap_vertical(vertical_id)

    _logger.info("verticals_bootstrapped", count=len(enabled))
