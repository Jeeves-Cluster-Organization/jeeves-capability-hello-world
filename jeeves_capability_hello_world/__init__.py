"""
Jeeves Hello World - General Chatbot Capability

A simplified 3-agent template demonstrating multi-agent orchestration patterns.

This is a minimal, general-purpose chatbot (NOT code-analysis specific) that
anyone can customize for their domain.

Architecture:
    Understand (LLM) → Think (Tools) → Respond (LLM)

Key components:
- registration.py: Capability registration (Constitution R7)
- pipeline_config.py: 3-agent pipeline configuration
- prompts/chatbot/: LLM prompts for Understand and Respond agents
- tools/: Minimal general-purpose tools (web_search, get_time, list_tools)
- orchestration/: Service wrapper and wiring for running the pipeline

Usage:
    from jeeves_capability_hello_world import register_capability, CAPABILITY_ID

    # Register capability at startup (Constitution R7)
    register_capability()

    # Then import infrastructure and create service
    # See gradio_app.py for full example
"""

from jeeves_capability_hello_world.registration import (
    register_capability,
    CAPABILITY_ID,
    CAPABILITY_VERSION,
)

__version__ = CAPABILITY_VERSION
__capability__ = CAPABILITY_ID

__all__ = [
    # Capability registration (Constitution R7)
    "register_capability",
    "CAPABILITY_ID",
    "CAPABILITY_VERSION",
    # Metadata
    "__version__",
    "__capability__",
]
