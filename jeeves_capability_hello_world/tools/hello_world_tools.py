"""
General-purpose tool implementations for Hello World chatbot.

This module provides 3 minimal tools:
1. web_search - Search the web for current information
2. get_time - Get current date/time (simple stateless example)
3. list_tools - Tool introspection
"""

import os
from datetime import datetime
from typing import Dict, Any, List


# ═══════════════════════════════════════════════════════════════
# Tool 1: Web Search
# ═══════════════════════════════════════════════════════════════

async def web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Search the web for current information.

    This is a template implementation. In production, integrate with:
    - Google Custom Search API (recommended)
    - Serper API
    - DuckDuckGo

    Args:
        query: Search query string
        max_results: Maximum number of results to return (default: 5)

    Returns:
        {
            "status": "success"|"error",
            "results": [{"title": str, "snippet": str, "url": str}, ...],
            "sources": [str, ...],
            "query": str
        }
    """
    # Check for Google Custom Search API credentials
    google_api_key = os.getenv("GOOGLE_API_KEY")
    google_cx = os.getenv("GOOGLE_CX")

    if google_api_key and google_cx:
        # TODO: Implement Google Custom Search
        # Example:
        # import httpx
        # url = f"https://www.googleapis.com/customsearch/v1?key={google_api_key}&cx={google_cx}&q={query}"
        # async with httpx.AsyncClient() as client:
        #     response = await client.get(url)
        #     data = response.json()
        #     results = [
        #         {
        #             "title": item["title"],
        #             "snippet": item["snippet"],
        #             "url": item["link"]
        #         }
        #         for item in data.get("items", [])[:max_results]
        #     ]
        #     return {
        #         "status": "success",
        #         "results": results,
        #         "sources": [r["url"] for r in results],
        #         "query": query
        #     }
        pass

    # Fallback: Mock response for development
    # Replace this with real implementation
    return {
        "status": "success",
        "results": [
            {
                "title": f"Search result for: {query}",
                "snippet": f"This is a mock search result for '{query}'. In production, this would return real web search results from Google, Serper, or DuckDuckGo.",
                "url": "https://example.com"
            }
        ],
        "sources": ["https://example.com"],
        "query": query,
        "note": "This is a mock result. Set GOOGLE_API_KEY and GOOGLE_CX environment variables to enable real web search."
    }


# ═══════════════════════════════════════════════════════════════
# Tool 2: Get Time
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
# Tool 3: List Tools
# ═══════════════════════════════════════════════════════════════

def list_tools() -> Dict[str, Any]:
    """
    List all available tools for introspection.

    Useful for queries like "What can you do?" or "What tools do you have?"

    Returns:
        {
            "status": "success",
            "tools": [{"id": str, "description": str, "parameters": dict}, ...],
            "count": int
        }
    """
    tools = [
        {
            "id": "web_search",
            "description": "Search the web for current information, news, and facts",
            "parameters": {
                "query": "string (required) - The search query",
                "max_results": "int (optional) - Maximum number of results (default: 5)"
            },
            "examples": [
                "What's the weather in Paris?",
                "Latest AI news",
                "Who won the 2024 World Series?"
            ]
        },
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
            "description": "List all available tools and their capabilities",
            "parameters": {},
            "examples": [
                "What can you do?",
                "What tools do you have?",
                "Show me your capabilities"
            ]
        }
    ]

    return {
        "status": "success",
        "tools": tools,
        "count": len(tools)
    }


# ═══════════════════════════════════════════════════════════════
# Exports
# ═══════════════════════════════════════════════════════════════

# Tool functions are exported directly
# Registration is handled by tools/registration.py following Constitution R7

__all__ = [
    "web_search",
    "get_time",
    "list_tools",
    "print_setup_instructions",
]


# ═══════════════════════════════════════════════════════════════
# Helper: Setup Instructions
# ═══════════════════════════════════════════════════════════════

def print_setup_instructions():
    """Print instructions for setting up web search."""
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║  Hello World Chatbot - Web Search Setup                   ║
    ╚════════════════════════════════════════════════════════════╝

    To enable real web search, choose one option:

    Option 1: Google Custom Search API (Recommended)
    ─────────────────────────────────────────────────
    1. Go to: https://developers.google.com/custom-search
    2. Create a Custom Search Engine
    3. Get your API key and Search Engine ID (CX)
    4. Set environment variables:
       export GOOGLE_API_KEY="your-api-key"
       export GOOGLE_CX="your-search-engine-id"

    Free tier: 100 queries/day

    Option 2: Serper API
    ────────────────────
    1. Go to: https://serper.dev
    2. Sign up and get API key
    3. Set environment variable:
       export SERPER_API_KEY="your-api-key"

    Free tier: 2,500 queries

    Option 3: DuckDuckGo (No API key needed)
    ────────────────────────────────────────
    Install package: pip install duckduckgo-search
    No configuration needed, but results may be less structured

    ══════════════════════════════════════════════════════════════

    Without web search credentials, the chatbot will return mock
    results for development purposes.
    """)


if __name__ == "__main__":
    # Print setup instructions when run directly
    print_setup_instructions()
