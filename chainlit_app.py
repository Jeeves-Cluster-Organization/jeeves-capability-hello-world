"""
Jeeves Hello World - General Chatbot Chainlit Application

3-agent pipeline (Understand → Think → Respond) with REAL LLM via Chainlit UI.

Usage:
    chainlit run chainlit_app.py

Open browser: http://localhost:8000
"""
import chainlit as cl
import structlog
from typing import Dict, Any, List

from jeeves_capability_hello_world.orchestration import ChatbotService, ChatbotResult
from jeeves_capability_hello_world.pipeline_config import GENERAL_CHATBOT_PIPELINE
from jeeves_capability_hello_world.tools import register_hello_world_tools

# Setup logging
logger = structlog.get_logger()

# Global service
_service: ChatbotService = None


def _get_or_create_service() -> ChatbotService:
    """Get or create the chatbot service (with REAL LLM)."""
    global _service

    if _service is None:
        logger.info("initializing_chatbot_service", use_mock=False)

        # Import infrastructure components
        from avionics.llm import create_llm_provider_factory
        from avionics.tools.executor import ToolExecutor

        # Register hello-world tools
        from jeeves_capability_hello_world.tools.hello_world_tools import HELLO_WORLD_TOOLS

        # Create simple tool registry for hello-world
        class SimpleToolRegistry:
            def __init__(self, tools: Dict[str, Any]):
                self._tools = tools

            def get(self, tool_id: str):
                return self._tools.get(tool_id)

            def list_all(self):
                return list(self._tools.keys())

        tool_registry = SimpleToolRegistry(HELLO_WORLD_TOOLS)

        # Create REAL LLM provider factory (not mock)
        llm_provider_factory = create_llm_provider_factory()

        # Create tool executor
        tool_executor = ToolExecutor(tool_catalog=tool_registry, logger=logger)

        # Create service with REAL LLM (use_mock=False)
        _service = ChatbotService(
            llm_provider_factory=llm_provider_factory,
            tool_executor=tool_executor,
            logger=logger,
            pipeline_config=GENERAL_CHATBOT_PIPELINE,
            use_mock=False,  # ✅ REAL LLM enabled
        )

        logger.info("chatbot_service_ready",
                    pipeline="general_chatbot",
                    agents=3,
                    use_real_llm=True)

    return _service


@cl.on_chat_start
async def on_chat_start():
    """Initialize chat session."""
    session_id = cl.user_session.get("id", "default")
    user_info = cl.user_session.get("user", {})
    user_id = user_info.get("id", "anonymous") if isinstance(user_info, dict) else "anonymous"

    # Store session info
    cl.user_session.set("session_id", session_id)
    cl.user_session.set("user_id", user_id)
    cl.user_session.set("conversation_history", [])

    # Welcome message
    await cl.Message(
        content="👋 Hello! I'm a general-purpose AI assistant powered by a 3-agent system. I can chat, answer questions, and search the web. How can I help you today?",
        author="Assistant"
    ).send()

    logger.info("chat_started", session_id=session_id, user_id=user_id)


@cl.on_message
async def on_message(message: cl.Message):
    """Handle user message with 3-agent pipeline (REAL LLM)."""
    service = _get_or_create_service()

    session_id = cl.user_session.get("session_id")
    user_id = cl.user_session.get("user_id")
    conversation_history = cl.user_session.get("conversation_history", [])

    user_message = message.content.strip()

    logger.info("message_received", message=user_message, session_id=session_id)

    # Show "thinking" indicator
    thinking_msg = cl.Message(content="", author="Assistant")
    await thinking_msg.send()

    try:
        # Update conversation history
        conversation_history.append({"role": "user", "content": user_message})

        # Build metadata with conversation history
        metadata = {
            "conversation_history": conversation_history[-5:]  # Last 5 messages
        }

        # Process with 3-agent pipeline (REAL LLM)
        result: ChatbotResult = await service.process_message(
            user_id=user_id,
            session_id=session_id,
            message=user_message,
            metadata=metadata,
        )

        if result.status == "success":
            # Update message with response
            response_text = result.response

            # Add citations if present
            if result.citations:
                citations_text = "\n\n**Sources:**\n" + "\n".join(
                    f"- {cite}" for cite in result.citations
                )
                response_text += citations_text

            # Add confidence indicator if not high
            if result.confidence and result.confidence != "high":
                confidence_emoji = "🟡" if result.confidence == "medium" else "🔴"
                response_text += f"\n\n{confidence_emoji} *Confidence: {result.confidence}*"

            thinking_msg.content = response_text
            await thinking_msg.update()

            # Update conversation history
            conversation_history.append({"role": "assistant", "content": result.response})
            cl.user_session.set("conversation_history", conversation_history)

            logger.info("response_sent",
                       session_id=session_id,
                       has_citations=bool(result.citations),
                       confidence=result.confidence)

        else:
            # Error response
            error_message = result.error or "An error occurred. Please try again."
            thinking_msg.content = f"❌ {error_message}"
            await thinking_msg.update()

            logger.error("processing_failed",
                        session_id=session_id,
                        error=result.error)

    except Exception as e:
        logger.exception("message_handling_failed", error=str(e))
        thinking_msg.content = f"❌ An unexpected error occurred: {str(e)}"
        await thinking_msg.update()


@cl.on_stop
async def on_stop():
    """Handle stop request."""
    await cl.Message(
        content="⏸️ Processing stopped.",
        author="System"
    ).send()


@cl.on_chat_end
async def on_chat_end():
    """Handle chat session end."""
    session_id = cl.user_session.get("session_id")
    logger.info("chat_ended", session_id=session_id)


if __name__ == "__main__":
    # This runs when executing directly with `chainlit run chainlit_app.py`
    # Chainlit will automatically start the server
    pass
