"""
Hello World Pipeline Configuration - Onboarding Chatbot

3-Agent template: Understand → Think → Respond

This is an onboarding assistant capability that explains the Jeeves ecosystem
to newcomers, demonstrating the core multi-agent orchestration pattern.

Domain: Onboarding assistant (ecosystem explanation, concept clarification)
Agents: 3 (minimal pipeline for onboarding chatbot)
Use case: Learning template, ecosystem onboarding
"""

from typing import Any, Dict
from jeeves_infra.protocols import (
    PipelineConfig,
    AgentConfig,
    ToolAccess,
    TerminalReason,
)
from jeeves_infra.protocols import AgentOutputMode, TokenStreamMode, GenerationParams


# ═══════════════════════════════════════════════════════════════
# AGENT HOOK FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def _format_conversation_history(history: list) -> str:
    """Format conversation history as readable text for prompts."""
    if not history:
        return "No previous conversation."

    lines = []
    for msg in history[-5:]:  # Last 5 messages
        role = msg.get("role", "user").capitalize()
        content = msg.get("content", "")
        lines.append(f"{role}: {content}")

    return "\n".join(lines)


async def understand_pre_process(envelope: Any, agent: Any = None) -> Any:
    """
    Build context for Understand agent.

    Normalizes user input and prepares conversation history for LLM.
    """
    # Normalize input
    user_message = envelope.raw_input.strip()

    # Get conversation history (if available) and format as text
    conversation_history = envelope.metadata.get("conversation_history", [])
    formatted_history = _format_conversation_history(conversation_history)

    # Inject session context from in-dialogue memory
    session_context = envelope.metadata.get("session_context", {})
    conversation_summary = session_context.get("conversation_summary", "")

    # Build context for prompt template
    context = {
        "user_message": user_message,
        "conversation_history": formatted_history,
        "conversation_summary": conversation_summary,
        "turn_count": session_context.get("turn_count", 0),
        "system_identity": "Jeeves Onboarding Assistant",
        "capabilities": "ecosystem explanation, concept clarification, getting started help",
    }

    envelope.metadata.update(context)
    return envelope


async def understand_post_process(envelope: Any, output: Dict[str, Any], agent: Any = None) -> Any:
    """
    Process Understand agent output and prepare context for Think and Respond agents.

    Extracts intent and topic to enable targeted knowledge retrieval.
    """
    intent = output.get("intent", "general")
    topic = output.get("topic", "")

    # Store classification for downstream agents
    envelope.metadata["classified_intent"] = intent
    envelope.metadata["classified_topic"] = topic

    # Map intent to relevant knowledge sections for targeted retrieval
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


async def think_pre_process(envelope: Any, agent: Any = None) -> Any:
    """
    Prepare Think agent for knowledge retrieval.

    Uses the classified intent to retrieve targeted knowledge sections.
    """
    from jeeves_capability_hello_world.prompts.knowledge_base import get_knowledge_for_sections

    # Get the knowledge sections identified by understand agent
    knowledge_sections = envelope.metadata.get("knowledge_sections", ["ecosystem_overview"])
    intent = envelope.metadata.get("classified_intent", "general")
    topic = envelope.metadata.get("classified_topic", "")

    # Retrieve targeted knowledge
    targeted_knowledge = get_knowledge_for_sections(knowledge_sections)

    # Store for Respond agent
    envelope.metadata["targeted_knowledge"] = targeted_knowledge
    envelope.metadata["tool_calls"] = []  # No external tool calls for onboarding

    return envelope


async def think_post_process(envelope: Any, output: Dict[str, Any], agent: Any = None) -> Any:
    """
    Process Think agent output.

    For onboarding, this is a pass-through that ensures knowledge context is available.
    """
    # Store knowledge retrieval results for Respond agent
    output["information"] = {
        "has_data": True,
        "knowledge_retrieved": True,
    }

    return envelope


async def respond_pre_process(envelope: Any, agent: Any = None) -> Any:
    """
    Build context for Respond agent.

    Combines original message, intent, conversation history, and targeted knowledge.
    """
    understand_output = envelope.outputs.get("understanding", {})

    user_message = envelope.raw_input
    intent = envelope.metadata.get("classified_intent", understand_output.get("intent", "general"))
    topic = envelope.metadata.get("classified_topic", understand_output.get("topic", ""))

    # Get formatted conversation history
    conversation_history = envelope.metadata.get("conversation_history", [])
    if isinstance(conversation_history, str):
        formatted_history = conversation_history
    else:
        formatted_history = _format_conversation_history(conversation_history)

    # Get targeted knowledge from Think agent
    targeted_knowledge = envelope.metadata.get("targeted_knowledge", "")

    # Inject session context from in-dialogue memory
    session_context = envelope.metadata.get("session_context", {})
    conversation_summary = session_context.get("conversation_summary", "")

    context = {
        "user_message": user_message,
        "intent": intent,
        "topic": topic,
        "conversation_history": formatted_history,
        "conversation_summary": conversation_summary,
        "turn_count": session_context.get("turn_count", 0),
        "targeted_knowledge": targeted_knowledge,
        "task": "Craft a helpful, accurate response about the Jeeves ecosystem"
    }

    envelope.metadata.update(context)
    return envelope


async def respond_post_process(envelope: Any, output: Dict[str, Any], agent: Any = None) -> Any:
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

ONBOARDING_CHATBOT_PIPELINE = PipelineConfig(
    name="onboarding_chatbot",
    max_iterations=2,           # Simple queries don't need many iterations
    max_llm_calls=4,            # 2 LLM agents × 2 potential calls each
    max_agent_hops=10,
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
            required_output_fields=["intent", "topic"],
            max_tokens=4000,                 # Increased for 8k context models
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
            max_tokens=4000,                 # Increased for 8k context models
            temperature=0.5,                 # Balanced for natural responses

            # K8s-style generation spec
            generation=GenerationParams(
                stop=["\n\n\n", "User:", "Question:"],  # Stop at clear boundaries
                repeat_penalty=1.15,  # Penalize repetition moderately
            ),

            pre_process=respond_pre_process,
            post_process=respond_post_process,
            mock_handler=None,               # Mock only for tests
            default_next="end",
            # ✅ STREAMING CONFIGURATION (Phase 1: Default Hybrid)
            output_mode=AgentOutputMode.TEXT,              # Plain text output (not JSON)
            token_stream=TokenStreamMode.AUTHORITATIVE,    # Tokens ARE authoritative output
            streaming_prompt_key="chatbot.respond_streaming",  # Use streaming prompt
        ),
    ],
)


# ═══════════════════════════════════════════════════════════════
# MODE REGISTRY
# ═══════════════════════════════════════════════════════════════

PIPELINE_MODES = {
    "onboarding_chatbot": ONBOARDING_CHATBOT_PIPELINE,
    "hello_world": ONBOARDING_CHATBOT_PIPELINE,  # Alias for compatibility
}


def get_pipeline_for_mode(mode: str = "onboarding_chatbot") -> PipelineConfig:
    """
    Get pipeline configuration for specified mode.

    Args:
        mode: Pipeline mode ("onboarding_chatbot" or "hello_world")

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
