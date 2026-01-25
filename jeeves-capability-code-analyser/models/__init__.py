"""
Models for Code Analysis capability.

Exports:
- TraversalState: Working memory for code traversal
- Type definitions: Enums for type-safe pipeline
- OperationStatus: Re-exported from protocols for tool results
"""

from models.traversal_state import (
    TraversalState,
    CodeSnippet,
    CallChainEntry,
    DEFAULT_CODE_BOUNDS,
    create_traversal_state,
)
from models.types import (
    # Target classification (used by tool_profiles.py)
    TargetKind,
    Operation,
)

# Re-export OperationStatus from protocols for tool status codes
from protocols import OperationStatus

__all__ = [
    # State
    "TraversalState",
    "CodeSnippet",
    "CallChainEntry",
    "DEFAULT_CODE_BOUNDS",
    "create_traversal_state",
    # Enums
    "TargetKind",
    "Operation",
    "OperationStatus",
]
