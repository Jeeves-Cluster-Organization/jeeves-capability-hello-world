"""
Jeeves Code Analysis Capability - App Layer.

This is a standalone application built on mission_system.
It implements a 7-agent pipeline for read-only code analysis.

Architecture:
    jeeves-capability-code-analyser (this app)
        ↓ imports
    mission_system (generic orchestration + contracts)
        ↓ imports
    avionics (infrastructure adapters)
        ↓ imports
    jeeves_core_engine (pure runtime)

Key components:
- agents/: 7-agent pipeline (Perception, Intent, Planner, Traverser, Synthesizer, Critic, Integration)
- tools/: Code analysis tools (composite, resilient, base)
- orchestration/: LangGraph workflow and service
- prompts/: LLM prompts and templates
- models/: Domain-specific data models (TraversalState, etc.)
- registration.py: Capability resource registration (schemas, modes)

Usage:
    # At application startup (before infrastructure initialization)
    from jeeves_capability_code_analyser import register_capability
    register_capability()
"""

from jeeves_capability_code_analyser.registration import (
    CAPABILITY_ID,
    register_capability,
    get_schema_path,
)

__version__ = "1.0.0"

__all__ = [
    "CAPABILITY_ID",
    "register_capability",
    "get_schema_path",
]
