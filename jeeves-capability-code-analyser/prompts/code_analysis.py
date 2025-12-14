"""
Code Analysis prompts - registered versions for the 7-agent code analysis pipeline.

These prompts are designed for read-only codebase exploration and understanding.
They follow the Constitutional principles:
- P1 (Accuracy First): Never hallucinate code
- P2 (Code Context Priority): Understand code in context before claims
- Amendment XI (Context Bounds): Respect token limits

Pipeline: Perception -> Intent -> Planner -> Traverser (no prompt) -> Synthesizer -> Critic -> Integration

Constitutional Compliance:
- Prompts are inline in code (not external files) per Forbidden Patterns
- P5: Deterministic Spine (prompts are contracts at LLM boundary)
- P6: Observable (prompts in version control, reviewable)

IMPORTANT: Prompts use {placeholder} syntax for context injection.
Context builder functions provide the values via str.format().
"""

from jeeves_mission_system.prompts.core.registry import register_prompt


# --- PERCEPTION PROMPTS (Agent 1) - Context Loading ---

def code_analysis_perception() -> str:
    """Perception prompt - normalize query and extract scope."""
    return """{system_identity}

**Query:** {user_query}
**Session:** {session_state}

Normalize query, extract scope (files/dirs), identify type (explore/explain/search/trace).

Output ONE JSON object only: {{"normalized_query": "...", "scope": "...", "query_type": "..."}}"""


# --- INTENT PROMPTS (Agent 2) - Query Classification ---

def code_analysis_intent() -> str:
    """Intent prompt - classify query and extract goals."""
    return """{system_identity}

**Query:** {normalized_input}
**Context:** {context_summary}
**Languages:** {detected_languages}

{capabilities_summary}

Analyze the query and extract:

1. **intent**: What the user wants to accomplish:
   - "find_symbol" - locate a specific class, function, or variable
   - "explore_module" - understand a directory or module structure
   - "trace_flow" - follow execution from entry point to implementation
   - "explain_code" - understand what specific code does
   - "search_concept" - find code related to a concept/feature

2. **search_targets**: Keywords/symbols to search for (CRITICAL for planner):
   - Extract specific names: class names, function names, variable names
   - Extract keywords: "authentication", "database", "routing"
   - Extract directory hints: "agents/", "tools/", "src/"

3. **goals**: Specific questions to answer (actionable, verifiable)

4. **constraints**: Any limits mentioned (specific files, directories, languages)

Output ONE JSON object:
{{
  "intent": "<one of the 5 intents above>",
  "search_targets": ["<symbol or keyword 1>", "<symbol or keyword 2>"],
  "goals": ["<specific goal 1>", "<specific goal 2>"],
  "constraints": {{"directories": [], "file_types": [], "exclude": []}},
  "confidence": 0.9
}}"""


# --- PLANNER PROMPTS (Agent 3) - Traversal Planning ---

def code_analysis_planner() -> str:
    """Planner prompt - create tool execution plan."""
    return """{system_identity}

**User Query:** {user_query}
**Repository:** {repo_path}
**Intent:** {intent}
**Search Targets:** {search_targets}
**Goals:** {goals}
**Scope:** {scope_path}
**Prior exploration:** {exploration_summary}

**Tools:** {available_tools}

**Bounds:** files {files_explored}/{max_files}, tokens {tokens_used}/{max_tokens}

{retry_feedback}

TWO-TOOL ARCHITECTURE - Use the search_targets extracted by Intent:

1. SEARCH using the provided search_targets:
   - Use search_code(query) with each search target
   - The Intent agent already extracted: {search_targets}
   - Use these targets DIRECTLY - don't invent new paths

2. READ ONLY after search returns paths:
   - Use read_code(path) ONLY on paths returned by search_code
   - Never guess paths

CRITICAL RULES:
- Use the search_targets from Intent - they are already extracted for you
- NEVER invent file paths like "/workspace/path/to/File.py"
- search_code finds files; read_code reads confirmed paths

Output EXACTLY ONE JSON object (no duplicates, no code fences, no explanation):
{{"steps": [{{"tool": "search_code", "parameters": {{"query": "<use a search_target from above>"}}, "reasoning": "searching for this target"}}], "rationale": "search strategy based on intent"}}"""


# --- SYNTHESIZER PROMPTS (Agent 5 - after Traverser) - Structured Understanding ---

def code_analysis_synthesizer() -> str:
    """Synthesizer prompt - structure findings with citations."""
    return """{system_identity}

**Query:** {user_query}
**Intent:** {intent}
**Search Targets:** {search_targets}
**Goals:** {goals}

**Execution Results:** {execution_results}
**Code Snippets:** {relevant_snippets}

Synthesize the search results into structured findings:

1. **findings**: What was discovered about each search target
   - Include file:line citations for EVERY claim
   - Mark which goals are satisfied vs. still open

2. **goal_status**: For each goal, indicate:
   - "satisfied" - found clear answer with evidence
   - "partial" - found some information but incomplete
   - "unsatisfied" - no relevant information found

3. **gaps**: What's missing that would fully answer the query?
   - Missing search targets that weren't found
   - Files that should be read but weren't
   - Connections that couldn't be traced

4. **quality_score**: 0.0-1.0 indicating completeness of findings

Output ONE JSON object:
{{
  "findings": [{{"target": "...", "summary": "...", "citations": ["file:line", ...]}}],
  "goal_status": {{"<goal>": "satisfied|partial|unsatisfied"}},
  "gaps": ["<gap 1>", "<gap 2>"],
  "quality_score": 0.8,
  "suggested_next_searches": ["<term>"]
}}"""


# --- CRITIC PROMPTS (Agent 6 - after Synthesizer) - Anti-Hallucination ---

def code_analysis_critic() -> str:
    """Critic prompt - validate claims against code, provide feedback (no routing).

    The Critic provides FEEDBACK ONLY. Integration decides whether to answer or reintent.
    """
    return """{system_identity}

**Query:** {user_query}
**Intent:** {intent}
**Goals:** {goals}

**Synthesizer Output:** {synthesizer_output}
**Execution Results:** {execution_results}
**Code Snippets:** {relevant_snippets}

Validate the synthesis and provide feedback for Integration:

1. **Verify citations**: Do file:line references actually exist in the snippets?
2. **Check goal coverage**: Are all goals addressed with evidence?
3. **Detect hallucination**: Are there claims without supporting code?
4. **Assess completeness**: Is this enough to answer the user's query?

**Recommendation levels** (Integration decides what to do):
- "sufficient" - Findings are accurate and complete. Ready to answer.
- "partial" - Some findings, but gaps remain. May still be enough to answer.
- "insufficient" - Major gaps or no results. May need different search approach.

Output ONE JSON object:
{{
  "recommendation": "sufficient|partial|insufficient",
  "confidence": 0.9,
  "issues": ["<issue 1>", "<issue 2>"],
  "suggested_response": "<draft response if recommendation is sufficient or partial>",
  "refine_hint": "<if insufficient: what should be searched differently>",
  "additional_searches": ["<suggested additional search terms>"]
}}"""


# --- INTEGRATION PROMPTS (Agent 7) - Response Building ---

def code_analysis_integration() -> str:
    """Integration prompt - decide answer vs reintent, build final response.

    Integration is the DECISION MAKER: answer with current findings OR reintent for better search.
    """
    return """{system_identity}

**Query:** {user_query}
**Critic Recommendation:** {critic_recommendation}
**Critic Feedback:** {critic_feedback}

**Synthesizer Findings:** {synthesizer_output}
**Code Snippets:** {relevant_snippets}
**Files Examined:** {files_examined}

**Prior Cycle Context (if reintent):** {cycle_context}

DECIDE: Can you answer the user's query with current findings?

**Decision criteria:**
- If findings exist and address the query (even partially): **answer**
- If search completely failed (no files examined) AND this is first attempt: **reintent**
- If already reintented once: **answer** with whatever we have (avoid infinite loops)

**If action=answer:**
1. Answer the query directly - Start with the key finding
2. Cite every claim - Use format `path/to/file.py:42`
3. Include relevant code snippets - Quote key lines when helpful
4. Acknowledge gaps - If something wasn't found, say so honestly
5. Keep it concise - Don't repeat information

**If action=reintent:**
- Explain why current search failed
- Suggest what Intent should look for instead

Output ONE JSON object:
{{
  "action": "answer|reintent",
  "final_response": "<if answer: the response text with citations>",
  "reason": "<if reintent: why reintenting and what to search instead>"
}}"""


def register_code_analysis_prompts() -> None:
    """Register all code analysis prompts with the PromptRegistry.

    This function should be called during capability registration
    to make prompts available to the pipeline.
    """
    # Use the decorator to register each prompt
    register_prompt(
        name="code_analysis.perception",
        version="2.0",
        description="Normalize user query and load session context for code analysis",
        constitutional_compliance="P1 (Accuracy First), P2 (Code Context Priority)"
    )(code_analysis_perception)

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
