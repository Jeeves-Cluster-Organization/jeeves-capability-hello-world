"""
Hello World Chatbot Orchestration.

Constitution R7 compliant service wiring and orchestration.

The ChatbotService provides a clean interface for the general chatbot
capability using the Understand → Think → Respond pattern.

Usage:
    from jeeves_capability_hello_world.orchestration import (
        create_hello_world_service,
        ChatbotService,
    )

    # Use factory function (recommended)
    service = create_hello_world_service(
        llm_provider_factory=llm_factory,
        tool_executor=tool_executor,
    )

    # Or use complete wiring
    from jeeves_capability_hello_world.orchestration import create_wiring
    wiring = create_wiring(settings)
    service = create_hello_world_service(**wiring)
"""

from .chatbot_service import ChatbotService, ChatbotResult
from .wiring import (
    create_hello_world_service,
    create_tool_registry_adapter,
    create_wiring,
)
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
    "create_tool_registry_adapter",
    "create_wiring",
    # Types
    "MessageRole",
    "Confidence",
    "ChatMessage",
    "ChatbotRequest",
    "ChatbotResponse",
    "StreamEvent",
]
