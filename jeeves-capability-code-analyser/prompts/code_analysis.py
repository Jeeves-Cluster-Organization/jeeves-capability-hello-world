"""
Code Analysis prompts - registered versions for the 7-agent code analysis pipeline.

These prompts are designed for read-only codebase exploration and understanding.
They follow the Constitutional principles:
- P1 (Accuracy First): Never hallucinate code
- P2 (Code Context Priority): Understand code in context before claims
- Amendment XI (Context Bounds): Respect token limits

Pipeline: Perception (no LLM) -> Intent -> Planner -> Executor (no LLM) -> Synthesizer -> Critic -> Integration

Note: Perception and Executor agents have has_llm=False, so no prompts are needed for them.

Constitutional Compliance:
- Prompts are inline in code (not external files) per Forbidden Patterns
- P5: Deterministic Spine (prompts are contracts at LLM boundary)
- P6: Observable (prompts in version control, reviewable)

IMPORTANT: Prompts use {placeholder} syntax for context injection.
Context builder functions provide the values via str.format().
"""

from mission_system.prompts.core.registry import register_prompt


# --- INTENT PROMPTS (Agent 2) - Query Classification ---
# Note: Perception (Agent 1) has has_llm=False, so no prompt needed

def code_analysis_intent() -> str:
    """Intent prompt - classify query and extract goals."""
    return """{role_description}

**Query:** {normalized_input}
**Context:** {context_summary}
**Languages:** {detected_languages}

Extract search targets that will find code:

**search_targets rules:**
- SINGLE terms only: ClassName, function_name, keyword
- NO phrases like "event handler" - split into ["event", "handler", "EventHandler"]
- Extract CamelCase: FlowEvent, WebSocket, EventBus
- Extract snake_case: emit_event, handle_message
- Extract directories: gateway/, events/

**intent types:** find_symbol, explore_module, trace_flow, explain_code, search_concept

Output JSON:
{{
  "intent": "find_symbol|explore_module|trace_flow|explain_code|search_concept",
  "search_targets": ["<term_extracted_from_query>", "<another_term>"],
  "goals": ["<specific_goal_from_user_query>"],
  "constraints": {{"directories": [], "file_types": []}},
  "confidence": <0.0_to_1.0>
}}"""


# --- PLANNER PROMPTS (Agent 3) - Traversal Planning ---

def code_analysis_planner() -> str:
    """Planner prompt - create tool execution plan."""
    return """{role_description}

**Query:** {user_query}
**Search Targets:** {search_targets}
**Goals:** {goals}
**Bounds:** files {files_explored}/{max_files}, tokens {tokens_used}/{max_tokens}
{retry_feedback}

Create search steps using the search_targets above.

Tool:
- search_code(query): Find code matching query. Returns file:line citations with code snippets.

Rules:
- Use search_targets DIRECTLY - one search_code call per target
- NEVER invent file paths - search_code finds them for you

Output JSON:
{{"steps": [{{"tool": "search_code", "parameters": {{"query": "target_from_above"}}, "reasoning": "why"}}], "rationale": "strategy"}}"""


# --- SYNTHESIZER PROMPTS (Agent 5 - after Traverser) - Structured Understanding ---

def code_analysis_synthesizer() -> str:
    """Synthesizer prompt - structure findings with citations."""
    return """{role_description}

**Query:** {user_query}
**Goals:** {goals}
**Execution Results:** {execution_results}
**Code Snippets:** {relevant_snippets}

Synthesize findings from the code snippets above.

Rules:
- If Code Snippets is empty: findings=[], quality_score=0.0, all goals="unsatisfied"
- Every finding MUST cite file:line from actual snippets above
- NEVER invent file paths or citations

Output JSON:
{{
  "findings": [{{"target": "X", "summary": "...", "citations": ["file.py:42"]}}],
  "goal_status": {{"goal1": "satisfied|partial|unsatisfied"}},
  "gaps": ["what's missing"],
  "quality_score": 0.0-1.0,
  "suggested_next_searches": ["alternative terms if gaps exist"]
}}"""


# --- CRITIC PROMPTS (Agent 6 - after Synthesizer) - Anti-Hallucination ---

def code_analysis_critic() -> str:
    """Critic prompt - validate claims against code."""
    return """{role_description}

**Query:** {user_query}
**Goals:** {goals}
**Synthesizer Output:** {synthesizer_output}
**Code Snippets:** {relevant_snippets}

Validate the synthesizer findings.

Rules:
- If Code Snippets is empty: recommendation="insufficient", confidence<0.3
- Check: Do citations match actual files in snippets?
- Check: Are all goals addressed with evidence?
- Detect any claims without supporting code

Output JSON:
{{
  "recommendation": "sufficient|partial|insufficient",
  "confidence": 0.0-1.0,
  "issues": ["issue if any"],
  "refine_hint": "alternative search terms if insufficient"
}}"""


# --- INTEGRATION PROMPTS (Agent 7) - Response Building ---

def code_analysis_integration() -> str:
    """Integration prompt - decide answer vs reintent, build final response."""
    return """{role_description}

**Query:** {user_query}
**Critic Recommendation:** {critic_recommendation}
**Critic Feedback:** {critic_feedback}
**Synthesizer Findings:** {synthesizer_output}
**Code Snippets:** {relevant_snippets}
**Files Examined:** {files_examined}
**Prior Cycle:** {cycle_context}

Decide: answer with findings OR reintent for better search.

**Reintent if:** Code Snippets empty AND first attempt (no Prior Cycle)
**Answer if:** Real snippets exist OR already reintented OR critic says sufficient

Rules:
- NEVER invent file paths not in Code Snippets
- NEVER cite lines you cannot see
- If no results: say "search did not find relevant code" and list tried terms
- If results: cite only files from snippets above

Output JSON (one of):
{{"action": "answer", "final_response": "response with file:line citations"}}
{{"action": "reintent", "reason": "why and what to try instead"}}"""


def register_code_analysis_prompts() -> None:
    """Register all code analysis prompts with the PromptRegistry.

    This function should be called during capability registration
    to make prompts available to the pipeline.

    Note: Perception and Executor agents have has_llm=False, so no prompts registered for them.
    """
    register_prompt(
        name="code_analysis.intent",
        version="2.0",
        description="Classify code analysis query intent and extract goals",
        constitutional_compliance="P1 (Accuracy First), P2 (Code Context Priority)"
    )(code_analysis_intent)

    register_prompt(
        name="code_analysis.planner",
        version="2.0",
        description="Generate code traversal plan with tool calls",
        constitutional_compliance="P2 (Code Context Priority), Amendment XI (Context Bounds)"
    )(code_analysis_planner)

    register_prompt(
        name="code_analysis.synthesizer",
        version="1.0",
        description="Synthesize execution results into structured understanding",
        constitutional_compliance="P1 (Accuracy First), P2 (Code Context Priority)"
    )(code_analysis_synthesizer)

    register_prompt(
        name="code_analysis.critic",
        version="2.0",
        description="Validate code analysis results against actual code - anti-hallucination gate",
        constitutional_compliance="P1 (Accuracy First), P2 (Code Context Priority)"
    )(code_analysis_critic)

    register_prompt(
        name="code_analysis.integration",
        version="2.0",
        description="Build final response with code citations",
        constitutional_compliance="P1 (Accuracy First), P2 (Code Context Priority)"
    )(code_analysis_integration)
