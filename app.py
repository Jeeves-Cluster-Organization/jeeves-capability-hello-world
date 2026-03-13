"""Jeeves Onboarding Assistant — PyO3 entry point.

Single-process Gradio chatbot using the Rust kernel as a library.
Replaces: run.py + mcp_server.py + gradio_app.py (3 files, 3 processes).

Usage:
    python app.py

Open browser: http://localhost:8001
"""

import os
import sys
from datetime import datetime, timezone

# Direct-load knowledge_base without triggering package __init__
import importlib.util

_kb_spec = importlib.util.spec_from_file_location(
    "knowledge_base",
    os.path.join(os.path.dirname(__file__), "jeeves_capability_hello_world", "prompts", "knowledge_base.py"),
)
_knowledge_base = importlib.util.module_from_spec(_kb_spec)
_kb_spec.loader.exec_module(_knowledge_base)
get_knowledge_for_sections = _knowledge_base.get_knowledge_for_sections

from jeeves_core import PipelineRunner, tool

# =============================================================================
# Intent → knowledge section mapping
# =============================================================================

SECTION_MAP = {
    "architecture": ["ecosystem_overview", "layer_details"],
    "concept": ["key_concepts", "code_examples"],
    "getting_started": ["hello_world_structure", "how_to_guides"],
    "component": ["ecosystem_overview", "layer_details"],
    "general": ["ecosystem_overview"],
}

# =============================================================================
# Tools (registered as Python callables — no MCP subprocess needed)
# =============================================================================


@tool(name="get_time", description="Get current date and time (UTC)", parameters={"type": "object", "properties": {}})
def get_time(params):
    now = datetime.now(timezone.utc)
    return {
        "status": "success",
        "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "timezone": "UTC",
        "day_of_week": now.strftime("%A"),
        "iso_format": now.isoformat(),
    }


@tool(
    name="list_tools",
    description="List available tools and onboarding capabilities",
    parameters={"type": "object", "properties": {}},
)
def list_tools_fn(params):
    tools = [
        {
            "id": "get_time",
            "description": "Get the current date and time (UTC)",
            "parameters": {},
            "examples": ["What time is it?", "What's today's date?"],
        },
        {
            "id": "list_tools",
            "description": "List all available tools and capabilities",
            "parameters": {},
            "examples": ["What can you do?", "What tools do you have?"],
        },
    ]
    capabilities = [
        "Explain the Jeeves ecosystem architecture (3 layers)",
        "Describe jeeves-core (Rust micro-kernel)",
        "Explain key concepts: Envelope, PipelineConfig, routing",
        "Explain the multi-agent pipeline pattern",
        "Help with getting started and adding tools",
    ]
    return {"status": "success", "tools": tools, "capabilities": capabilities, "count": len(tools)}


@tool(
    name="think_knowledge",
    description="Retrieve targeted knowledge sections based on classified intent",
    parameters={
        "type": "object",
        "properties": {
            "raw_input": {"type": "string"},
            "outputs": {"type": "object"},
            "state": {"type": "object"},
            "metadata": {"type": "object"},
        },
    },
)
def think_knowledge(params):
    outputs = params.get("outputs", {})
    understand_output = outputs.get("understand", {})
    intent = understand_output.get("intent", "general")
    sections = SECTION_MAP.get(intent, ["ecosystem_overview"])
    targeted = get_knowledge_for_sections(sections)
    return {
        "information": {"has_data": True, "knowledge_retrieved": True},
        "targeted_knowledge": targeted,
    }


@tool(
    name="think_tools",
    description="Invoke tools based on classified topic from understand stage",
    parameters={
        "type": "object",
        "properties": {
            "raw_input": {"type": "string"},
            "outputs": {"type": "object"},
            "state": {"type": "object"},
            "metadata": {"type": "object"},
        },
    },
)
def think_tools(params):
    outputs = params.get("outputs", {})
    understand_output = outputs.get("understand", {})
    topic = understand_output.get("topic", "")
    intent = understand_output.get("intent", "general")

    tool_output = ""
    if any(kw in topic.lower() for kw in ("time", "date", "day", "clock")):
        result = get_time({})
        tool_output = (
            f"Current date: {result['date']}, time: {result['time']} {result['timezone']}, "
            f"day: {result['day_of_week']}"
        )
    elif any(kw in topic.lower() for kw in ("tool", "capability", "what can")):
        result = list_tools_fn({})
        tools_desc = ", ".join(t["id"] for t in result["tools"])
        caps_desc = "; ".join(result["capabilities"][:3])
        tool_output = f"Available tools: {tools_desc}. Capabilities: {caps_desc}"
    elif intent == "general":
        tool_output = "No specific tools needed for this query."

    return {
        "information": {"has_data": True, "tools_executed": True},
        "targeted_knowledge": tool_output or "No tool results.",
    }


# =============================================================================
# Runner
# =============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

runner = PipelineRunner.from_json(
    pipeline_path=os.path.join(SCRIPT_DIR, "pipeline.json"),
    prompts_dir=os.path.join(SCRIPT_DIR, "prompts"),
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    openai_base_url=os.getenv("OPENAI_BASE_URL"),
)
runner.register_tool(get_time)
runner.register_tool(list_tools_fn)
runner.register_tool(think_knowledge)
runner.register_tool(think_tools)

# =============================================================================
# Gradio UI
# =============================================================================

import gradio as gr


def chat(message, history):
    """Streaming chat handler — yields incremental response text."""
    for event in runner.stream(message, user_id="gradio_user"):
        if event["type"] == "delta":
            yield event["content"]


if __name__ == "__main__":
    port = int(os.getenv("GRADIO_SERVER_PORT", "8001"))
    demo = gr.ChatInterface(chat, title="Jeeves Onboarding Assistant")
    demo.launch(server_name="0.0.0.0", server_port=port, share=False)
