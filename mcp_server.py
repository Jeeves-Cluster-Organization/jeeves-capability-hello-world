"""MCP tool server for hello-world onboarding chatbot.

Exposes 4 tools for the Rust kernel:
  - get_time: Get current date/time
  - list_tools: List available tools and capabilities
  - think_knowledge: Retrieve targeted knowledge sections based on intent
  - think_tools: Invoke tools based on classified topic

Run via stdio transport (kernel spawns this process):
    python mcp_server.py
"""

import sys
import os
import importlib.util

# Ensure the package is importable
sys.path.insert(0, os.path.dirname(__file__))

# Direct-load knowledge_base without triggering jeeves_capability_hello_world.__init__
# (which imports the deleted jeeves_core Python package)
_kb_spec = importlib.util.spec_from_file_location(
    "knowledge_base",
    os.path.join(os.path.dirname(__file__), "jeeves_capability_hello_world", "prompts", "knowledge_base.py"),
)
_knowledge_base = importlib.util.module_from_spec(_kb_spec)
_kb_spec.loader.exec_module(_knowledge_base)
get_knowledge_for_sections = _knowledge_base.get_knowledge_for_sections

from datetime import datetime
from jeeves_mcp_bridge import mcp_tool, McpToolServer


# =============================================================================
# Tool: get_time
# =============================================================================

@mcp_tool(
    name="get_time",
    description="Get current date and time (UTC)",
    parameters={"type": "object", "properties": {}},
)
def get_time(params: dict) -> dict:
    now = datetime.utcnow()
    return {
        "status": "success",
        "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "timezone": "UTC",
        "day_of_week": now.strftime("%A"),
        "iso_format": now.isoformat(),
    }


# =============================================================================
# Tool: list_tools
# =============================================================================

@mcp_tool(
    name="list_tools",
    description="List available tools and onboarding capabilities",
    parameters={"type": "object", "properties": {}},
)
def list_tools_fn(params: dict) -> dict:
    tools = [
        {
            "id": "get_time",
            "description": "Get the current date and time (UTC)",
            "parameters": {},
            "examples": ["What time is it?", "What's today's date?", "What day of the week is it?"],
        },
        {
            "id": "list_tools",
            "description": "List all available tools and onboarding capabilities",
            "parameters": {},
            "examples": ["What can you do?", "What tools do you have?", "Show me your capabilities"],
        },
    ]
    capabilities = [
        "Explain the Jeeves ecosystem architecture (3 layers)",
        "Describe jeeves-core (Rust micro-kernel)",
        "Describe jeeves-core (Python infrastructure & orchestration framework)",
        "Explain key concepts: Envelope, AgentConfig, Constitution R7",
        "Explain the 3-agent pipeline pattern",
        "Help with getting started and adding tools",
    ]
    return {"status": "success", "tools": tools, "capabilities": capabilities, "count": len(tools)}


# =============================================================================
# Tool: think_knowledge (deterministic agent via MCP)
# =============================================================================

# Intent → knowledge section mapping
SECTION_MAP = {
    "architecture": ["ecosystem_overview", "layer_details"],
    "concept": ["key_concepts", "code_examples"],
    "getting_started": ["hello_world_structure", "how_to_guides"],
    "component": ["ecosystem_overview", "layer_details"],
    "general": ["ecosystem_overview"],
}


@mcp_tool(
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
def think_knowledge(params: dict) -> dict:
    outputs = params.get("outputs", {})
    understand_output = outputs.get("understand", {})
    intent = understand_output.get("intent", "general")

    sections = SECTION_MAP.get(intent, ["ecosystem_overview"])
    targeted = get_knowledge_for_sections(sections)

    return {
        "information": {"has_data": True, "knowledge_retrieved": True},
        "targeted_knowledge": targeted,
    }


# =============================================================================
# Tool: think_tools (deterministic agent via MCP)
# =============================================================================

@mcp_tool(
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
def think_tools(params: dict) -> dict:
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
# Server
# =============================================================================

if __name__ == "__main__":
    server = McpToolServer()
    server.register(get_time)
    server.register(list_tools_fn)
    server.register(think_knowledge)
    server.register(think_tools)

    if "--http" in sys.argv:
        port = int(sys.argv[sys.argv.index("--http") + 1]) if len(sys.argv) > sys.argv.index("--http") + 1 else 9001
        server.run_http(port=port)
    else:
        server.run_stdio()
