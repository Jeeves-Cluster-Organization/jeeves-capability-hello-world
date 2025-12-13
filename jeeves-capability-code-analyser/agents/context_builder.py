"""
Shared context builder for the 6-agent code analysis pipeline.

This module provides consistent context to all agents, ensuring each
agent has the information it needs to perform its role effectively.

Constitutional Alignment:
- P1 (Accuracy First): Agents get accurate system capability information
- P2 (Code Context Priority): Repo context flows through the pipeline
- Amendment X (Agent Boundaries): Each agent gets role-appropriate context
- Amendment XI (Context Bounds): Bounds are communicated clearly

Pipeline Context Flow:
    Perception -> Intent -> Planner -> Traverser -> Critic -> Integration

Each agent receives:
1. System identity (who we are)
2. Role-specific context (what this agent does)
3. Repository context (what we're analyzing)
4. Available capabilities (what tools exist)
5. Current bounds (limits to respect)
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
# Constitutional imports - RiskLevel from protocols, others from mission_system contracts
from jeeves_protocols import RiskLevel
from jeeves_mission_system.contracts import ContextBounds, tool_catalog


@dataclass
class RepositoryContext:
    """Context about the repository being analyzed."""

    # Populated by Perception agent
    detected_languages: List[str]
    scope_path: Optional[str]
    root_structure: Optional[str]  # Brief tree overview

    # Session continuity
    explored_files_count: int
    explored_symbols_count: int
    tokens_used: int

    def to_summary(self, context_bounds: Optional[ContextBounds] = None) -> str:
        """Generate human-readable summary.

        Args:
            context_bounds: Context bounds configuration (from AppContext)
        """
        parts = []

        if self.detected_languages:
            parts.append(f"Languages: {', '.join(self.detected_languages)}")

        if self.scope_path:
            parts.append(f"Focus: {self.scope_path}")

        if self.explored_files_count > 0:
            parts.append(f"Prior exploration: {self.explored_files_count} files, {self.explored_symbols_count} symbols")

        if self.tokens_used > 0 and context_bounds is not None:
            remaining = context_bounds.max_total_code_tokens - self.tokens_used
            parts.append(f"Token budget: {remaining:,} remaining")

        return " | ".join(parts) if parts else "New session - no prior context"


def get_system_identity() -> str:
    """Core identity block for the Code Analysis Agent.

    This replaces the fragmented identity blocks with a unified statement
    that emphasizes the read-only, accuracy-focused nature of the system.
    """
    return """You are the Code Analysis Agent - a specialized system for understanding codebases.

CORE PRINCIPLES (in priority order):
1. ACCURACY FIRST: Never hallucinate code. Every claim must be backed by actual source.
2. EVIDENCE-BASED: Cite specific file:line references for all assertions.
3. READ-ONLY: You analyze and explain. You do not modify files or manage tasks.

Your responses must be:
- Verifiable: Claims can be checked against actual code
- Cited: Use format `path/to/file.py:42` for all references
- Honest: If uncertain, say so. If you can't find something, say that."""


def get_available_tools_description() -> str:
    """Generate description of the 5 exposed tools.

    Per Amendment XXII (Tool Consolidation):
    - Only 5 tools are exposed to agents
    - analyze handles most queries in a single step
    - All composite tools are INTERNAL to analyze
    """
    return """**AVAILABLE TOOLS (use only these):**

### Primary (use for most queries)
  - analyze(target): Unified analysis - auto-detects if target is a symbol, module, file, or query.
    Internally orchestrates all necessary tools. Returns comprehensive analysis with citations.
    Examples: analyze("CodeAnalysisRuntime"), analyze("agents/"), analyze("how does routing work")

### Direct Access (when you need specific data)
  - read_code(path): Read a specific file's contents
  - find_related(query): Find files semantically related to a query

### Utility
  - git_status(): Current repository state
  - list_tools(): Discover available tools

**PLANNING GUIDANCE:**
- For most queries: 1 step with analyze(target) is sufficient
- Use read_code only when you need the exact contents of a known file
- Use find_related when you need to discover files by semantic similarity"""


def get_context_bounds_description(context_bounds: ContextBounds) -> str:
    """Generate clear description of context bounds.

    This ensures all agents understand the limits they must respect.

    Args:
        context_bounds: Context bounds configuration (from AppContext)
    """
    return f"""CONTEXT BOUNDS (Amendment XI - MUST RESPECT):
- Max files per query: {context_bounds.max_files_per_query}
- Max tokens per query: {context_bounds.max_total_code_tokens:,}
- Max grep results: {context_bounds.max_grep_results}
- Max tree depth: 3 levels recommended
- Max planner-critic loops: {context_bounds.max_loops}

When approaching limits:
- Prioritize most relevant files
- Use line ranges instead of full files
- Focus on answering the specific question"""


def get_pipeline_overview() -> str:
    """Description of the 6-agent pipeline for agents that need context."""
    return """PIPELINE STRUCTURE (6 agents, sequential flow):
1. PERCEPTION: Normalizes query, loads session context, detects scope
2. INTENT: Classifies query type, extracts specific goals
3. PLANNER: Creates tool execution plan respecting bounds
4. TRAVERSER: Executes tools, gathers code evidence (deterministic)
5. CRITIC: Validates results, anti-hallucination gate
6. INTEGRATION: Builds final response with citations

Data flows through GenericEnvelope - each agent reads predecessors' output and writes its own."""


def build_perception_context(
    user_query: str,
    session_state: Dict[str, Any],
) -> Dict[str, str]:
    """Build context dictionary for Perception agent."""
    return {
        "system_identity": get_system_identity(),
        "user_query": user_query,
        "session_state": _format_session_state(session_state),
        "role_description": """Your role: PERCEPTION AGENT
- Normalize the user's query (clean up, focus on core question)
- Detect if query targets specific directories or files
- Load any relevant session context
- Identify programming languages mentioned or implied""",
    }


def build_intent_context(
    normalized_input: str,
    context_summary: str,
    detected_languages: List[str],
) -> Dict[str, str]:
    """Build context dictionary for Intent agent."""
    tools_summary = _get_tools_capability_summary()

    return {
        "system_identity": get_system_identity(),
        "normalized_input": normalized_input,
        "context_summary": context_summary or "New session - no prior context",
        "detected_languages": ", ".join(detected_languages) if detected_languages else "Not specified",
        "capabilities_summary": tools_summary,
        "role_description": """Your role: INTENT AGENT
- Classify the query into one of 5 categories
- Extract specific, actionable goals
- Identify constraints (file types, directories, etc.)
- Flag ambiguities that might need clarification""",
    }


def build_planner_context(
    intent: str,
    goals: List[str],
    scope_path: Optional[str],
    exploration_summary: str,
    tokens_used: int,
    files_explored: int,
    context_bounds: ContextBounds,
    retry_feedback: Optional[str] = None,
    completed_stages: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, str]:
    """Build context dictionary for Planner agent.

    Args:
        intent: The classified intent from Intent agent
        goals: List of goals to achieve
        scope_path: Optional scope path for focused analysis
        exploration_summary: Summary of prior exploration
        tokens_used: Tokens consumed so far
        files_explored: Files explored so far
        context_bounds: Context bounds configuration (from AppContext)
        retry_feedback: Optional feedback from previous attempt
        completed_stages: Results from previous stages (for multi-stage execution).
                         Each stage contains: satisfied_goals, entities_found, open_questions.
    """
    context = {
        "system_identity": get_system_identity(),
        "intent": intent,
        "goals": "\n".join(f"- {g}" for g in goals) if goals else "- Answer the user's query",
        "scope_path": scope_path or "Entire repository",
        "exploration_summary": exploration_summary,
        "available_tools": get_available_tools_description(),
        "bounds_description": get_context_bounds_description(context_bounds),
        "max_files": str(context_bounds.max_files_per_query),
        "max_tokens": str(context_bounds.max_total_code_tokens),
        "tokens_used": str(tokens_used),
        "files_explored": str(files_explored),
        "remaining_tokens": str(context_bounds.max_total_code_tokens - tokens_used),
        "remaining_files": str(context_bounds.max_files_per_query - files_explored),
        "role_description": """Your role: PLANNER AGENT
- Create a plan of tool calls to answer the query
- Respect context bounds (files, tokens)
- Order steps logically (broader exploration first, then specific reads)
- Each step should have clear reasoning""",
    }

    if retry_feedback:
        context["retry_feedback"] = f"\nPREVIOUS ATTEMPT FEEDBACK:\n{retry_feedback}\nAdjust your plan to address this feedback."
    else:
        context["retry_feedback"] = ""

    # Add context from previous stages (for multi-stage execution)
    if completed_stages:
        stage_context = _format_completed_stages(completed_stages)
        context["previous_stages"] = stage_context
    else:
        context["previous_stages"] = ""

    return context


def _format_completed_stages(stages: List[Dict[str, Any]]) -> str:
    """Format completed stages for Planner context."""
    if not stages:
        return ""

    parts = ["PREVIOUS STAGES (already explored - don't repeat):"]
    for stage in stages:
        stage_num = stage.get("stage_number", "?")
        satisfied = stage.get("satisfied_goals", [])
        entities = stage.get("entities_found", [])
        questions = stage.get("open_questions", [])

        parts.append(f"\n**Stage {stage_num}:**")
        if satisfied:
            parts.append(f"  Goals satisfied: {', '.join(satisfied[:3])}")
        if entities:
            parts.append(f"  Entities found: {', '.join(entities[:5])}")
        if questions:
            parts.append(f"  Open questions: {'; '.join(questions[:2])}")

    parts.append("\nFocus on REMAINING goals. Don't re-explore what was already found.")
    return "\n".join(parts)


def build_synthesizer_context(
    user_query: str,
    intent: str,
    goals: List[str],
    execution_results: str,
    relevant_snippets: str,
) -> Dict[str, str]:
    """Build context dictionary for Synthesizer agent."""
    return {
        "system_identity": get_system_identity(),
        "user_query": user_query,
        "intent": intent,
        "goals": "\n".join(f"- {g}" for g in goals) if goals else "- Answer the query",
        "execution_results": execution_results,
        "relevant_snippets": relevant_snippets,
        "role_description": """Your role: SYNTHESIZER AGENT (Structured Understanding)
- Extract entities (classes, functions, modules) from execution results
- Identify key code flows (call chains, data flows)
- Surface open questions that remain unanswered
- Detect contradictions in the discovered code
- Provide hints for goal refinement
- Build accumulated evidence with file:line citations

You bridge raw execution data to structured understanding for the Critic.""",
    }


def build_critic_context(
    user_query: str,
    intent: str,
    goals: List[str],
    execution_results: str,
    relevant_snippets: str,
) -> Dict[str, str]:
    """Build context dictionary for Critic agent."""
    return {
        "system_identity": get_system_identity(),
        "user_query": user_query,
        "intent": intent,
        "goals": "\n".join(f"- {g}" for g in goals) if goals else "- Answer the query",
        "execution_results": execution_results,
        "relevant_snippets": relevant_snippets,
        "role_description": """Your role: CRITIC AGENT (Anti-Hallucination Gate)
- Verify execution results address all stated goals
- Check that every potential claim has code evidence
- Detect gaps that would weaken the answer
- NEVER approve claims not backed by retrieved code

Verdict options:
- APPROVED: Results support an accurate answer (provide suggested response)
- REPLAN: Need more information (provide feedback for planner)
- CLARIFY: Query too ambiguous (provide clarification question)""",
    }


def build_integration_context(
    user_query: str,
    verdict: str,
    validated_claims: str,
    relevant_snippets: str,
    exploration_summary: str,
    files_examined: List[str],
) -> Dict[str, str]:
    """Build context dictionary for Integration agent."""
    return {
        "system_identity": get_system_identity(),
        "user_query": user_query,
        "verdict": verdict,
        "validated_claims": validated_claims or "No validated claims from critic",
        "relevant_snippets": relevant_snippets,
        "exploration_summary": exploration_summary,
        "files_examined": ", ".join(files_examined) if files_examined else "None recorded",
        "pipeline_overview": get_pipeline_overview(),
        "role_description": """Your role: INTEGRATION AGENT (Response Writer)
- Build the final response from validated claims
- Add file:line citations for every claim
- Structure the answer clearly
- Note limitations honestly""",
    }


def _format_session_state(state: Dict[str, Any]) -> str:
    """Format session state for prompt inclusion."""
    if not state:
        return "No prior session state (new session)"

    parts = []

    if state.get("explored_files"):
        files = state["explored_files"]
        parts.append(f"Files explored: {len(files)} ({', '.join(files[:5])}{'...' if len(files) > 5 else ''})")

    if state.get("explored_symbols"):
        symbols = state["explored_symbols"]
        parts.append(f"Symbols looked up: {len(symbols)}")

    if state.get("relevant_snippets"):
        parts.append(f"Snippets collected: {len(state['relevant_snippets'])}")

    if state.get("detected_languages"):
        parts.append(f"Languages: {', '.join(state['detected_languages'])}")

    if state.get("last_query"):
        parts.append(f"Last query: {state['last_query'][:100]}...")

    return "\n".join(parts) if parts else "Session exists but no exploration yet"


def _get_tools_capability_summary() -> str:
    """Brief summary of what the system can do (for Intent agent).

    Per Amendment XXII: Only 5 tools exposed, with analyze as primary.
    """
    return """This system can:
- Analyze anything: symbols, modules, files, or natural language queries (via analyze tool)
- Read specific files: get exact file contents (via read_code)
- Find related code: semantic search for similar files (via find_related)
- Check git status: current repository state (via git_status)

All operations are READ-ONLY - we analyze code, we don't modify it.
The analyze tool internally handles all complexity (symbol lookup, module mapping, etc.)."""
