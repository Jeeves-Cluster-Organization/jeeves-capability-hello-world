"""Hello World Capability for Jeeves-Core.

Thin capability layer that registers hello-world chatbot with jeeves-core.
Uses framework components (mission_system, jeeves_infra) for orchestration,
memory, and infrastructure - keeping capability code minimal.

Constitutional Reference:
- Capability owns domain-specific logic (agent behavior, prompts, tools)
- Core provides runtime (LLM providers, orchestration, persistence)
- Integration via protocols and adapters, never direct imports

Components:
- wiring.py: Capability registration and ChatbotService factory

Usage (RECOMMENDED - using mission_system.bootstrap):
    from mission_system.bootstrap import create_app_context
    from jeeves_capability_hello_world.capability import (
        register_capability,
        create_hello_world_from_app_context,
    )

    # At startup
    register_capability()
    app_context = create_app_context()

    # Returns ChatbotService - use framework EventOrchestrator at API layer
    chatbot_service = create_hello_world_from_app_context(app_context)

Note:
    For event streaming and session memory, use framework components:
    - mission_system.orchestrator.EventOrchestrator for events
    - jeeves_infra.memory.services.SessionStateService for sessions
"""

from jeeves_capability_hello_world.capability.wiring import (
    register_capability,
    create_hello_world_from_app_context,
    CAPABILITY_ID,
    CAPABILITY_VERSION,
)

__all__ = [
    "register_capability",
    "create_hello_world_from_app_context",
    "CAPABILITY_ID",
    "CAPABILITY_VERSION",
]
