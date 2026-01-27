"""
Domain Types for Hello World Capability.

Type definitions for the chatbot service request/response patterns.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class MessageRole(str, Enum):
    """Message role in conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Confidence(str, Enum):
    """Confidence level for responses."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ChatMessage:
    """A single message in a conversation."""

    role: MessageRole
    content: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ChatbotRequest:
    """Request to the chatbot service."""

    user_message: str
    session_id: str
    user_id: str
    conversation_history: List[ChatMessage] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ChatbotResponse:
    """Response from the chatbot service."""

    response: str
    citations: List[str] = field(default_factory=list)
    confidence: Confidence = Confidence.MEDIUM
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class StreamEvent:
    """Event emitted during streaming."""

    type: str  # "token", "done", "error"
    data: Dict[str, Any] = field(default_factory=dict)
    debug: bool = False


__all__ = [
    "MessageRole",
    "Confidence",
    "ChatMessage",
    "ChatbotRequest",
    "ChatbotResponse",
    "StreamEvent",
]
