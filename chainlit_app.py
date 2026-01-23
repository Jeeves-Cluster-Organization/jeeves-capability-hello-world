"""Chainlit entry point for Jeeves Code Analysis.

Wires the console layer and starts the Chainlit UI.

Run with:
    chainlit run chainlit_app.py
"""

import chainlit as cl

from console.handler import create_handler
from console.adapters.chainlit_adapter import ChainlitAdapter

# Create and register handler at module load
_handler = create_handler()
_handler.register()


@cl.on_chat_start
async def on_start():
    """Initialize adapter for this chat session."""
    adapter = ChainlitAdapter()
    session_id = cl.user_session.get("id", "default")
    await adapter.start(session_id)
    cl.user_session.set("adapter", adapter)


@cl.on_message
async def on_message(message: cl.Message):
    """Handle user message - route through CommBus."""
    content = message.content.strip()

    # Admin command
    if content == "/status":
        adapter = cl.user_session.get("adapter")
        status = await adapter.get_status()
        await cl.Message(content=f"**System Status**\n```json\n{status}\n```").send()
        return

    # Regular query
    adapter = cl.user_session.get("adapter")
    user_id = cl.user_session.get("user", {}).get("id", "anonymous")
    await adapter.send_query(query=content, user_id=user_id)


@cl.on_stop
async def on_stop():
    """Handle stop request."""
    await cl.Message(content="Processing stopped.", author="system").send()
