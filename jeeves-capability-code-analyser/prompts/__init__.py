"""
Chatbot Prompts for Hello World capability.

This module contains prompt templates for the 3-agent chatbot:
- chatbot.understand: Understand agent (intent classification + search decision)
- chatbot.respond: Respond agent (response crafting with citations)

Note: Think agent has has_llm=False (pure tool execution), so no prompt needed.
"""

from .chatbot import (
    chatbot_understand,
    chatbot_respond,
)

__all__ = [
    "chatbot_understand",
    "chatbot_respond",
]
