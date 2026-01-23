"""
Models for Code Analysis capability.

Exports:
- TraversalState: Working memory for code traversal
- Type definitions: Enums and Pydantic models for type-safe pipeline
- OperationStatus: Re-exported from jeeves_protocols for tool results
"""

from models.traversal_state import (
    TraversalState,
    CodeSnippet,
    CallChainEntry,
    DEFAULT_CODE_BOUNDS,
    create_traversal_state,
)
from models.types import (
    # Target classification
    TargetKind,
    Operation,
    # Tool execution
    ToolResult,
    # Perception output
    Observation,
    PerceptionObservations,
    # Intent output
    StructuredGoal,
    IntentClassification,
    # Evidence types
    EvidenceItem,
    EvidenceSummary,
)

# Re-export OperationStatus from jeeves_protocols for tool status codes
from jeeves_protocols import OperationStatus

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
    # Models
    "ToolResult",
    "Observation",
    "PerceptionObservations",
    "StructuredGoal",
    "IntentClassification",
    "EvidenceItem",
    "EvidenceSummary",
]
