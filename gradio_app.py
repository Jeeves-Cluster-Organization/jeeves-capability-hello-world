"""
Jeeves Onboarding Assistant - Gradio Application (HTTP API)

Communicates with the Rust kernel via HTTP instead of the Python jeeves_core package.
Supports both buffered and streaming modes.

Usage:
    # Start the Rust kernel with hello-world config (see run.py)
    # Then start the Gradio UI:
    python gradio_app_http.py

Open browser: http://localhost:8001
"""

import gradio as gr
import json
import os
import uuid
import requests
from typing import List, Generator

# =============================================================================
# CONFIGURATION
# =============================================================================

KERNEL_URL = os.getenv("JEEVES_KERNEL_URL", "http://localhost:8080")
PIPELINE_CONFIG_PATH = os.getenv("JEEVES_PIPELINE_CONFIG", os.path.join(os.path.dirname(__file__), "pipeline.json"))

# Load pipeline config once
with open(PIPELINE_CONFIG_PATH) as f:
    PIPELINE_CONFIG = json.load(f)


# =============================================================================
# Kernel HTTP Client
# =============================================================================

def chat_buffered(message: str, session_id: str, metadata: dict = None) -> dict:
    """Send a message to the kernel and get the full response."""
    payload = {
        "pipeline_config": PIPELINE_CONFIG,
        "input": message,
        "user_id": "gradio_user",
        "session_id": session_id,
    }
    if metadata:
        payload["metadata"] = metadata

    resp = requests.post(
        f"{KERNEL_URL}/api/v1/chat/messages",
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def chat_streaming(message: str, session_id: str, metadata: dict = None) -> Generator:
    """Send a message to the kernel and stream SSE events."""
    payload = {
        "pipeline_config": PIPELINE_CONFIG,
        "input": message,
        "user_id": "gradio_user",
        "session_id": session_id,
    }
    if metadata:
        payload["metadata"] = metadata

    resp = requests.post(
        f"{KERNEL_URL}/api/v1/chat/stream",
        json=payload,
        stream=True,
        timeout=120,
    )
    resp.raise_for_status()

    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue
        if line.startswith("data: "):
            data = line[6:]
            if data.strip() == "[DONE]":
                break
            try:
                yield json.loads(data)
            except json.JSONDecodeError:
                continue


# =============================================================================
# Helpers
# =============================================================================

def format_agent_status(agent_name: str, data: dict) -> str:
    """Format agent completion for pipeline status display."""
    if agent_name == "understand":
        intent = data.get("intent", "")
        topic = data.get("topic", "")
        if intent and topic:
            return f"*{intent}: {topic}*"
        elif intent:
            return f"*{intent}*"
    elif agent_name in ("think_knowledge", "think_tools"):
        info = data.get("information", {})
        if info.get("knowledge_retrieved"):
            return "*Knowledge retrieved*"
        elif info.get("tools_executed"):
            return "*Tools executed*"
    return ""


def extract_conversation_history(history: list) -> list:
    """Extract conversation history from Gradio chat format."""
    conversation = []
    for msg in history:
        if isinstance(msg, dict):
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        content = item.get("text", "")
                        break
            if content:
                if role == "assistant" and "---" in str(content):
                    content = str(content).split("---")[-1].strip()
                conversation.append({"role": role, "content": str(content)})
        elif isinstance(msg, (list, tuple)) and len(msg) >= 2:
            user_msg, assistant_msg = msg[0], msg[1]
            if user_msg:
                conversation.append({"role": "user", "content": str(user_msg)})
            if assistant_msg:
                clean_msg = str(assistant_msg)
                if "---" in clean_msg:
                    clean_msg = clean_msg.split("---")[-1].strip()
                conversation.append({"role": "assistant", "content": clean_msg})
    return conversation


# =============================================================================
# Chat handlers
# =============================================================================

def chat_with_pipeline_buffered(message: str, history: list, session_id: str) -> str:
    """Handle user message with buffered kernel response."""
    conversation_history = extract_conversation_history(history)
    metadata = {"conversation_history": conversation_history[-5:]}

    try:
        result = chat_buffered(message, session_id, metadata)
        outputs = result.get("outputs", {})

        # Build pipeline status
        pipeline_status = ""
        understand = outputs.get("understand", {})
        if understand:
            status = format_agent_status("understand", understand)
            if status:
                pipeline_status += status + " "

        think = outputs.get("think_results", {})
        if think:
            status = format_agent_status(
                "think_knowledge" if think.get("information", {}).get("knowledge_retrieved") else "think_tools",
                think,
            )
            if status:
                pipeline_status += status + "\n\n"

        # Extract response
        respond_output = outputs.get("respond", {})
        response = respond_output.get("response", "")
        if not response:
            response = str(respond_output) if respond_output else "No response generated."

        return pipeline_status + response

    except requests.exceptions.ConnectionError:
        return "Error: Cannot connect to kernel at {}. Is it running?".format(KERNEL_URL)
    except Exception as e:
        return f"Error: {e}"


def chat_with_pipeline_streaming(message: str, history: list, session_id: str) -> Generator:
    """Handle user message with streaming kernel response."""
    conversation_history = extract_conversation_history(history)
    metadata = {"conversation_history": conversation_history[-5:]}

    pipeline_status = ""
    current_response = ""

    try:
        for event in chat_streaming(message, session_id, metadata):
            event_type = event.get("type", "")

            if event_type == "stage_started":
                pass  # Wait for stage_completed

            elif event_type == "stage_completed":
                stage = event.get("stage", "")
                # Status will be built from outputs at done

            elif event_type == "delta":
                content = event.get("content", "")
                current_response += content
                yield pipeline_status + current_response

            elif event_type == "done":
                if not current_response:
                    # Fallback: extract from final outputs
                    current_response = "Pipeline completed."
                yield pipeline_status + current_response
                return

            elif event_type == "error":
                yield f"Error: {event.get('message', 'Unknown error')}"
                return

    except requests.exceptions.ConnectionError:
        yield "Error: Cannot connect to kernel at {}. Is it running?".format(KERNEL_URL)
    except Exception as e:
        yield f"Error: {e}"


# =============================================================================
# Gradio UI
# =============================================================================

# Use streaming if available, fall back to buffered
USE_STREAMING = os.getenv("JEEVES_STREAMING", "false").lower() == "true"

with gr.Blocks(title="Jeeves Onboarding Assistant") as demo:
    gr.Markdown("# Jeeves Onboarding Assistant")
    gr.Markdown(f"*Kernel: `{KERNEL_URL}` | Mode: {'streaming' if USE_STREAMING else 'buffered'}*")

    session_id_state = gr.State(lambda: str(uuid.uuid4()))

    chatbot = gr.Chatbot(label="Conversation", height=450)

    with gr.Row():
        msg = gr.Textbox(
            label="Your message",
            placeholder="Ask about the Jeeves ecosystem...",
            scale=4,
            show_label=False,
        )
        submit_btn = gr.Button("Send", variant="primary", scale=1)

    with gr.Row():
        clear_btn = gr.Button("Clear Chat")

    if USE_STREAMING:
        async def respond(message: str, chat_history: list, session_id: str):
            if not message.strip():
                yield chat_history
                return
            chat_history = chat_history + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": ""},
            ]
            yield chat_history
            for response in chat_with_pipeline_streaming(message, chat_history[:-2], session_id):
                chat_history[-1]["content"] = response
                yield chat_history
    else:
        async def respond(message: str, chat_history: list, session_id: str):
            if not message.strip():
                yield chat_history
                return
            chat_history = chat_history + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": "Thinking..."},
            ]
            yield chat_history
            response = chat_buffered_wrapper(message, chat_history[:-2], session_id)
            chat_history[-1]["content"] = response
            yield chat_history

        def chat_buffered_wrapper(message, history, session_id):
            return chat_with_pipeline_buffered(message, history, session_id)

    msg.submit(respond, [msg, chatbot, session_id_state], [chatbot]).then(
        lambda: "", None, [msg]
    )
    submit_btn.click(respond, [msg, chatbot, session_id_state], [chatbot]).then(
        lambda: "", None, [msg]
    )
    clear_btn.click(lambda: [], None, [chatbot])


if __name__ == "__main__":
    port = int(os.getenv("GRADIO_SERVER_PORT", "8001"))
    print(f"Starting Gradio on port {port}...")
    demo.launch(server_name="0.0.0.0", server_port=port, share=False)
