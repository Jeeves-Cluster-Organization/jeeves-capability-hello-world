"""
Jeeves Onboarding Assistant - Gradio Application

3-agent pipeline (Understand → Think → Respond) that explains the Jeeves ecosystem.
Shows intent classification and knowledge retrieval as the pipeline progresses.

Features:
- Intent classification: architecture, concept, getting_started, component, general
- Targeted knowledge retrieval based on classified intent
- Streaming responses with pipeline visibility

Supports Ollama and other OpenAI-compatible endpoints.

Usage:
    # With Ollama (default)
    python gradio_app.py

    # With custom endpoint
    JEEVES_LLM_BASE_URL=http://localhost:8080/v1 python gradio_app.py

    # With OpenAI
    JEEVES_LLM_API_KEY=sk-xxx JEEVES_LLM_BASE_URL=https://api.openai.com/v1 python gradio_app.py

Open browser: http://localhost:8001
"""
import gradio as gr
import structlog
import json
import os
from typing import List, Tuple, Generator

# =============================================================================
# LLM CONFIGURATION - Configure for Ollama or other providers
# =============================================================================

# Default to Ollama running locally
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"
DEFAULT_OLLAMA_MODEL = "llama3.2"  # Change to your installed model

# Set LLM environment variables (can be overridden by env vars before running)
os.environ.setdefault("JEEVES_LLM_ADAPTER", "openai_http")
os.environ.setdefault("JEEVES_LLM_BASE_URL", DEFAULT_OLLAMA_BASE_URL)
os.environ.setdefault("JEEVES_LLM_MODEL", DEFAULT_OLLAMA_MODEL)
os.environ.setdefault("JEEVES_LLM_API_KEY", "ollama")  # Ollama doesn't need a real key

# Also set the agent-specific models (these override the default)
os.environ.setdefault("JEEVES_LLM_UNDERSTAND_MODEL", DEFAULT_OLLAMA_MODEL)
os.environ.setdefault("JEEVES_LLM_RESPOND_MODEL", DEFAULT_OLLAMA_MODEL)

# =============================================================================

# Constitution R7: Register capability FIRST, before infrastructure imports
from jeeves_capability_hello_world import register_capability
register_capability()

# Register LLM provider factory (required before using create_llm_provider_factory)
from jeeves_infra.wiring import set_llm_provider_factory
from jeeves_infra.llm.factory import create_llm_provider
set_llm_provider_factory(create_llm_provider)

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
    """Get or create the chatbot service (with REAL LLM and KernelClient)."""
    global _service

    if _service is None:
        logger.info("initializing_chatbot_service", use_mock=False)

        # Constitution R7: Use jeeves_infra.bootstrap for unified initialization
        from jeeves_infra.bootstrap import create_app_context
        from jeeves_infra.wiring import (
            create_llm_provider_factory,
            create_tool_executor,
        )
        from jeeves_infra.kernel_client import get_kernel_client

        # Create app context (composition root)
        app_context = create_app_context()

        # Initialize tools with the catalog
        initialize_all_tools(logger=logger)

        # Create tool registry adapter from catalog
        tool_registry = create_tool_registry_adapter()

        # Create LLM provider factory from app context settings
        llm_provider_factory = create_llm_provider_factory(app_context.settings)

        # Create tool executor via adapter
        tool_executor = create_tool_executor(tool_registry)

        # Get kernel_client for resource tracking
        # Note: kernel_client connection is async, but we defer until first use
        kernel_client = app_context.kernel_client
        logger.info("kernel_client_status", available=kernel_client is not None)

        # Create service using factory function
        _service = create_hello_world_service(
            llm_provider_factory=llm_provider_factory,
            tool_executor=tool_executor,
            kernel_client=kernel_client,
            logger=logger,
            use_mock=False,
        )

        logger.info("chatbot_service_ready",
                    pipeline="onboarding_chatbot",
                    agents=3,
                    use_real_llm=True,
                    has_kernel_client=kernel_client is not None)

    return _service


def format_agent_output(agent_name: str, data: dict, status: str) -> str:
    """Format agent output for display - shows classification and knowledge retrieval."""
    if status == "completed":
        if agent_name == "understand":
            intent = data.get("intent", "")
            topic = data.get("topic", "")
            if intent and topic:
                return f"📋 *{intent}: {topic}*"
            elif intent:
                return f"📋 *{intent}*"
        elif agent_name == "think":
            # Show knowledge retrieval status
            info = data.get("information", {})
            if info.get("knowledge_retrieved"):
                return "📚 *Knowledge retrieved*"
    return ""


async def chat_with_pipeline(message: str, history: List[List]) -> Generator:
    """
    Handle user message showing full pipeline progress.

    Pipeline flow with visibility:
    1. Understand: Shows intent analysis
    2. Think: Shows tool execution
    3. Respond: TRUE STREAMING (tokens appear in real-time)

    Args:
        message: User's message
        history: Chat history as list of [user_msg, assistant_msg] pairs

    Yields:
        Tuples of (history, pipeline_status) for updating both components
    """
    service = get_or_create_service()

    session_id = "gradio-session"
    user_id = "gradio-user"

    logger.info("message_received", message=message, session_id=session_id)

    # Initialize pipeline status display
    pipeline_status = ""
    current_response = ""

    # Agent outputs collected during pipeline
    agent_outputs = {}

    try:
        # Build conversation history from Gradio format (dict format in Gradio 6.x)
        conversation_history = []
        for msg in history:
            if isinstance(msg, dict):
                # Gradio 6.x format: {"role": "user/assistant", "content": "..."}
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                # Handle multimodal content list
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get('type') == 'text':
                            content = item.get('text', '')
                            break
                if content:
                    # Strip pipeline markers from assistant messages
                    if role == 'assistant' and "---" in str(content):
                        content = str(content).split("---")[-1].strip()
                    conversation_history.append({"role": role, "content": str(content)})
            elif isinstance(msg, (list, tuple)) and len(msg) >= 2:
                # Legacy tuple format fallback
                user_msg, assistant_msg = msg[0], msg[1]
                if user_msg:
                    conversation_history.append({"role": "user", "content": str(user_msg)})
                if assistant_msg:
                    clean_msg = str(assistant_msg)
                    if "---" in clean_msg:
                        clean_msg = clean_msg.split("---")[-1].strip()
                    conversation_history.append({"role": "assistant", "content": clean_msg})

        # Build metadata
        metadata = {
            "conversation_history": conversation_history[-5:]
        }

        # Stream events from service
        async for event in service.process_message_stream(
            user_id=user_id,
            session_id=session_id,
            message=message,
            metadata=metadata,
        ):
            event_type = event.type
            agent_name = event.agent if hasattr(event, 'agent') else ""
            data = event.data if hasattr(event, 'data') else {}

            if event_type == "stage":
                status = data.get("status", "")
                agent_name = agent_name or data.get("agent", "")

                # Capture agent outputs for understand and think
                if status == "completed":
                    output_text = format_agent_output(agent_name, data, "completed")
                    if output_text:
                        if agent_name == "understand":
                            pipeline_status = output_text + " "
                        elif agent_name == "think":
                            pipeline_status += output_text + "\n\n"

            elif event_type == "token" and not getattr(event, 'debug', False):
                # Streaming token from Respond agent
                token = data.get("token", "")
                current_response += token
                yield pipeline_status + current_response

            elif event_type == "error":
                error_msg = data.get("error", "Unknown error")
                logger.error("streaming_error", error=error_msg)
                yield f"Error: {error_msg}"
                break

            elif event_type == "done":
                logger.info("response_completed", session_id=session_id)
                yield pipeline_status + current_response
                break

    except Exception as e:
        logger.exception("message_handling_failed", error=str(e))
        yield f"❌ An unexpected error occurred: {str(e)}"


# =============================================================================
# LLM Settings Management
# =============================================================================

def get_current_llm_config() -> dict:
    """Get current LLM configuration from environment."""
    return {
        "base_url": os.getenv("JEEVES_LLM_BASE_URL", DEFAULT_OLLAMA_BASE_URL),
        "model": os.getenv("JEEVES_LLM_MODEL", DEFAULT_OLLAMA_MODEL),
        "api_key": os.getenv("JEEVES_LLM_API_KEY", "ollama"),
    }


def update_llm_config(base_url: str, model: str, api_key: str) -> str:
    """Update LLM configuration and reinitialize service."""
    global _service

    # Update environment variables
    os.environ["JEEVES_LLM_BASE_URL"] = base_url
    os.environ["JEEVES_LLM_MODEL"] = model
    os.environ["JEEVES_LLM_API_KEY"] = api_key
    os.environ["JEEVES_LLM_UNDERSTAND_MODEL"] = model
    os.environ["JEEVES_LLM_RESPOND_MODEL"] = model

    # Reset service so it reinitializes with new config
    _service = None

    logger.info(
        "llm_config_updated",
        base_url=base_url,
        model=model,
    )

    return f"Configuration updated. Using model `{model}` at `{base_url}`"


# Create custom Gradio interface
with gr.Blocks(title="Jeeves Onboarding Assistant") as demo:
    gr.Markdown("# Jeeves Onboarding Assistant")

    # Settings accordion (collapsed by default)
    with gr.Accordion("LLM Settings (Ollama / OpenAI)", open=False):
        gr.Markdown("""
        Configure your LLM endpoint. Default is **Ollama** running locally.

        **Popular Ollama models:** `llama3.2`, `llama3.1`, `qwen2.5`, `mistral`, `phi3`
        """)

        with gr.Row():
            base_url_input = gr.Textbox(
                label="API Base URL",
                value=os.getenv("JEEVES_LLM_BASE_URL", DEFAULT_OLLAMA_BASE_URL),
                placeholder="http://localhost:11434/v1",
            )
            model_input = gr.Textbox(
                label="Model Name",
                value=os.getenv("JEEVES_LLM_MODEL", DEFAULT_OLLAMA_MODEL),
                placeholder="llama3.2",
            )

        with gr.Row():
            api_key_input = gr.Textbox(
                label="API Key (optional for Ollama)",
                value="",
                placeholder="sk-xxx or 'ollama'",
                type="password",
            )
            apply_btn = gr.Button("Apply Settings", variant="secondary")

        config_status = gr.Markdown("")

        apply_btn.click(
            update_llm_config,
            inputs=[base_url_input, model_input, api_key_input],
            outputs=[config_status],
        )

    chatbot = gr.Chatbot(
        label="Conversation",
        height=450,
    )

    with gr.Row():
        msg = gr.Textbox(
            label="Your message",
            placeholder="Ask a question...",
            scale=4,
            show_label=False,
        )
        submit_btn = gr.Button("Send", variant="primary", scale=1)

    with gr.Row():
        clear_btn = gr.Button("Clear Chat")

    async def respond(message: str, chat_history: List):
        """Handle message and update chat with pipeline visibility."""
        if not message.strip():
            yield chat_history
            return

        # Add user message to history (Gradio 6.x uses dict format)
        chat_history = chat_history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": ""},
        ]
        yield chat_history

        # Stream response with pipeline info
        async for response in chat_with_pipeline(message, chat_history[:-2]):
            chat_history[-1]["content"] = response
            yield chat_history

    # Wire up the interface
    msg.submit(respond, [msg, chatbot], [chatbot]).then(
        lambda: "", None, [msg]  # Clear input after submit
    )
    submit_btn.click(respond, [msg, chatbot], [chatbot]).then(
        lambda: "", None, [msg]  # Clear input after submit
    )
    clear_btn.click(lambda: [], None, [chatbot])


if __name__ == "__main__":
    import os
    port = int(os.getenv("GRADIO_SERVER_PORT", "8001"))
    logger.info("starting_gradio_app", port=port)
    demo.launch(
        server_name="0.0.0.0",
        server_port=port,
        share=False,
    )
