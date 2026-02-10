"""
Jeeves Onboarding Assistant - Gradio Application

3-agent pipeline (Understand -> Think -> Respond) that explains the Jeeves ecosystem.
Shows intent classification and knowledge retrieval as the pipeline progresses.

Features:
- Intent classification: architecture, concept, getting_started, component, general
- Targeted knowledge retrieval based on classified intent
- Streaming responses with pipeline visibility
- SQLite-backed in-dialogue memory (session state + message persistence)
- Per-tab session isolation

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
import os
import uuid
from typing import List, Generator

# =============================================================================
# LLM CONFIGURATION - Configure for Ollama or other providers
# =============================================================================

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"
DEFAULT_OLLAMA_MODEL = "llama3.2"

os.environ.setdefault("JEEVES_LLM_ADAPTER", "openai_http")
os.environ.setdefault("JEEVES_LLM_BASE_URL", DEFAULT_OLLAMA_BASE_URL)
os.environ.setdefault("JEEVES_LLM_MODEL", DEFAULT_OLLAMA_MODEL)
os.environ.setdefault("JEEVES_LLM_API_KEY", "ollama")

os.environ.setdefault("JEEVES_LLM_UNDERSTAND_MODEL", DEFAULT_OLLAMA_MODEL)
os.environ.setdefault("JEEVES_LLM_RESPOND_MODEL", DEFAULT_OLLAMA_MODEL)

# =============================================================================

# Constitution R7: Register capability FIRST, before infrastructure imports
from jeeves_capability_hello_world import register_capability
register_capability()

# Capability layer imports only
from jeeves_capability_hello_world.orchestration import ChatbotService
from jeeves_capability_hello_world.capability.wiring import create_hello_world_from_app_context

# Import prompts to register them (the @register_prompt decorators run on import)
import jeeves_capability_hello_world.prompts.chatbot.understand  # noqa
import jeeves_capability_hello_world.prompts.chatbot.respond  # noqa
import jeeves_capability_hello_world.prompts.chatbot.respond_streaming  # noqa

logger = structlog.get_logger()

# Global service (singleton — shared across all sessions)
_service: ChatbotService = None


def get_or_create_service() -> ChatbotService:
    """Get or create the chatbot service via capability layer."""
    global _service

    if _service is None:
        logger.info("initializing_chatbot_service")

        from jeeves_infra.bootstrap import create_app_context
        app_context = create_app_context()

        _service = create_hello_world_from_app_context(app_context)

        logger.info("chatbot_service_ready",
                    pipeline="onboarding_chatbot",
                    agents=3,
                    has_kernel_client=app_context.kernel_client is not None)

    return _service


def format_agent_output(agent_name: str, data: dict, status: str) -> str:
    """Format agent output for display."""
    if status == "completed":
        if agent_name == "understand":
            intent = data.get("intent", "")
            topic = data.get("topic", "")
            if intent and topic:
                return f"*{intent}: {topic}*"
            elif intent:
                return f"*{intent}*"
        elif agent_name == "think":
            info = data.get("information", {})
            if info.get("knowledge_retrieved"):
                return "*Knowledge retrieved*"
    return ""


async def chat_with_pipeline(message: str, history: List[List], session_id: str) -> Generator:
    """Handle user message showing full pipeline progress."""
    service = get_or_create_service()
    user_id = "gradio-user"

    logger.info("message_received", message=message, session_id=session_id)

    pipeline_status = ""
    current_response = ""

    try:
        # Build conversation history from Gradio format
        conversation_history = []
        for msg in history:
            if isinstance(msg, dict):
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get('type') == 'text':
                            content = item.get('text', '')
                            break
                if content:
                    if role == 'assistant' and "---" in str(content):
                        content = str(content).split("---")[-1].strip()
                    conversation_history.append({"role": role, "content": str(content)})
            elif isinstance(msg, (list, tuple)) and len(msg) >= 2:
                user_msg, assistant_msg = msg[0], msg[1]
                if user_msg:
                    conversation_history.append({"role": "user", "content": str(user_msg)})
                if assistant_msg:
                    clean_msg = str(assistant_msg)
                    if "---" in clean_msg:
                        clean_msg = clean_msg.split("---")[-1].strip()
                    conversation_history.append({"role": "assistant", "content": clean_msg})

        metadata = {
            "conversation_history": conversation_history[-5:]
        }

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

                if status == "completed":
                    output_text = format_agent_output(agent_name, data, "completed")
                    if output_text:
                        if agent_name == "understand":
                            pipeline_status = output_text + " "
                        elif agent_name == "think":
                            pipeline_status += output_text + "\n\n"

            elif event_type == "token" and not getattr(event, 'debug', False):
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
        yield f"An unexpected error occurred: {str(e)}"


# =============================================================================
# LLM Settings Management
# =============================================================================

def get_current_llm_config() -> dict:
    return {
        "base_url": os.getenv("JEEVES_LLM_BASE_URL", DEFAULT_OLLAMA_BASE_URL),
        "model": os.getenv("JEEVES_LLM_MODEL", DEFAULT_OLLAMA_MODEL),
        "api_key": os.getenv("JEEVES_LLM_API_KEY", "ollama"),
    }


def update_llm_config(base_url: str, model: str, api_key: str) -> str:
    global _service

    os.environ["JEEVES_LLM_BASE_URL"] = base_url
    os.environ["JEEVES_LLM_MODEL"] = model
    os.environ["JEEVES_LLM_API_KEY"] = api_key
    os.environ["JEEVES_LLM_UNDERSTAND_MODEL"] = model
    os.environ["JEEVES_LLM_RESPOND_MODEL"] = model

    _service = None

    logger.info("llm_config_updated", base_url=base_url, model=model)
    return f"Configuration updated. Using model `{model}` at `{base_url}`"


# =============================================================================
# Gradio UI
# =============================================================================

with gr.Blocks(title="Jeeves Onboarding Assistant") as demo:
    gr.Markdown("# Jeeves Onboarding Assistant")

    # Per-tab session ID (unique per browser tab)
    session_id_state = gr.State(lambda: str(uuid.uuid4()))

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

    async def respond(message: str, chat_history: List, session_id: str):
        """Handle message and update chat with pipeline visibility."""
        if not message.strip():
            yield chat_history
            return

        chat_history = chat_history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": ""},
        ]
        yield chat_history

        async for response in chat_with_pipeline(message, chat_history[:-2], session_id):
            chat_history[-1]["content"] = response
            yield chat_history

    # Wire up the interface with per-tab session_id
    msg.submit(respond, [msg, chatbot, session_id_state], [chatbot]).then(
        lambda: "", None, [msg]
    )
    submit_btn.click(respond, [msg, chatbot, session_id_state], [chatbot]).then(
        lambda: "", None, [msg]
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
