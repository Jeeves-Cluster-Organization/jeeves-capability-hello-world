"""
Jeeves Hello World - Onboarding Chatbot Capability

A 4-agent pipeline with conditional routing demonstrating kernel-driven orchestration.

Architecture:
    Understand (LLM) → Think-Knowledge | Think-Tools → Respond (LLM)
    Respond may loop back to Understand (bounded by max_llm_calls=6)

Key components:
- capability/wiring.py: Capability registration and ChatbotService factory
- pipeline_config.py: 4-agent pipeline with RoutingRule and error_next
- prompts/chatbot/: LLM prompts for Understand and Respond agents
- tools/hello_world_tools.py: get_time, list_tools
- orchestration/: ChatbotService wrapper over PipelineWorker

Usage (RECOMMENDED - using jeeves_core bootstrap):
    from jeeves_core.bootstrap import create_app_context
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
    # Service factory (use jeeves_core.bootstrap for AppContext)
    "create_hello_world_from_app_context",
    # Metadata
    "__version__",
    "__capability__",
]
