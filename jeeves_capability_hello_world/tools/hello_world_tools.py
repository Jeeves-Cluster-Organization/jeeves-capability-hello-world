"""
Tool implementations for Onboarding Chatbot.

This module provides 2 minimal tools:
1. get_time - Get current date/time (simple stateless example)
2. list_tools - Tool introspection for onboarding

Note: Web search was removed as onboarding uses embedded knowledge.
"""

from datetime import datetime
from typing import Dict, Any


# ═══════════════════════════════════════════════════════════════
# Tool 1: Get Time
# ═══════════════════════════════════════════════════════════════

def get_time() -> Dict[str, Any]:
    """
    Get current date and time.

    Simple stateless tool demonstrating basic tool pattern.
    Useful for queries like "What time is it?" or "What's today's date?"

    Returns:
        {
            "status": "success",
            "datetime": str,  # Full datetime string
            "date": str,      # Just the date
            "time": str,      # Just the time
            "timezone": str   # Timezone (UTC)
        }
    """
    now = datetime.utcnow()
    return {
        "status": "success",
        "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "timezone": "UTC",
        "day_of_week": now.strftime("%A"),
        "iso_format": now.isoformat()
    }


# ═══════════════════════════════════════════════════════════════
# Tool 2: List Tools
# ═══════════════════════════════════════════════════════════════

def list_tools() -> Dict[str, Any]:
    """
    List all available tools and onboarding capabilities.

    Useful for queries like "What can you do?" or "What tools do you have?"

    Returns:
        {
            "status": "success",
            "tools": [{"id": str, "description": str, "parameters": dict}, ...],
            "capabilities": [str, ...],
            "count": int
        }
    """
    tools = [
        {
            "id": "get_time",
            "description": "Get the current date and time (UTC)",
            "parameters": {},
            "examples": [
                "What time is it?",
                "What's today's date?",
                "What day of the week is it?"
            ]
        },
        {
            "id": "list_tools",
            "description": "List all available tools and onboarding capabilities",
            "parameters": {},
            "examples": [
                "What can you do?",
                "What tools do you have?",
                "Show me your capabilities"
            ]
        }
    ]

    capabilities = [
        "Explain the Jeeves ecosystem architecture (4 layers)",
        "Describe jeeves-core (Rust micro-kernel)",
        "Describe jeeves-infra (Python infrastructure)",
        "Describe mission_system (orchestration framework)",
        "Explain key concepts: Envelope, AgentConfig, Constitution R7",
        "Explain the 3-agent pipeline pattern",
        "Help with getting started and adding tools",
    ]

    return {
        "status": "success",
        "tools": tools,
        "capabilities": capabilities,
        "count": len(tools)
    }


# ═══════════════════════════════════════════════════════════════
# Exports
# ═══════════════════════════════════════════════════════════════

# Tool functions are exported directly
# Registration is handled by capability/wiring.py following Constitution R7

__all__ = [
    "get_time",
    "list_tools",
]
