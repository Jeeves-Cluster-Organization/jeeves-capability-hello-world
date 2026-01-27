"""
Capability Registration for Hello World Chatbot.

Constitution R7 compliant capability registration.
This module provides the central entry point for registering all capability
resources at startup time.

Architecture:
    Apps call register_capability() BEFORE importing infrastructure.
    This ensures all capability resources are registered before use.

Usage:
    from jeeves_capability_hello_world import register_capability
    register_capability()  # Call at module/startup level

    # Then import and use infrastructure
    from mission_system.adapters import create_llm_provider_factory
"""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Capability identity
CAPABILITY_ID = "hello_world"
CAPABILITY_VERSION = "0.1.0"
CAPABILITY_ROOT = Path(__file__).parent


def _create_service_factory() -> Callable:
    """
    Create deferred factory for ChatbotService.

    Returns factory function to avoid circular imports.
    The factory is called at runtime when the service is needed.
    """
    def factory(
        llm_provider_factory: Callable,
        tool_executor: Any,
        logger: Any,
        persistence: Optional[Any] = None,
        control_tower: Optional[Any] = None,
    ):
        from jeeves_capability_hello_world.orchestration.chatbot_service import ChatbotService
        from jeeves_capability_hello_world.pipeline_config import GENERAL_CHATBOT_PIPELINE

        return ChatbotService(
            llm_provider_factory=llm_provider_factory,
            tool_executor=tool_executor,
            logger=logger,
            pipeline_config=GENERAL_CHATBOT_PIPELINE,
            use_mock=False,
        )
    return factory


def _create_tools_initializer() -> Callable:
    """
    Create deferred initializer for tools.

    Returns initializer function to avoid import-time side effects.
    """
    def initializer(db: Optional[Any] = None, logger: Optional[Any] = None) -> Dict[str, Any]:
        from jeeves_capability_hello_world.tools import initialize_all_tools
        return initialize_all_tools(db=db, logger=logger)
    return initializer


def _get_prompts() -> Dict[str, Any]:
    """
    Get all registered prompts for this capability.

    Returns dict mapping prompt keys to prompt specs.
    """
    # Prompts are registered via decorators when imported
    # Import them to ensure registration
    import jeeves_capability_hello_world.prompts.chatbot.understand  # noqa: F401
    import jeeves_capability_hello_world.prompts.chatbot.respond  # noqa: F401
    import jeeves_capability_hello_world.prompts.chatbot.respond_streaming  # noqa: F401

    return {
        "chatbot.understand": {
            "description": "Intent classification and query analysis",
            "version": "1.0",
        },
        "chatbot.respond": {
            "description": "JSON response synthesis",
            "version": "1.0",
        },
        "chatbot.respond_streaming": {
            "description": "Plain text streaming response",
            "version": "1.0",
        },
    }


def _get_agent_definitions() -> List[Dict[str, Any]]:
    """
    Get agent definitions for this capability.

    Returns list of agent configuration dicts.
    """
    return [
        {
            "name": "understand",
            "description": "Analyze user intent and plan approach",
            "has_llm": True,
            "layer": "perception",
        },
        {
            "name": "think",
            "description": "Execute tools based on intent",
            "has_llm": False,
            "layer": "execution",
        },
        {
            "name": "respond",
            "description": "Synthesize response from gathered information",
            "has_llm": True,
            "layer": "synthesis",
        },
    ]


def register_capability() -> Dict[str, Any]:
    """
    Register all capability resources at startup.

    Constitution R7: This function MUST be called before importing
    infrastructure (mission_system, avionics) to ensure resources
    are registered before use.

    Returns:
        Dict with registration results including:
        - capability_id: Capability identifier
        - service_factory: Factory function for creating the service
        - tools_initializer: Function to initialize tools
        - prompts: Registered prompt keys
        - agents: Agent definitions

    Example:
        from jeeves_capability_hello_world import register_capability

        # Call at startup, before infrastructure imports
        registration = register_capability()

        # Now safe to import infrastructure
        from mission_system.adapters import create_llm_provider_factory
    """
    return {
        "capability_id": CAPABILITY_ID,
        "capability_version": CAPABILITY_VERSION,
        "capability_root": str(CAPABILITY_ROOT),
        "service_factory": _create_service_factory(),
        "tools_initializer": _create_tools_initializer(),
        "prompts": _get_prompts(),
        "agents": _get_agent_definitions(),
    }


__all__ = [
    "CAPABILITY_ID",
    "CAPABILITY_VERSION",
    "CAPABILITY_ROOT",
    "register_capability",
]
