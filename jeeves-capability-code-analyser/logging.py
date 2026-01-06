"""Logging utility for code analysis capability.

Provides a simple logger factory that uses structlog directly,
removing dependency on jeeves_mission_system.adapters.

This is a transitional module to help migrate away from adapter imports.
"""

import structlog
from typing import Optional


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.
    
    Args:
        name: Optional logger name. If not provided, uses caller's module.
        
    Returns:
        Configured structlog logger
    """
    if name:
        return structlog.get_logger(name)
    return structlog.get_logger()


__all__ = ["get_logger"]

