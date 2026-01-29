"""
Jeeves Hello World - General Chatbot Capability

A simplified 3-agent template demonstrating multi-agent orchestration patterns.
Uses framework components for orchestration - capability layer is thin.

Architecture:
    Understand (LLM) → Think (Tools) → Respond (LLM)

Key components:
- capability/wiring.py: Capability registration and ChatbotService factory
- pipeline_config.py: 3-agent pipeline configuration
- prompts/chatbot/: LLM prompts for Understand and Respond agents
- tools/: Minimal general-purpose tools (web_search, get_time, list_tools)
- orchestration/: ChatbotService wrapper over PipelineRunner

Usage (RECOMMENDED - using mission_system bootstrap):
    from mission_system.bootstrap import create_app_context
    from jeeves_capability_hello_world import register_capability, create_hello_world_from_app_context

    # Register capability at startup
    register_capability()

    # Create app context (unified configuration)
    app_context = create_app_context()

    # Get ChatbotService (use framework EventOrchestrator at API layer for events)
    chatbot_service = create_hello_world_from_app_context(app_context)

Usage (STANDALONE):
    from jeeves_capability_hello_world import register_capability, CAPABILITY_ID

    # Register capability at startup
    register_capability()

    # See gradio_app.py for standalone wiring example
"""

from jeeves_capability_hello_world.capability.wiring import (
    register_capability,
    CAPABILITY_ID,
    CAPABILITY_VERSION,
    CAPABILITY_ROOT,
    AGENT_LLM_CONFIGS,
    AGENT_DEFINITIONS,
    get_agent_config,
    create_hello_world_from_app_context,
)

__version__ = CAPABILITY_VERSION
__capability__ = CAPABILITY_ID

__all__ = [
    # Capability registration
    "register_capability",
    "CAPABILITY_ID",
    "CAPABILITY_VERSION",
    "CAPABILITY_ROOT",
    # Agent configurations
    "AGENT_LLM_CONFIGS",
    "AGENT_DEFINITIONS",
    "get_agent_config",
    # Service factory (use mission_system.bootstrap for AppContext)
    "create_hello_world_from_app_context",
    # Metadata
    "__version__",
    "__capability__",
]
