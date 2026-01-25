"""
Chatbot prompts for general-purpose assistant capability.

This module contains LLM prompts for the 3-agent chatbot pipeline:
- understand: Classifies intent and determines if web search is needed
- respond: Crafts helpful responses with or without search results
"""

from .understand import chatbot_understand
from .respond import chatbot_respond

__all__ = [
    "chatbot_understand",
    "chatbot_respond",
]
