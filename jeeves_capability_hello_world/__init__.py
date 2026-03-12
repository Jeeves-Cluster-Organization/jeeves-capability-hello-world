"""Jeeves Hello World - Onboarding Chatbot Capability

A 4-agent pipeline with conditional routing demonstrating kernel-driven orchestration.

Architecture:
    Understand (LLM) → Think-Knowledge | Think-Tools → Respond (LLM)
    Respond may loop back to Understand (bounded by max_llm_calls=6)

Usage:
    from jeeves_capability_hello_world import register_capability
    register_capability()

    # ChatbotService is auto-wired via service_class + pipeline_config.
    # Use jeeves_core.bootstrap.create_app_context() for runtime wiring.
"""

from jeeves_capability_hello_world.capability.wiring import (
    register_capability,
    CAPABILITY_ID,
    CAPABILITY_VERSION,
    CAPABILITY_ROOT,
)

__version__ = CAPABILITY_VERSION
__capability__ = CAPABILITY_ID

__all__ = [
    # Capability registration
    "register_capability",
    "CAPABILITY_ID",
    "CAPABILITY_VERSION",
    "CAPABILITY_ROOT",
    # Metadata
    "__version__",
    "__capability__",
]
