"""
Capability-specific types for Code Analysis.

This module defines strict types for the code analysis pipeline,
ensuring type safety and preventing semantic misuse of tools.

Design Principles:
- Enums over strings for closed sets
- Capability-specific (not generic core types)

Used by:
- config/tool_profiles.py for tool selection based on (Operation, TargetKind)
"""

from enum import Enum


# ═══════════════════════════════════════════════════════════════════
# TARGET CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════

class TargetKind(str, Enum):
    """Classification of what the user is asking about.

    Used by Perception to structure observations and by Planner
    to select appropriate tools.
    """
    FILE = "file"                 # Single file: "protocols.py"
    DIRECTORY = "directory"       # Directory/folder: "agents/"
    SYMBOL = "symbol"             # Code symbol: "CoreEnvelope", "process"
    MODULE = "module"             # Logical module: "agents", "tools.base"
    ENTRY_POINT = "entry_point"   # HTTP route, CLI command, main()
    REPOSITORY = "repository"     # Whole repo scope
    UNKNOWN = "unknown"           # Could not classify


class Operation(str, Enum):
    """High-level operation the user wants to perform.

    Maps to tool selection profiles in config/tool_profiles.py.
    """
    EXPLAIN = "explain"           # Understand what code does
    TRACE = "trace"               # Follow execution/data flow
    FIND = "find"                 # Locate code by name/pattern
    MAP = "map"                   # Get structure overview
    COMPARE = "compare"           # Diff/compare code
    HISTORY = "history"           # Git history analysis


__all__ = [
    "TargetKind",
    "Operation",
]
