"""
Jeeves Hello World - General Chatbot Gradio Application

3-agent pipeline (Understand → Think → Respond) with REAL LLM via Gradio UI.

Usage:
    python gradio_app.py

Open browser: http://localhost:8000
"""
import gradio as gr
import structlog
from typing import List

from jeeves_capability_hello_world.orchestration import ChatbotService, ChatbotResult
from jeeves_capability_hello_world.pipeline_config import GENERAL_CHATBOT_PIPELINE

# Import prompts to register them (the @register_prompt decorators run on import)
import jeeves_capability_hello_world.prompts.chatbot.understand  # noqa
import jeeves_capability_hello_world.prompts.chatbot.respond  # noqa
import jeeves_capability_hello_world.prompts.chatbot.respond_streaming  # noqa

# Setup logging
logger = structlog.get_logger()

# Global service
_service: ChatbotService = None


def get_or_create_service() -> ChatbotService:
    """Get or create the chatbot service (with REAL LLM)."""
    global _service

    if _service is None:
        logger.info("initializing_chatbot_service", use_mock=False)

        # Import infrastructure components
        from avionics.llm.factory import LLMFactory
        from avionics.wiring import ToolExecutor
        from avionics.settings import Settings
        from jeeves_capability_hello_world.tools.hello_world_tools import HELLO_WORLD_TOOLS

        # Create simple tool registry for hello-world
        class SimpleToolRegistry:
            def __init__(self, tools):
                self._tools = tools

            def has_tool(self, name: str) -> bool:
                return name in self._tools

            def get_tool(self, name: str):
                return self._tools.get(name)

        tool_registry = SimpleToolRegistry(HELLO_WORLD_TOOLS)

        # Create REAL LLM provider factory (not mock)
        settings = Settings()
        llm_factory = LLMFactory(settings=settings, node_profiles=None)
        llm_provider_factory = llm_factory.get_provider_for_agent

        # Create tool executor
        tool_executor = ToolExecutor(registry=tool_registry, logger=logger)

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


async def chat(message: str, history: List):
    """
    Handle user message with TRUE token streaming.

    Pipeline flow:
    - Understand + Think: Buffered (~1-2s)
    - Respond: TRUE STREAMING (tokens appear in real-time)

    Args:
        message: User's message
        history: Chat history as list of message objects

    Yields:
        Accumulated response text (Gradio requires full accumulated text)
    """
    service = get_or_create_service()

    session_id = "gradio-session"
    user_id = "gradio-user"

    logger.info("message_received", message=message, session_id=session_id)

    try:
        # Build conversation history from Gradio format
        conversation_history = []
        for msg in history:
            role = msg.get('role', 'user')
            content_list = msg.get('content', [])
            text = ''
            for item in content_list:
                if item.get('type') == 'text':
                    text = item.get('text', '')
                    break
            if text:
                conversation_history.append({"role": role, "content": text})

        # Build metadata
        metadata = {
            "conversation_history": conversation_history[-5:]
        }

        # Stream events from service
        accumulated = ""
        async for event in service.process_message_stream(
            user_id=user_id,
            session_id=session_id,
            message=message,
            metadata=metadata,
        ):
            # Filter for authoritative tokens only
            if event.type == "token" and not event.debug:
                token = event.data.get("token", "")
                accumulated += token
                yield accumulated  # Gradio requires full accumulated text

            elif event.type == "error":
                error_msg = event.data.get("error", "Unknown error")
                logger.error("streaming_error", error=error_msg)
                yield f"\n\n❌ Error: {error_msg}"
                break

            elif event.type == "done":
                # Terminal event - streaming complete
                logger.info("response_completed", session_id=session_id)
                break

    except Exception as e:
        logger.exception("message_handling_failed", error=str(e))
        yield f"❌ An unexpected error occurred: {str(e)}"


# Create Gradio interface
demo = gr.ChatInterface(
    fn=chat,
    title="Jeeves Hello World - Streaming Chatbot",
    description="A 3-agent AI assistant with TRUE token-level streaming. Watch responses appear in real-time! (Understand → Think → Respond)",
    examples=[
        "Tell me a joke",
        "What is the weather like today?",
        "Explain quantum computing in simple terms",
    ],
)


if __name__ == "__main__":
    logger.info("starting_gradio_app", port=8000)
    demo.launch(
        server_name="0.0.0.0",
        server_port=8000,
        share=False,
    )
