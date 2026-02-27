"""
Chatbot Prompts for Hello World capability.

Prompt templates for the 4-agent pipeline:
- chatbot.understand: Intent classification and routing
- chatbot.respond: Response synthesis (JSON mode)
- chatbot.respond_streaming: Response synthesis (plain text streaming)

Think agents have no LLM, so no prompts needed.
"""

from .chatbot import (
    chatbot_understand,
    chatbot_respond,
)

__all__ = [
    "chatbot_understand",
    "chatbot_respond",
]
