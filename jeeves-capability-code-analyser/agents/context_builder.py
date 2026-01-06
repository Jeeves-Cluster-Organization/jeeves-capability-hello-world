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
from tools.catalog import tool_catalog
# Domain-specific bounds from capability config (per Constitution R6)
from jeeves_capability_code_analyser.config import CodeAnalysisBounds, get_code_analysis_bounds


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

    def to_summary(self, context_bounds: Optional[CodeAnalysisBounds] = None) -> str:
        """Generate human-readable summary.

        Args:
            context_bounds: Code analysis bounds (from capability config)
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
    """Generate description of the exposed tools.

    Per Amendment XXII v2 (Two-Tool Architecture):
    - search_code: Primary search tool - ALWAYS searches, never assumes paths
    - read_code: Read confirmed paths ONLY from prior search results
    """
    return """**AVAILABLE TOOLS - TWO-TOOL ARCHITECTURE:**

### Step 1: SEARCH (always start here)
  - search_code(query): Search for code - ALWAYS searches, never assumes paths exist.
    Use for: symbols, keywords, natural language, directory exploration.
    Examples:
      - search_code("Jeeves") - finds the Jeeves class
      - search_code("authentication") - finds auth-related code
      - search_code("agents/") - explores the agents directory
      - search_code("how does routing work") - semantic search

### Step 2: READ (only after search)
  - read_code(path): Read a specific file's contents.
    ONLY use paths returned by search_code results.
    Example: If search_code returns "agents/planner.py:42", use read_code("agents/planner.py")

### Utility
  - git_status(): Current repository state
  - list_tools(): Discover available tools

**CRITICAL RULES:**
1. ALWAYS start with search_code - it finds files for you
2. NEVER invent file paths like "/workspace/path/to/File.py"
3. read_code is ONLY for paths from prior search_code results
4. If you don't know the path, use search_code first"""


def get_context_bounds_description(context_bounds: CodeAnalysisBounds) -> str:
    """Generate clear description of context bounds.

    This ensures all agents understand the limits they must respect.

    Args:
        context_bounds: Code analysis bounds (from capability config)
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


# Note: build_perception_context() removed - Perception agent has has_llm=False,
# so it doesn't need a context builder. See pipeline_config.py perception_pre_process()


def build_intent_context(
    normalized_input: str,
    context_summary: str,
    detected_languages: List[str],
    reintent_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """Build context dictionary for Intent agent.

    Args:
        normalized_input: Normalized query from perception
        context_summary: Summary of session context
        detected_languages: Languages detected in codebase
        reintent_context: Context from prior cycle (if this is a reintent)
    """
    tools_summary = _get_tools_capability_summary()

    # Format reintent context if present
    reintent_str = ""
    if reintent_context:
        prior_cycle = reintent_context.get("prior_cycle", {})
        reason = reintent_context.get("reason", "")
        prior_targets = prior_cycle.get("prior_search_targets", [])
        prior_files = prior_cycle.get("files_examined", [])
        refine_hint = prior_cycle.get("critic_feedback", {}).get("refine_hint", "")

        reintent_str = f"""
**REINTENT - Prior search failed. Extract DIFFERENT search targets.**
- Prior search targets (did not work): {prior_targets}
- Files found: {len(prior_files)}
- Reason for reintent: {reason}
- Hint: {refine_hint}

Do NOT repeat the same search targets. Try different keywords, synonyms, or approaches."""

    context_with_reintent = context_summary or "New session - no prior context"
    if reintent_str:
        context_with_reintent += reintent_str

    return {
        "normalized_input": normalized_input,
        "context_summary": context_with_reintent,
        "detected_languages": ", ".join(detected_languages) if detected_languages else "Not specified",
        "capabilities_summary": tools_summary,
        "role_description": """Your role: INTENT AGENT
- Classify the query into one of 5 intent categories
- Extract SEARCH TARGETS (symbols, keywords, directories) - this is CRITICAL
- Extract specific, actionable goals
- Identify constraints (file types, directories, etc.)
- The planner will use your search_targets to call search_code()""",
    }


def build_planner_context(
    intent: str,
    goals: List[str],
    scope_path: Optional[str],
    exploration_summary: str,
    tokens_used: int,
    files_explored: int,
    context_bounds: CodeAnalysisBounds,
    retry_feedback: Optional[str] = None,
    completed_stages: Optional[List[Dict[str, Any]]] = None,
    user_query: Optional[str] = None,
    repo_path: Optional[str] = None,
    search_targets: Optional[List[str]] = None,
) -> Dict[str, str]:
    """Build context dictionary for Planner agent.

    Args:
        intent: The classified intent from Intent agent
        goals: List of goals to achieve
        scope_path: Optional scope path for focused analysis
        exploration_summary: Summary of prior exploration
        tokens_used: Tokens consumed so far
        files_explored: Files explored so far
        context_bounds: Code analysis bounds (from capability config)
        retry_feedback: Optional feedback from previous attempt
        completed_stages: Results from previous stages (for multi-stage execution).
                         Each stage contains: satisfied_goals, entities_found, open_questions.
        user_query: Original user query (for target extraction)
        repo_path: Current repository path being analyzed
        search_targets: List of search targets extracted by Intent agent
    """
    # Format search targets for the prompt
    targets_formatted = ", ".join(f'"{t}"' for t in search_targets) if search_targets else "none extracted"

    context = {
        "user_query": user_query or "Unknown query",
        "repo_path": repo_path or "/workspace",
        "intent": intent,
        "search_targets": targets_formatted,
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
- Use the search_targets from Intent to call search_code()
- Respect context bounds (files, tokens)
- NEVER invent file paths - use search_code to find them
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
        "user_query": user_query,
        "intent": intent,
        "goals": "\n".join(f"- {g}" for g in goals) if goals else "- Answer the query",
        "execution_results": execution_results,
        "relevant_snippets": relevant_snippets,
        "role_description": """Your role: SYNTHESIZER AGENT (Structured Understanding)
- Extract entities (classes, functions, modules) from execution results
- Identify key code flows (call chains, data flows)
- Surface open questions that remain unanswered
- Build accumulated evidence with file:line citations

You bridge raw execution data to structured understanding for the Critic.""",
    }


def build_critic_context(
    user_query: str,
    intent: str,
    goals: List[str],
    execution_results: str,
    relevant_snippets: str,
    synthesizer_output: str = "",
) -> Dict[str, str]:
    """Build context dictionary for Critic agent."""
    return {
        "user_query": user_query,
        "intent": intent,
        "goals": "\n".join(f"- {g}" for g in goals) if goals else "- Answer the query",
        "execution_results": execution_results,
        "relevant_snippets": relevant_snippets,
        "synthesizer_output": synthesizer_output,
        "role_description": """Your role: CRITIC AGENT (Anti-Hallucination Gate)
- Verify execution results address all stated goals
- Check that every potential claim has code evidence
- Detect gaps that would weaken the answer
- NEVER approve claims not backed by retrieved code

Verdict options:
- sufficient: Results support an accurate answer
- partial: Some evidence but gaps remain
- insufficient: Need more information or search failed""",
    }


def build_integration_context(
    user_query: str,
    critic_recommendation: str,
    critic_feedback: Dict[str, Any],
    synthesizer_output: str,
    relevant_snippets: str,
    files_examined: List[str],
    cycle_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """Build context dictionary for Integration agent.

    Integration is the DECISION MAKER: decides answer vs reintent.

    Args:
        user_query: Original user query
        critic_recommendation: sufficient/partial/insufficient
        critic_feedback: Full critic output with issues, hints, etc.
        synthesizer_output: Structured findings from synthesizer
        relevant_snippets: Code snippets collected
        files_examined: List of files that were examined
        cycle_context: Context from prior cycle (if reintenting)
    """
    # Format critic feedback for prompt
    critic_feedback_str = ""
    if critic_feedback:
        issues = critic_feedback.get("issues", [])
        if issues:
            critic_feedback_str += f"Issues: {'; '.join(issues)}\n"
        refine_hint = critic_feedback.get("refine_hint", "")
        if refine_hint:
            critic_feedback_str += f"Refinement hint: {refine_hint}"

    # Format cycle context
    cycle_context_str = "First attempt - no prior cycle"
    if cycle_context:
        prior = cycle_context.get("prior_cycle", {})
        if prior:
            prior_targets = prior.get("prior_search_targets", [])
            prior_files = prior.get("files_examined", [])
            cycle_context_str = f"Prior search targets: {prior_targets}. Prior files examined: {len(prior_files)}."
            reason = cycle_context.get("reason", "")
            if reason:
                cycle_context_str += f" Reason for reintent: {reason}"

    return {
        "user_query": user_query,
        "critic_recommendation": critic_recommendation,
        "critic_feedback": critic_feedback_str or "No specific feedback",
        "synthesizer_output": synthesizer_output,
        "relevant_snippets": relevant_snippets,
        "files_examined": ", ".join(files_examined) if files_examined else "None examined",
        "cycle_context": cycle_context_str,
        "role_description": """Your role: INTEGRATION AGENT (Decision Maker)
- DECIDE: answer with current findings OR reintent for better search
- If answering: build response with file:line citations
- If reintenting: explain why and what to search instead
- Avoid infinite loops - if already reintented, answer with best effort""",
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

    Per Amendment XXII v2: Two-tool architecture.
    """
    return """This system can:
- Search for code: find symbols, keywords, patterns (via search_code)
- Read files: get exact file contents (via read_code, ONLY for confirmed paths)
- Check git status: current repository state (via git_status)

All operations are READ-ONLY - we analyze code, we don't modify it.
The search_code tool finds files; read_code reads them. Always search first."""
