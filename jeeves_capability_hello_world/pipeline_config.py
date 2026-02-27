"""
Hello World Pipeline Configuration - Onboarding Chatbot

4-Agent pipeline with circular routing:
  Understand → Think-Knowledge ─┐
                                ├→ Respond ──┐
  Understand → Think-Tools ─────┘            │
       ▲                                     │
       └─── (needs_more_context=true) ───────┘

Routing is declarative — the Rust kernel evaluates RoutingRule conditions.
Tight bounds guarantee termination:
  - max_llm_calls=6 → max 3 loops (2 LLM calls per loop)
  - max_agent_hops=12 → max 3 loops (4 hops per loop)
  - max_iterations=3 → explicit iteration cap
"""

from typing import Any, Dict
from jeeves_core.protocols import (
    PipelineConfig,
    AgentConfig,
    RoutingRule,
    ToolAccess,
    TerminalReason,
)
from jeeves_core.protocols import AgentOutputMode, TokenStreamMode, GenerationParams


# =============================================================================
# AGENT HOOK FUNCTIONS
# =============================================================================

def _format_conversation_history(history: list) -> str:
    """Format conversation history as readable text for prompts."""
    if not history:
        return "No previous conversation."
    lines = []
    for msg in history[-5:]:
        role = msg.get("role", "user").capitalize()
        content = msg.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


async def understand_pre_process(envelope: Any, agent: Any = None) -> Any:
    """Build context for Understand agent."""
    user_message = envelope.raw_input.strip()
    conversation_history = envelope.metadata.get("conversation_history", [])
    formatted_history = _format_conversation_history(conversation_history)

    session_context = envelope.metadata.get("session_context", {})

    context = {
        "user_message": user_message,
        "conversation_history": formatted_history,
        "conversation_summary": session_context.get("conversation_summary", ""),
        "turn_count": session_context.get("turn_count", 0),
        "is_retry": envelope.metadata.get("_routing_loop_count", 0) > 0,
        "previous_response": "",
    }

    # On retry loops, include what the previous respond agent produced
    prev_response = envelope.outputs.get("final_response", {})
    if isinstance(prev_response, dict) and prev_response.get("response"):
        context["previous_response"] = prev_response["response"]

    envelope.metadata.update(context)
    return envelope


async def understand_post_process(envelope: Any, output: Dict[str, Any], agent: Any = None) -> Any:
    """Process Understand output — map intent to knowledge sections."""
    intent = output.get("intent", "general")
    topic = output.get("topic", "")

    envelope.metadata["classified_intent"] = intent
    envelope.metadata["classified_topic"] = topic

    knowledge_sections = _get_knowledge_sections_for_intent(intent, topic)
    envelope.metadata["knowledge_sections"] = knowledge_sections

    return envelope


def _get_knowledge_sections_for_intent(intent: str, topic: str) -> list:
    """Map intent to relevant knowledge base sections."""
    section_map = {
        "architecture": ["ecosystem_overview", "layer_details"],
        "concept": ["key_concepts", "code_examples"],
        "getting_started": ["hello_world_structure", "how_to_guides"],
        "component": ["ecosystem_overview", "layer_details"],
        "general": ["ecosystem_overview"],
    }
    return section_map.get(intent, ["ecosystem_overview"])


async def think_knowledge_pre_process(envelope: Any, agent: Any = None) -> Any:
    """Retrieve targeted knowledge sections (no LLM, no tools)."""
    from jeeves_capability_hello_world.prompts.knowledge_base import get_knowledge_for_sections

    knowledge_sections = envelope.metadata.get("knowledge_sections", ["ecosystem_overview"])
    targeted_knowledge = get_knowledge_for_sections(knowledge_sections)

    envelope.metadata["targeted_knowledge"] = targeted_knowledge
    return envelope


async def think_knowledge_post_process(envelope: Any, output: Dict[str, Any], agent: Any = None) -> Any:
    """Mark knowledge retrieval results."""
    output["information"] = {"has_data": True, "knowledge_retrieved": True}
    return envelope


async def think_tools_pre_process(envelope: Any, agent: Any = None) -> Any:
    """Invoke tools based on classified topic."""
    from jeeves_capability_hello_world.tools.hello_world_tools import get_time, list_tools

    topic = envelope.metadata.get("classified_topic", "")
    intent = envelope.metadata.get("classified_intent", "general")

    tool_output = ""
    if any(kw in topic.lower() for kw in ("time", "date", "day", "clock")):
        result = get_time()
        tool_output = (
            f"Current date: {result['date']}, time: {result['time']} {result['timezone']}, "
            f"day: {result['day_of_week']}"
        )
    elif any(kw in topic.lower() for kw in ("tool", "capability", "what can")):
        result = list_tools()
        tools_desc = ", ".join(t["id"] for t in result["tools"])
        caps_desc = "; ".join(result["capabilities"][:3])
        tool_output = f"Available tools: {tools_desc}. Capabilities: {caps_desc}"
    elif intent == "general":
        tool_output = "No specific tools needed for this query."

    envelope.metadata["targeted_knowledge"] = tool_output or "No tool results."
    return envelope


async def think_tools_post_process(envelope: Any, output: Dict[str, Any], agent: Any = None) -> Any:
    """Mark tool execution results."""
    output["information"] = {"has_data": True, "tools_executed": True}
    return envelope


async def respond_pre_process(envelope: Any, agent: Any = None) -> Any:
    """Build context for Respond agent from upstream outputs."""
    understand_output = envelope.outputs.get("understanding", {})

    user_message = envelope.raw_input
    intent = envelope.metadata.get("classified_intent", understand_output.get("intent", "general"))
    topic = envelope.metadata.get("classified_topic", understand_output.get("topic", ""))

    conversation_history = envelope.metadata.get("conversation_history", [])
    if isinstance(conversation_history, str):
        formatted_history = conversation_history
    else:
        formatted_history = _format_conversation_history(conversation_history)

    targeted_knowledge = envelope.metadata.get("targeted_knowledge", "")

    session_context = envelope.metadata.get("session_context", {})

    context = {
        "user_message": user_message,
        "intent": intent,
        "topic": topic,
        "conversation_history": formatted_history,
        "conversation_summary": session_context.get("conversation_summary", ""),
        "turn_count": session_context.get("turn_count", 0),
        "targeted_knowledge": targeted_knowledge,
        "task": "Craft a helpful, accurate response about the Jeeves ecosystem",
    }

    envelope.metadata.update(context)
    return envelope


async def respond_post_process(envelope: Any, output: Dict[str, Any], agent: Any = None) -> Any:
    """Check if response is complete or needs another loop."""
    loop_count = envelope.metadata.get("_routing_loop_count", 0)

    # If LLM signals more context needed AND we haven't looped too much, loop back
    if output.get("needs_more_context") and loop_count < 2:
        envelope.metadata["_routing_loop_count"] = loop_count + 1
        # Don't terminate — kernel routing rule will send back to understand
        return envelope

    # Normal termination
    if "response" not in output:
        output["response"] = "I apologize, but I wasn't able to generate a response. Please try again."

    envelope.terminated = True
    envelope.termination_reason = "completed"
    envelope.terminal_reason = TerminalReason.COMPLETED
    return envelope


# =============================================================================
# PIPELINE CONFIGURATION
# =============================================================================

ONBOARDING_CHATBOT_PIPELINE = PipelineConfig(
    name="onboarding_chatbot",
    max_iterations=3,           # Max 3 understand→think→respond loops
    max_llm_calls=6,            # 2 LLM agents × 3 loops
    max_agent_hops=12,          # 4 hops per loop × 3 loops
    clarification_resume_stage="understand",
    confirmation_resume_stage="think_knowledge",
    agents=[
        # ─── Agent 1: Understand (LLM) ───
        AgentConfig(
            name="understand",
            stage_order=0,
            has_llm=True,
            model_role="planner",
            prompt_key="chatbot.understand",
            output_key="understanding",
            required_output_fields=["intent", "topic"],
            max_tokens=4000,
            temperature=0.3,
            pre_process=understand_pre_process,
            post_process=understand_post_process,
            routing_rules=[
                RoutingRule(condition="intent", value="getting_started", target="think_tools"),
                RoutingRule(condition="intent", value="general", target="think_tools"),
            ],
            default_next="think_knowledge",
            error_next="respond",
        ),

        # ─── Agent 2a: Think-Knowledge (No LLM, No Tools) ───
        AgentConfig(
            name="think_knowledge",
            stage_order=1,
            has_llm=False,
            has_tools=False,
            output_key="think_results",
            pre_process=think_knowledge_pre_process,
            post_process=think_knowledge_post_process,
            default_next="respond",
            error_next="respond",
        ),

        # ─── Agent 2b: Think-Tools (No LLM, Has Tools) ───
        AgentConfig(
            name="think_tools",
            stage_order=2,
            has_llm=False,
            has_tools=True,
            tool_access=ToolAccess.ALL,
            output_key="think_results",
            pre_process=think_tools_pre_process,
            post_process=think_tools_post_process,
            default_next="respond",
            error_next="respond",
        ),

        # ─── Agent 3: Respond (LLM, Streaming) ───
        AgentConfig(
            name="respond",
            stage_order=3,
            has_llm=True,
            model_role="planner",
            prompt_key="chatbot.respond",
            output_key="final_response",
            required_output_fields=["response"],
            max_tokens=4000,
            temperature=0.5,
            generation=GenerationParams(
                stop=["\n\n\n", "User:", "Question:"],
                repeat_penalty=1.15,
            ),
            pre_process=respond_pre_process,
            post_process=respond_post_process,
            routing_rules=[
                RoutingRule(condition="needs_more_context", value="true", target="understand"),
            ],
            default_next="end",
            error_next="end",
            output_mode=AgentOutputMode.TEXT,
            token_stream=TokenStreamMode.AUTHORITATIVE,
            streaming_prompt_key="chatbot.respond_streaming",
        ),
    ],
)


# =============================================================================
# MODE REGISTRY
# =============================================================================

PIPELINE_MODES = {
    "onboarding_chatbot": ONBOARDING_CHATBOT_PIPELINE,
    "hello_world": ONBOARDING_CHATBOT_PIPELINE,
}


def get_pipeline_for_mode(mode: str = "onboarding_chatbot") -> PipelineConfig:
    if mode not in PIPELINE_MODES:
        raise ValueError(
            f"Unknown pipeline mode: {mode}. Available modes: {list(PIPELINE_MODES.keys())}"
        )
    return PIPELINE_MODES[mode]
