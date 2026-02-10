"""
Hello World Chatbot Orchestration.

Constitution R7 compliant service wiring and orchestration.

The ChatbotService provides a clean interface for the general chatbot
capability using the Understand → Think → Respond pattern.

Includes KernelClient integration for resource tracking and quota enforcement.

Usage (recommended - via capability layer):
    from jeeves_capability_hello_world.capability.wiring import (
        register_capability,
        create_hello_world_from_app_context,
    )
    from jeeves_infra.bootstrap import create_app_context

    register_capability()
    app_context = create_app_context()
    service = create_hello_world_from_app_context(app_context)

Usage (explicit params - tests, framework path):
    from jeeves_capability_hello_world.orchestration import (
        create_hello_world_service,
        ChatbotService,
    )

    service = create_hello_world_service(
        llm_provider_factory=llm_factory,
        tool_executor=tool_executor,
        kernel_client=kernel_client,
    )
"""

from .chatbot_service import ChatbotService, ChatbotResult
from .wiring import create_hello_world_service
from .types import (
    MessageRole,
    Confidence,
    ChatMessage,
    ChatbotRequest,
    ChatbotResponse,
    StreamEvent,
)

__all__ = [
    # Service
    "ChatbotService",
    "ChatbotResult",
    # Wiring (Constitution R7)
    "create_hello_world_service",
    # Types
    "MessageRole",
    "Confidence",
    "ChatMessage",
    "ChatbotRequest",
    "ChatbotResponse",
    "StreamEvent",
]
