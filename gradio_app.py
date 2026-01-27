"""
Jeeves Hello World - General Chatbot Gradio Application

3-agent pipeline (Understand → Think → Respond) with REAL LLM via Gradio UI.

Constitution R7 compliant: Uses mission_system.adapters instead of direct
avionics imports.

Usage:
    python gradio_app.py

Open browser: http://localhost:8000
"""
import gradio as gr
import structlog
from typing import List

# Constitution R7: Register capability FIRST, before infrastructure imports
from jeeves_capability_hello_world import register_capability
register_capability()

# Now safe to import infrastructure via adapters
from jeeves_capability_hello_world.orchestration import (
    ChatbotService,
    create_hello_world_service,
    create_tool_registry_adapter,
)
from jeeves_capability_hello_world.tools import initialize_all_tools

# Import prompts to register them (the @register_prompt decorators run on import)
import jeeves_capability_hello_world.prompts.chatbot.understand  # noqa
import jeeves_capability_hello_world.prompts.chatbot.respond  # noqa
import jeeves_capability_hello_world.prompts.chatbot.respond_streaming  # noqa

# Setup logging
logger = structlog.get_logger()

# Global service
_service: ChatbotService = None


def get_or_create_service() -> ChatbotService:
    """Get or create the chatbot service (with REAL LLM and Control Tower)."""
    global _service

    if _service is None:
        logger.info("initializing_chatbot_service", use_mock=False)

        # Constitution R7: Use mission_system.adapters, not direct avionics
        from mission_system.adapters import (
            create_llm_provider_factory,
            create_tool_executor,
            get_settings,
        )
        from control_tower import ControlTower
        from control_tower.types import ResourceQuota

        # Initialize tools with the catalog
        initialize_all_tools(logger=logger)

        # Create tool registry adapter from catalog
        tool_registry = create_tool_registry_adapter()

        # Get settings and create LLM provider factory
        settings = get_settings()
        llm_provider_factory = create_llm_provider_factory(settings)

        # Create tool executor via adapter
        tool_executor = create_tool_executor(tool_registry)

        # Create Control Tower for resource tracking
        ct_logger = structlog.get_logger("control_tower")
        control_tower = ControlTower(
            logger=ct_logger,
            default_quota=ResourceQuota(
                max_llm_calls=10,
                max_tool_calls=50,
                max_agent_hops=21,
                max_iterations=3,
            ),
            default_service="hello_world",
        )
        logger.info("control_tower_initialized")

        # Create service using factory function
        _service = create_hello_world_service(
            llm_provider_factory=llm_provider_factory,
            tool_executor=tool_executor,
            control_tower=control_tower,
            logger=logger,
            use_mock=False,
        )

        logger.info("chatbot_service_ready",
                    pipeline="general_chatbot",
                    agents=3,
                    use_real_llm=True,
                    has_control_tower=True)

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
        # Gradio ChatInterface passes history as [[user_msg, assistant_msg], ...]
        conversation_history = []
        for msg in history:
            if isinstance(msg, (list, tuple)) and len(msg) >= 2:
                # Gradio format: [user_message, assistant_message]
                user_msg, assistant_msg = msg[0], msg[1]
                if user_msg:
                    conversation_history.append({"role": "user", "content": str(user_msg)})
                if assistant_msg:
                    conversation_history.append({"role": "assistant", "content": str(assistant_msg)})
            elif isinstance(msg, dict):
                # Alternative dict format (if Gradio changes)
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                if isinstance(content, list):
                    # Handle content list format
                    for item in content:
                        if isinstance(item, dict) and item.get('type') == 'text':
                            content = item.get('text', '')
                            break
                if content:
                    conversation_history.append({"role": role, "content": str(content)})

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
