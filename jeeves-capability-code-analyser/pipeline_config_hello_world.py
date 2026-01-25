"""
Hello World Pipeline Configuration - General Chatbot

3-Agent template: Understand → Think → Respond

This is a simplified, general-purpose chatbot capability that demonstrates
the core multi-agent orchestration pattern using jeeves-core.

Domain: General-purpose assistant (conversation, Q&A, web search)
Agents: 3 (vs 7 in full code-analysis capability)
Use case: Learning template, simple chatbot applications
"""

from typing import Any, Dict
from mission_system.contracts_core import (
    PipelineConfig,
    AgentConfig,
    ToolAccess,
    TerminalReason,
)


# ═══════════════════════════════════════════════════════════════
# AGENT HOOK FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def understand_pre_process(envelope: Any, agent: Any = None) -> Any:
    """
    Build context for Understand agent.

    Normalizes user input and prepares conversation history for LLM.
    """
    # Normalize input
    user_message = envelope.raw_input.strip()

    # Get conversation history (if available)
    conversation_history = envelope.metadata.get("conversation_history", [])

    # Build context for prompt template
    context = {
        "user_message": user_message,
        "conversation_history": conversation_history[-5:],  # Last 5 messages
        "system_identity": "Helpful AI Assistant",
        "capabilities": "conversation, web search, general knowledge",
    }

    envelope.metadata.update(context)
    return envelope


def understand_post_process(envelope: Any, output: Dict[str, Any], agent: Any = None) -> Any:
    """
    Process Understand agent output and prepare for Think agent.

    Determines if web search is needed and prepares action for Think agent.
    """
    needs_search = output.get("needs_search", False)
    search_query = output.get("search_query", "")

    # Prepare for Think agent
    if needs_search and search_query:
        # Think will execute web search
        envelope.outputs["think_plan"] = {
            "action": "web_search",
            "query": search_query
        }
    else:
        # Think will pass through (no tools needed)
        envelope.outputs["think_plan"] = {
            "action": "none",
            "query": None
        }

    return envelope


def think_pre_process(envelope: Any, agent: Any = None) -> Any:
    """
    Prepare Think agent for tool execution.

    Converts the plan from Understand into tool calls for executor.
    """
    think_plan = envelope.outputs.get("think_plan", {})

    action = think_plan.get("action", "none")
    query = think_plan.get("query")

    # Build tool calls for executor
    tool_calls = []
    if action == "web_search" and query:
        tool_calls.append({
            "name": "web_search",
            "params": {"query": query}
        })

    # Store for tool executor
    envelope.metadata["tool_calls"] = tool_calls

    return envelope


def think_post_process(envelope: Any, output: Dict[str, Any], agent: Any = None) -> Any:
    """
    Process Think agent output (tool results).

    Extracts web search results and sources for Respond agent.
    """
    tool_results = output.get("tool_results", [])

    # Extract search results
    search_results = []
    sources = []

    for result in tool_results:
        tool_name = result.get("tool", "")
        if tool_name == "web_search":
            result_data = result.get("result", {})
            # Handle both direct data and wrapped data
            data = result_data.get("data", result_data)

            search_results.extend(data.get("results", []))
            sources.extend(data.get("sources", []))

    # Store for Respond agent
    output["information"] = {
        "has_data": bool(search_results),
        "results": search_results[:5],  # Top 5 results
        "sources": sources[:5]
    }

    return envelope


def respond_pre_process(envelope: Any, agent: Any = None) -> Any:
    """
    Build context for Respond agent.

    Combines original message, intent, and search results for final response.
    """
    understand_output = envelope.outputs.get("understanding", {})
    think_output = envelope.outputs.get("think_results", {})

    user_message = envelope.raw_input
    intent = understand_output.get("intent", "chat")
    information = think_output.get("information", {})

    context = {
        "user_message": user_message,
        "intent": intent,
        "has_search_results": information.get("has_data", False),
        "search_results": str(information.get("results", []))[:5000],  # Cap to prevent prompt explosion
        "sources": information.get("sources", []),
        "task": "Craft a helpful, accurate response"
    }

    envelope.metadata.update(context)
    return envelope


def respond_post_process(envelope: Any, output: Dict[str, Any], agent: Any = None) -> Any:
    """
    Finalize response and terminate pipeline.

    Ensures response exists and marks pipeline as complete.
    """
    # Ensure response exists
    if "response" not in output:
        output["response"] = "I apologize, but I wasn't able to generate a response. Please try again."

    # Mark as complete
    envelope.terminated = True
    envelope.termination_reason = "completed"
    envelope.terminal_reason = TerminalReason.COMPLETED

    return envelope


# ═══════════════════════════════════════════════════════════════
# PIPELINE CONFIGURATION
# ═══════════════════════════════════════════════════════════════

GENERAL_CHATBOT_PIPELINE = PipelineConfig(
    name="general_chatbot",
    max_iterations=2,           # Simple queries don't need many iterations
    max_llm_calls=4,            # 2 LLM agents × 2 potential calls each
    max_agent_hops=10,
    enable_arbiter=False,       # No arbiter needed for simple flow
    clarification_resume_stage="understand",
    confirmation_resume_stage="think",
    agents=[
        # ─── Agent 1: Understand (LLM) ───
        # Analyzes user message, determines intent, decides if search needed
        AgentConfig(
            name="understand",
            stage_order=0,
            has_llm=True,                    # ✅ REAL LLM enabled
            model_role="planner",
            prompt_key="chatbot.understand",
            output_key="understanding",
            required_output_fields=["intent", "needs_search"],
            max_tokens=2000,
            temperature=0.3,                 # Low temp for consistent classification
            pre_process=understand_pre_process,
            post_process=understand_post_process,
            mock_handler=None,               # Mock only for tests
            default_next="think",
        ),

        # ─── Agent 2: Think (Tools, No LLM) ───
        # Executes tools (web search) when needed
        AgentConfig(
            name="think",
            stage_order=1,
            has_llm=False,                   # No LLM - pure tool execution
            has_tools=True,
            tool_access=ToolAccess.ALL,
            output_key="think_results",
            pre_process=think_pre_process,
            post_process=think_post_process,
            default_next="respond",
        ),

        # ─── Agent 3: Respond (LLM) ───
        # Synthesizes information and crafts final response
        AgentConfig(
            name="respond",
            stage_order=2,
            has_llm=True,                    # ✅ REAL LLM enabled
            model_role="planner",
            prompt_key="chatbot.respond",
            output_key="final_response",
            required_output_fields=["response"],
            max_tokens=3000,
            temperature=0.7,                 # Higher temp for natural responses
            pre_process=respond_pre_process,
            post_process=respond_post_process,
            mock_handler=None,               # Mock only for tests
            default_next="end",
        ),
    ],
)


# ═══════════════════════════════════════════════════════════════
# MODE REGISTRY
# ═══════════════════════════════════════════════════════════════

PIPELINE_MODES = {
    "general_chatbot": GENERAL_CHATBOT_PIPELINE,
    "hello_world": GENERAL_CHATBOT_PIPELINE,  # Alias for compatibility
}


def get_pipeline_for_mode(mode: str = "general_chatbot") -> PipelineConfig:
    """
    Get pipeline configuration for specified mode.

    Args:
        mode: Pipeline mode ("general_chatbot" or "hello_world")

    Returns:
        PipelineConfig for the specified mode

    Raises:
        ValueError: If mode is not recognized
    """
    if mode not in PIPELINE_MODES:
        raise ValueError(
            f"Unknown pipeline mode: {mode}. Available modes: {list(PIPELINE_MODES.keys())}"
        )

    return PIPELINE_MODES[mode]
