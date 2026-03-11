"""
Chatbot Prompts for Hello World capability.

Prompt templates for the 4-agent pipeline:
- chatbot.understand: Intent classification and routing
- chatbot.respond: Response synthesis (JSON mode)
- chatbot.respond_streaming: Response synthesis (plain text streaming)

Think agents have no LLM, so no prompts needed.
"""

from jeeves_core.runtime import PromptRegistry
from .chatbot.understand import chatbot_understand
from .chatbot.respond import chatbot_respond
from .chatbot.respond_streaming import chatbot_respond_streaming

prompt_registry = PromptRegistry({
    "chatbot.understand": chatbot_understand(),
    "chatbot.respond": chatbot_respond(),
    "chatbot.respond_streaming": chatbot_respond_streaming(),
})

__all__ = [
    "prompt_registry",
    "chatbot_understand",
    "chatbot_respond",
    "chatbot_respond_streaming",
]
