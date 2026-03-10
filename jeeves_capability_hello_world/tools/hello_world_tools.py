"""Tool implementations for Onboarding Chatbot.

Two minimal tools demonstrating the @tool decorator pattern:
1. get_time - Get current date/time (simple stateless example)
2. list_tools - Tool introspection for onboarding
"""

from datetime import datetime
from typing import Dict, Any

from jeeves_core.tools import tool


@tool(description="Get current date and time", category="standalone", risk="read_only/low")
def get_time() -> Dict[str, Any]:
    """Get current date and time (UTC)."""
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


@tool(
    description="List available tools and onboarding capabilities",
    category="standalone",
    risk="read_only/low",
)
def list_tools() -> Dict[str, Any]:
    """List all available tools and onboarding capabilities."""
    tools = [
        {
            "id": "get_time",
            "description": "Get the current date and time (UTC)",
            "parameters": {},
            "examples": [
                "What time is it?",
                "What's today's date?",
                "What day of the week is it?",
            ],
        },
        {
            "id": "list_tools",
            "description": "List all available tools and onboarding capabilities",
            "parameters": {},
            "examples": [
                "What can you do?",
                "What tools do you have?",
                "Show me your capabilities",
            ],
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

    return {
        "status": "success",
        "tools": tools,
        "capabilities": capabilities,
        "count": len(tools),
    }


__all__ = [
    "get_time",
    "list_tools",
]
