"""
Jeeves Hello World - General Chatbot Capability

A simplified 3-agent template demonstrating multi-agent orchestration patterns.

This is a minimal, general-purpose chatbot (NOT code-analysis specific) that
anyone can customize for their domain.

Architecture:
    Understand (LLM) → Think (Tools) → Respond (LLM)

Key components:
- pipeline_config.py: 3-agent pipeline configuration
- prompts/chatbot/: LLM prompts for Understand and Respond agents
- tools/: Minimal general-purpose tools (web_search, get_time, list_tools)
- orchestration/: Service wrapper for running the pipeline

Usage:
    from jeeves_capability_code_analyser.pipeline_config import GENERAL_CHATBOT_PIPELINE
    from jeeves_capability_code_analyser.tools import register_hello_world_tools

    # Create and run the chatbot
    # See chainlit_app.py for full example
"""

__version__ = "0.1.0-hello-world"
__capability__ = "general_chatbot"

__all__ = [
    "__version__",
    "__capability__",
]
