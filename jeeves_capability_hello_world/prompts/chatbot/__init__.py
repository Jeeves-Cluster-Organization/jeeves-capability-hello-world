"""
Chatbot prompts for onboarding assistant capability.

LLM prompts for the pipeline:
- understand: Classifies intent for routing
- respond: Crafts responses (JSON or streaming plain text)
"""

from .understand import chatbot_understand
from .respond import chatbot_respond

__all__ = [
    "chatbot_understand",
    "chatbot_respond",
]
