"""
Code Analysis Pipeline Configuration - Declarative agent definitions.

This replaces the 7 concrete agent classes with configuration-driven definitions.
The Runtime (v4.0) uses this config to execute the pipeline.

Migration:
- CodeAnalysisPerceptionAgent → AgentConfig(name="perception", ...)
- CodeAnalysisIntentAgent → AgentConfig(name="intent", has_llm=True, ...)
- etc.

Capability-specific logic (prompts, mock handlers, normalizers) is provided
via hook functions defined here.

Context Injection Architecture:
- LLM agents use pre_process hooks to call context builders
- Context builders return rich, capability-specific context dicts
- Hooks store context in envelope.metadata
- Runtime's _call_llm() merges metadata into prompt context via context.update(envelope.metadata)
- Prompts use {placeholder} syntax to access context fields
"""

from typing import Any, Dict, List, Optional
from jeeves_mission_system.contracts_core import (
    AgentConfig,
    PipelineConfig,
    RoutingRule,
    ToolAccess,
    TerminalReason,
)
from jeeves_capability_code_analyser.config import get_code_analysis_bounds


# ─────────────────────────────────────────────────────────────────
# CAPABILITY-SPECIFIC LIMITS
# ─────────────────────────────────────────────────────────────────

# Maximum number of reintent cycles before forcing an answer.
# This prevents infinite loops when LLM keeps deciding to reintent.
# Set to 2: allows one retry after initial attempt, then must answer.
MAX_REINTENT_CYCLES = 2


# ─────────────────────────────────────────────────────────────────
# HOOK FUNCTIONS - Capability-specific logic
# ─────────────────────────────────────────────────────────────────

def perception_pre_process(envelope: Any, agent: Any = None) -> Any:
    """Perception pre-process: normalize input, load context."""
    # Normalize input
    raw = envelope.raw_input.strip()

    # Build perception output
    output = {
        "normalized_input": raw,
        "context_summary": envelope.metadata.get("context_summary", ""),
        "session_scope": envelope.session_id,
        "detected_languages": [],  # Could detect from context
    }

    envelope.outputs["perception"] = output
    return envelope


def perception_mock_handler(envelope: Any) -> Dict[str, Any]:
    """Mock perception for testing."""
    return {
        "normalized_input": envelope.raw_input.strip(),
        "context_summary": "Mock context",
        "session_scope": envelope.session_id,
        "detected_languages": ["python"],
    }


# ─────────────────────────────────────────────────────────────────
# LLM AGENT PRE-PROCESS HOOKS - Context Builder Injection
# ─────────────────────────────────────────────────────────────────

def intent_pre_process(envelope: Any, agent: Any = None) -> Any:
    """Build rich context for Intent agent via context builder."""
    from agents.context_builder import build_intent_context

    perception = envelope.outputs.get("perception", {})

    context = build_intent_context(
        normalized_input=perception.get("normalized_input", envelope.raw_input),
        context_summary=perception.get("context_summary", ""),
        detected_languages=perception.get("detected_languages", []),
        reintent_context=envelope.metadata.get("reintent_context"),
    )

    envelope.metadata.update(context)
    return envelope


def planner_pre_process(envelope: Any, agent: Any = None) -> Any:
    """Build rich context for Planner agent via context builder."""
    from agents.context_builder import build_planner_context

    intent_output = envelope.outputs.get("intent", {})
    perception = envelope.outputs.get("perception", {})
    bounds = get_code_analysis_bounds()

    context = build_planner_context(
        intent=intent_output.get("intent", ""),
        goals=intent_output.get("goals", []),
        scope_path=perception.get("scope", ""),
        exploration_summary="",
        # NOTE: Cast to int because context builders return string values for prompt templates,
        # which get merged back into metadata. On reintent, we'd read strings without this cast.
        tokens_used=int(envelope.metadata.get("tokens_used", 0)),
        files_explored=int(envelope.metadata.get("files_explored", 0)),
        context_bounds=bounds,
        retry_feedback=envelope.metadata.get("retry_feedback"),
        user_query=envelope.raw_input,
        search_targets=intent_output.get("search_targets", []),
    )

    envelope.metadata.update(context)
    return envelope


def synthesizer_pre_process(envelope: Any, agent: Any = None) -> Any:
    """Build rich context for Synthesizer agent via context builder.

    NOTE: We summarize execution results here to prevent prompt explosion.
    Raw executor output can be 1-2M chars; summarizer caps to ~50K.
    """
    from agents.context_builder import build_synthesizer_context
    from agents.summarizer import summarize_execution_results, extract_citations_from_results
    from contracts.validation import validate_and_log
    import json
    import structlog

    logger = structlog.get_logger()
    intent_output = envelope.outputs.get("intent", {})
    execution = envelope.outputs.get("execution", {})

    # Validate tool results before LLM sees them (prevents hallucinations from malformed outputs)
    raw_results = execution.get("results", [])
    if isinstance(raw_results, list):
        for result in raw_results:
            if isinstance(result, dict):
                tool_name = result.get("tool") or result.get("tool_name")
                if tool_name:
                    validate_and_log(tool_name, result, logger)

    # Summarize raw execution results to prevent prompt explosion
    # Raw results can be 1-2M chars; this caps to manageable size
    if isinstance(raw_results, list):
        summarized = summarize_execution_results(raw_results)
        execution_results_str = json.dumps(summarized, indent=2, default=str)
    else:
        execution_results_str = str(raw_results)[:50000]  # Fallback cap

    # Extract citations for the synthesizer to use
    citations = extract_citations_from_results(raw_results) if isinstance(raw_results, list) else []
    citations_str = json.dumps(citations[:50], indent=2) if citations else "[]"

    # Snippets are usually already bounded, but cap just in case
    snippets = execution.get("snippets", "")
    snippets_str = str(snippets)[:30000] if snippets else ""

    context = build_synthesizer_context(
        user_query=envelope.raw_input,
        intent=intent_output.get("intent", ""),
        goals=intent_output.get("goals", []),
        execution_results=execution_results_str,
        relevant_snippets=f"{snippets_str}\n\n**Extracted Citations:**\n{citations_str}",
    )

    envelope.metadata.update(context)
    return envelope


def critic_pre_process(envelope: Any, agent: Any = None) -> Any:
    """Build rich context for Critic agent via context builder."""
    from agents.context_builder import build_critic_context

    intent_output = envelope.outputs.get("intent", {})
    execution = envelope.outputs.get("execution", {})
    synthesizer = envelope.outputs.get("synthesizer", {})

    context = build_critic_context(
        user_query=envelope.raw_input,
        intent=intent_output.get("intent", ""),
        goals=intent_output.get("goals", []),
        execution_results=str(execution.get("results", "")),
        relevant_snippets=str(execution.get("snippets", "")),
        synthesizer_output=str(synthesizer),
    )

    envelope.metadata.update(context)
    return envelope


def integration_pre_process(envelope: Any, agent: Any = None) -> Any:
    """Build rich context for Integration agent via context builder."""
    from agents.context_builder import build_integration_context

    critic = envelope.outputs.get("critic", {})
    synthesizer = envelope.outputs.get("synthesizer", {})
    execution = envelope.outputs.get("execution", {})

    context = build_integration_context(
        user_query=envelope.raw_input,
        critic_recommendation=critic.get("recommendation", ""),
        critic_feedback=critic,
        synthesizer_output=str(synthesizer),
        relevant_snippets=str(execution.get("snippets", "")),
        files_examined=execution.get("files_examined", []),
        cycle_context=envelope.metadata.get("_cycle_data"),
    )

    envelope.metadata.update(context)
    return envelope


def intent_mock_handler(envelope: Any) -> Dict[str, Any]:
    """Mock intent analysis for testing."""
    import re
    msg_lower = envelope.raw_input.lower()
    msg_original = envelope.raw_input

    # Classify intent
    if any(kw in msg_lower for kw in ["flow", "trace", "call chain", "execution"]):
        intent = "trace_flow"
    elif any(kw in msg_lower for kw in ["where is", "find", "definition", "locate"]):
        intent = "find_symbol"
    elif any(kw in msg_lower for kw in ["explain", "what does", "how does", "understand"]):
        intent = "explain_code"
    elif any(kw in msg_lower for kw in ["module", "directory", "structure", "architecture"]):
        intent = "explore_module"
    else:
        intent = "search_concept"

    # Extract search targets - look for CamelCase, quoted strings, or notable keywords
    search_targets = []

    # Find CamelCase words (likely class names)
    camel_matches = re.findall(r'\b[A-Z][a-zA-Z0-9]+\b', msg_original)
    search_targets.extend(camel_matches)

    # Find quoted strings
    quoted_matches = re.findall(r'["\']([^"\']+)["\']', msg_original)
    search_targets.extend(quoted_matches)

    # Find snake_case words (likely function names)
    snake_matches = re.findall(r'\b[a-z]+_[a-z_]+\b', msg_lower)
    search_targets.extend(snake_matches)

    # Find directory patterns
    dir_matches = re.findall(r'\b(\w+/)\b', msg_original)
    search_targets.extend(dir_matches)

    # Fallback: extract key nouns if no targets found
    if not search_targets:
        # Simple extraction of potential code terms
        words = msg_original.split()
        for word in words:
            clean = word.strip('?,.')
            if len(clean) > 3 and clean[0].isupper():
                search_targets.append(clean)

    # Deduplicate while preserving order
    seen = set()
    unique_targets = []
    for t in search_targets:
        if t.lower() not in seen:
            seen.add(t.lower())
            unique_targets.append(t)

    goals = [f"Find and analyze: {', '.join(unique_targets[:3]) if unique_targets else 'relevant code'}"]

    return {
        "intent": intent,
        "search_targets": unique_targets[:5],  # Limit to 5 targets
        "goals": goals,
        "constraints": {"directories": [], "file_types": [], "exclude": []},
        "confidence": 0.85,
        "clarification_needed": False,
        "clarification_question": None,
    }


def intent_post_process(envelope: Any, output: Dict[str, Any], agent: Any = None) -> Any:
    """Initialize goals after intent.

    FALLBACK: If LLM returns {"response": "..."} instead of structured output,
    we extract search targets from the raw query using the mock handler logic.
    """
    # Handle malformed LLM output - LLM may return {"response": "..."} instead of structured fields
    if "intent" not in output or "search_targets" not in output:
        # Use mock handler to generate fallback structured output
        fallback = intent_mock_handler(envelope)
        if "intent" not in output:
            output["intent"] = fallback["intent"]
        if "search_targets" not in output:
            output["search_targets"] = fallback["search_targets"]
        if "goals" not in output or not output["goals"]:
            output["goals"] = fallback["goals"]

    raw_goals = output.get("goals", [])
    # Normalize goals to strings (LLM may return dicts with metadata)
    goals = []
    for g in raw_goals:
        if isinstance(g, str):
            goals.append(g)
        elif isinstance(g, dict):
            # Extract goal text from dict
            goals.append(g.get("goal") or g.get("description") or str(g))
        else:
            goals.append(str(g))

    # Ensure we have at least one goal
    if not goals:
        goals = [f"Analyze: {envelope.raw_input[:100]}"]

    envelope.initialize_goals(goals)

    # Check for clarification
    if output.get("clarification_needed"):
        envelope.interrupt_pending = True
        envelope.interrupt = {
            "type": "clarification",
            "question": output.get("clarification_question"),
        }

    return envelope


def planner_mock_handler(envelope: Any) -> Dict[str, Any]:
    """Mock plan generation for testing."""
    intent_output = envelope.outputs.get("intent", {})
    intent = intent_output.get("intent", "understand_architecture")

    # Generate mock plan based on intent
    if intent == "trace_flow":
        steps = [
            {"step_id": "step_1", "tool": "search_code", "parameters": {"query": "main entry"}},
            {"step_id": "step_2", "tool": "read_file", "parameters": {"path": "src/main.py"}},
        ]
    elif intent == "find_definition":
        steps = [
            {"step_id": "step_1", "tool": "search_symbol", "parameters": {"symbol": "unknown"}},
        ]
    else:
        steps = [
            {"step_id": "step_1", "tool": "list_files", "parameters": {"path": "src/"}},
        ]

    return {
        "plan_id": f"plan_{envelope.envelope_id}",
        "steps": steps,
        "rationale": f"Mock plan for {intent}",
        "feasibility_score": 0.9,
    }


def executor_pre_process(envelope: Any, agent: Any = None) -> Any:
    """
    Pre-process for executor: Convert planner steps to tool_calls format.

    The planner outputs:
        {"steps": [{"step_id": "...", "tool": "search_code", "parameters": {...}}, ...]}

    The executor expects:
        {"tool_calls": [{"name": "search_code", "params": {...}}, ...]}

    This hook bridges that gap so tools actually execute.
    """
    plan_output = envelope.outputs.get("plan", {})

    # Debug logging to diagnose empty executor issues
    # Use agent's logger if available, otherwise try get_logger
    logger = None
    if agent is not None and hasattr(agent, '_logger'):
        logger = agent._logger
    else:
        try:
            import structlog
            logger = structlog.get_logger()
            logger = get_logger()
        except Exception:
            pass

    if logger:
        logger.debug(
            "executor_pre_process_plan_output",
            plan_output_type=type(plan_output).__name__,
            plan_output_keys=list(plan_output.keys()) if isinstance(plan_output, dict) else None,
            plan_output_preview=str(plan_output)[:500] if plan_output else "empty",
            envelope_output_keys=list(envelope.outputs.keys()),
        )

    steps = plan_output.get("steps", [])

    if logger:
        logger.debug(
            "executor_pre_process_steps",
            steps_count=len(steps),
            steps_preview=str(steps)[:300] if steps else "no_steps",
        )

    # Convert plan steps to tool_calls format
    tool_calls = []
    for step in steps:
        tool_name = step.get("tool")
        params = step.get("parameters", {})
        if tool_name:
            tool_calls.append({
                "name": tool_name,
                "params": params,
            })

    # Store in execution output so agent.process() can find it
    envelope.outputs["execution"] = {"tool_calls": tool_calls}

    return envelope


def _extract_files_from_result(tool_result: Any) -> List[str]:
    """
    Extract file paths from a tool result using convention-based keys.

    Tools consistently use these patterns:
    - "path": single file path (read_file, tree_structure)
    - "file": single file path (parse_symbols, get_dependencies)
    - "files": list of file paths (glob_files, list_directory)
    - Nested in "matches"/"references" with "file" key
    """
    if not isinstance(tool_result, dict):
        return []

    files = []

    # Direct path keys (single file)
    for key in ("path", "file", "file_path"):
        val = tool_result.get(key)
        if isinstance(val, str) and val:
            files.append(val)

    # List of files
    file_list = tool_result.get("files", [])
    if isinstance(file_list, list):
        files.extend(f for f in file_list if isinstance(f, str))

    # Nested matches/references with "file" key
    for key in ("matches", "references", "results"):
        nested = tool_result.get(key, [])
        if isinstance(nested, list):
            for item in nested[:20]:  # Limit nested extraction
                if isinstance(item, dict):
                    f = item.get("file") or item.get("path")
                    if isinstance(f, str) and f:
                        files.append(f)

    return files


def _extract_snippets_from_tool_results(tool_results: List[Any]) -> str:
    """
    Extract code snippets from tool results for LLM context.

    Transforms raw tool output into a formatted string that LLM agents
    can use to answer questions with accurate citations.

    This function bridges the gap between executor tool output and the
    {relevant_snippets} placeholder expected by synthesizer/critic/integration prompts.

    Returns:
        Formatted string with file paths, line numbers, and code content.
        Empty string if no snippets found.
    """
    snippets = []

    for result in tool_results:
        wrapped_result = result.get("result", {})

        if not isinstance(wrapped_result, dict):
            continue

        # Unwrap ToolExecutionCore wrapper: {"status": ..., "data": <actual_result>}
        # Fallback to wrapped_result if no "data" key (for direct tool results)
        tool_result = wrapped_result.get("data", wrapped_result)

        if not isinstance(tool_result, dict):
            continue

        # Extract from definition (singular - from _analyze_symbol after processing)
        if tool_result.get("definition"):
            defn = tool_result["definition"]
            file_path = defn.get("file", "")
            line = defn.get("line", 0)
            snippet = defn.get("snippet", defn.get("body", defn.get("context", "")))
            name = defn.get("name", "")
            kind = defn.get("type", defn.get("kind", "symbol"))
            if file_path:
                header = f"**{file_path}:{line}** - {kind}: `{name}`" if name else f"**{file_path}:{line}**"
                if snippet:
                    snippets.append(f"{header}\n```\n{snippet}\n```")
                else:
                    snippets.append(header)

        # Extract from definitions (plural - from explore_symbol_usage directly)
        for defn in tool_result.get("definitions", [])[:5]:
            file_path = defn.get("file", "")
            line = defn.get("line", 0)
            snippet = defn.get("snippet", defn.get("body", defn.get("context", "")))
            name = defn.get("name", "")
            kind = defn.get("type", defn.get("kind", "symbol"))
            if file_path:
                header = f"**{file_path}:{line}** - {kind}: `{name}`" if name else f"**{file_path}:{line}**"
                if snippet:
                    snippets.append(f"{header}\n```\n{snippet}\n```")
                else:
                    snippets.append(header)

        # Extract from usages (symbol usage search)
        for usage in tool_result.get("usages", [])[:10]:
            file_path = usage.get("file", "")
            line = usage.get("line", 0)
            snippet = usage.get("snippet", usage.get("body", usage.get("context", "")))
            if file_path:
                if snippet:
                    snippets.append(f"**{file_path}:{line}**\n```\n{snippet}\n```")
                else:
                    snippets.append(f"**{file_path}:{line}** - usage")

        # Extract from matches (grep/locate results)
        for match in tool_result.get("matches", [])[:15]:
            file_path = match.get("file", "")
            line = match.get("line", 0)
            snippet = match.get("match", match.get("body", match.get("context", match.get("snippet", ""))))
            if file_path and snippet:
                snippets.append(f"**{file_path}:{line}**\n```\n{snippet}\n```")

        # Extract from content (file read via read_code)
        if tool_result.get("content"):
            file_path = tool_result.get("path", tool_result.get("file", "unknown"))
            start_line = tool_result.get("start_line", 1)
            content = str(tool_result["content"])[:3000]  # Cap content size
            snippets.append(f"**{file_path}:{start_line}**\n```\n{content}\n```")

        # Extract from symbols (parse_symbols, get_file_symbols, find_symbol)
        for sym in tool_result.get("symbols", [])[:10]:
            file_path = sym.get("file", "")
            line = sym.get("line", 0)
            name = sym.get("name", "")
            kind = sym.get("kind", "symbol")
            snippet = sym.get("snippet", sym.get("body", sym.get("context", "")))
            if file_path and name:
                if snippet:
                    snippets.append(f"**{file_path}:{line}** - {kind}: `{name}`\n```\n{snippet}\n```")
                else:
                    snippets.append(f"**{file_path}:{line}** - {kind}: `{name}`")

        # Extract from module structure (map_module)
        if tool_result.get("structure"):
            path = tool_result.get("target", tool_result.get("path", "module"))
            structure = str(tool_result["structure"])[:2000]
            snippets.append(f"**Module: {path}**\n```\n{structure}\n```")

        # Extract key_files (map_module)
        key_files = tool_result.get("key_files", [])
        if key_files:
            files_list = ", ".join(f"`{f}`" for f in key_files[:5])
            snippets.append(f"**Key files:** {files_list}")

        # Extract exports (map_module)
        exports = tool_result.get("exports", [])
        if exports:
            exports_list = ", ".join(f"`{e}`" for e in exports[:10])
            snippets.append(f"**Exports:** {exports_list}")

        # Note: citations are file:line strings without code content
        # They're already included via definitions/usages/matches extraction above
        # No need to add bare citations - LLM needs actual code to cite

    # Join all snippets with separators
    if not snippets:
        return ""

    return "\n\n---\n\n".join(snippets)


class CodeAnalysisError(Exception):
    """Raised when code analysis cannot proceed due to missing data."""
    pass


def executor_post_process(envelope: Any, output: Dict[str, Any], agent: Any = None) -> Any:
    """
    Post-process executor results.

    Extracts and stores:
    1. files_examined - list of file paths for tracking
    2. snippets - formatted code snippets for LLM context (CRITICAL for downstream agents)
    3. results - raw tool results for downstream access

    Raises:
        CodeAnalysisError: If search returned no results (loud failure to prevent hallucination)
    """
    tool_results = output.get("tool_results", [])

    # LOUD FAILURE: If no tool results or all searches failed, stop the pipeline
    # This prevents downstream agents from hallucinating with empty data
    if not tool_results:
        raise CodeAnalysisError("Executor produced no tool results - cannot proceed")

    # Check if all search results are empty/failed
    # NOTE: ToolExecutionCore wraps results as {"status": "success", "data": <actual_result>}
    all_empty = True
    for result in tool_results:
        wrapped_result = result.get("result", {})
        status = wrapped_result.get("status", "")
        # The actual tool output is inside "data" due to ToolExecutionCore wrapping
        actual_data = wrapped_result.get("data", {})

        # Check for any successful result with actual data
        if status == "success":
            # Check if there's actual content (various keys depending on search type)
            has_data = any([
                actual_data.get("matches"),
                actual_data.get("definition"),   # singular for symbols
                actual_data.get("definitions"),  # plural variant
                actual_data.get("usages"),
                actual_data.get("content"),
                actual_data.get("symbols"),
                actual_data.get("key_files"),
                actual_data.get("structure"),    # for modules
                actual_data.get("related_files"),
            ])
            if has_data:
                all_empty = False
                break

    if all_empty:
        # Get the queries that were tried for error message
        queries_tried = []
        for r in tool_results:
            wrapped = r.get("result", {})
            data = wrapped.get("data", {})
            query = data.get("query") or data.get("target") or "unknown"
            queries_tried.append(query)
        raise CodeAnalysisError(
            f"search_code returned no results for queries: {queries_tried} - cannot proceed"
        )
    explored_files = []

    for result in tool_results:
        wrapped_result = result.get("result", {})
        # Unwrap ToolExecutionCore wrapper: {"status": ..., "data": <actual_result>}
        tool_result = wrapped_result.get("data", wrapped_result) if isinstance(wrapped_result, dict) else {}
        # Extract files using convention-based approach
        files = _extract_files_from_result(tool_result)
        explored_files.extend(files)

    # Deduplicate while preserving order
    seen = set()
    unique_files = []
    for f in explored_files:
        if f not in seen:
            seen.add(f)
            unique_files.append(f)

    # CRITICAL: Extract code snippets for downstream LLM agents
    # This populates the {relevant_snippets} placeholder in synthesizer/critic/integration prompts
    snippets_str = _extract_snippets_from_tool_results(tool_results)

    # Store all results for downstream agents
    output["results"] = tool_results
    output["files_examined"] = unique_files
    output["snippets"] = snippets_str  # Required by synthesizer/critic/integration context builders

    return envelope


def synthesizer_mock_handler(envelope: Any) -> Dict[str, Any]:
    """Mock synthesis for testing."""
    # Get search targets from intent
    intent_output = envelope.outputs.get("intent", {})
    search_targets = intent_output.get("search_targets", ["unknown"])
    goals = intent_output.get("goals", ["Answer the query"])

    # Get execution results
    execution = envelope.outputs.get("execution", {})
    files_examined = execution.get("files_examined", [])

    # Build findings for each search target
    findings = []
    for target in search_targets[:3]:
        findings.append({
            "target": target,
            "summary": f"Found references to {target}",
            "citations": [f"{f}:1" for f in files_examined[:2]] if files_examined else ["src/main.py:1"],
        })

    # Build goal status
    goal_status = {}
    for goal in goals:
        goal_status[goal] = "satisfied" if files_examined else "partial"

    return {
        "findings": findings,
        "goal_status": goal_status,
        "gaps": [] if files_examined else ["No files found matching search targets"],
        "quality_score": 0.8 if files_examined else 0.3,
        "suggested_next_searches": [],
    }


def synthesizer_post_process(envelope: Any, output: Dict[str, Any], agent: Any = None) -> Any:
    """Store synthesizer output in metadata for downstream prompts.

    NOTE: We store fields directly in metadata so they're available to prompts
    via context.update(envelope.metadata) in jeeves-core. This avoids core changes.

    FALLBACK: If LLM returns {"response": "..."} instead of structured output,
    we create a minimal findings structure from the response.
    """
    # Handle malformed LLM output - LLM may return {"response": "..."} instead of structured fields
    findings = output.get("findings")
    quality_score = output.get("quality_score")
    gaps = output.get("gaps")

    if findings is None:
        # Fallback: try to create findings from "response" field
        response_text = output.get("response", "")
        if response_text:
            # Create a single finding from the response
            findings = [{
                "target": "query",
                "summary": response_text[:500] if len(response_text) > 500 else response_text,
                "citations": [],
            }]
            quality_score = quality_score or 0.5
        else:
            findings = []
            quality_score = quality_score or 0.0

    if gaps is None:
        gaps = [] if findings else ["No findings from search"]

    if quality_score is None:
        quality_score = 0.5 if findings else 0.0

    # Store synthesizer output as string for critic prompt
    envelope.metadata["synthesizer_output"] = str(findings) if findings else "No findings"

    # Also store structured data for downstream access
    envelope.metadata["synthesizer_findings"] = findings
    envelope.metadata["synthesizer_quality_score"] = quality_score
    envelope.metadata["synthesizer_gaps"] = gaps

    return envelope


def critic_mock_handler(envelope: Any) -> Dict[str, Any]:
    """Mock critic evaluation for testing.

    Critic provides FEEDBACK ONLY - no routing decisions.
    Integration agent uses this feedback to decide answer vs reintent.
    """
    # Get synthesizer output to evaluate
    synthesizer = envelope.outputs.get("synthesizer", {})
    quality_score = synthesizer.get("quality_score", 0.5)
    gaps = synthesizer.get("gaps", [])
    findings = synthesizer.get("findings", [])

    # Get execution results
    execution = envelope.outputs.get("execution", {})
    files_examined = execution.get("files_examined", [])

    # Assess quality and provide feedback (but don't route)
    issues = list(gaps)  # Copy gaps as issues

    if not files_examined:
        issues.append("No files were examined - search may have failed")

    if quality_score < 0.5:
        issues.append("Low confidence in findings - may need different search approach")

    # Provide recommendation (Integration decides what to do with it)
    if quality_score >= 0.7 and not gaps and files_examined:
        recommendation = "sufficient"
    elif quality_score < 0.3 or not files_examined:
        recommendation = "insufficient"
    else:
        recommendation = "partial"

    return {
        "recommendation": recommendation,  # sufficient/partial/insufficient
        "confidence": quality_score,
        "issues": issues,
        "refine_hint": "Try different search terms" if recommendation == "insufficient" else "",
    }


def critic_post_process(envelope: Any, output: Dict[str, Any], agent: Any = None) -> Any:
    """Store critic feedback for Integration to use.

    Critic provides feedback only - Integration decides routing.

    NOTE: We store fields directly in metadata so they're available to prompts
    via context.update(envelope.metadata) in jeeves-core. This avoids core changes.

    FALLBACK: If LLM returns {"response": "..."} instead of structured output,
    we check synthesizer quality and infer recommendation intelligently.
    Key insight: If synthesizer found good results, don't trigger reintent.
    """
    # Handle malformed LLM output - LLM may return {"response": "..."} instead of structured fields
    recommendation = output.get("recommendation")
    confidence = output.get("confidence")

    if recommendation is None:
        # Log the fallback trigger
        import structlog
            logger = structlog.get_logger()
        logger = get_logger()

        # Get synthesizer results to make intelligent fallback decision
        synthesizer = envelope.outputs.get("synthesizer", {})
        synth_quality = synthesizer.get("quality_score", 0.5)
        synth_findings = synthesizer.get("findings", [])
        synth_gaps = synthesizer.get("gaps", [])

        # Also check if we have files examined (search succeeded)
        execution = envelope.outputs.get("execution", {})
        files_examined = execution.get("files_examined", [])

        # Fallback: try to infer from "response" field if present
        response_text = output.get("response", "").lower()

        logger.info(
            "critic_fallback_triggered",
            envelope_id=envelope.envelope_id,
            synth_quality=synth_quality,
            synth_findings_count=len(synth_findings),
            synth_gaps_count=len(synth_gaps),
            files_examined_count=len(files_examined),
            has_response_text=bool(response_text),
        )

        # Intelligent fallback based on synthesizer results + response text
        if synth_quality >= 0.7 and synth_findings and not synth_gaps:
            # Synthesizer found good results with no gaps - likely sufficient
            recommendation = "sufficient"
            confidence = synth_quality
        elif response_text and any(word in response_text for word in ["sufficient", "complete", "adequate", "good"]):
            recommendation = "sufficient"
            confidence = confidence or 0.7
        elif response_text and any(word in response_text for word in ["insufficient", "fail", "missing", "none", "empty"]):
            recommendation = "insufficient"
            confidence = confidence or 0.3
        elif synth_quality >= 0.5 and files_examined:
            # We have files and reasonable quality - default to sufficient to avoid reintent loop
            recommendation = "sufficient"
            confidence = synth_quality
        elif not files_examined or synth_quality < 0.3:
            # No files found or very low quality - insufficient
            recommendation = "insufficient"
            confidence = confidence or 0.3
        else:
            # Default case - partial but with higher confidence to avoid aggressive reintent
            recommendation = "partial"
            confidence = confidence or 0.6

        logger.info(
            "critic_fallback_decision",
            envelope_id=envelope.envelope_id,
            recommendation=recommendation,
            confidence=confidence,
        )

    # Store critic fields directly in metadata for prompt template access
    # These become {critic_recommendation}, {critic_feedback} in prompts
    envelope.metadata["critic_recommendation"] = recommendation

    # Format critic feedback as string for prompt
    issues = output.get("issues", [])
    refine_hint = output.get("refine_hint", "")
    feedback_parts = []
    if issues:
        feedback_parts.append(f"Issues: {'; '.join(issues)}")
    if refine_hint:
        feedback_parts.append(f"Hint: {refine_hint}")
    envelope.metadata["critic_feedback"] = "\n".join(feedback_parts) if feedback_parts else "No issues"

    # Store complete cycle data for potential reintent
    # Integration will pass this to Intent if it decides to reintent
    # NOTE: Use "_cycle_data" (not "cycle_context") to avoid collision with prompt display string
    envelope.metadata["_cycle_data"] = {
        "critic_feedback": {
            "recommendation": output.get("recommendation", "partial"),
            "confidence": output.get("confidence", 0.5),
            "issues": output.get("issues", []),
            "refine_hint": output.get("refine_hint", ""),
        },
        "prior_intent": envelope.outputs.get("intent", {}),
        "prior_search_targets": envelope.outputs.get("intent", {}).get("search_targets", []),
        "files_examined": envelope.outputs.get("execution", {}).get("files_examined", []),
        "synthesizer_findings": envelope.outputs.get("synthesizer", {}).get("findings", []),
    }

    # Store files_examined in metadata for Integration prompt
    files_examined = envelope.outputs.get("execution", {}).get("files_examined", [])
    envelope.metadata["files_examined"] = ", ".join(files_examined) if files_examined else "None examined"

    # Note: synthesizer_output is already stored by synthesizer_post_process

    return envelope


def integration_mock_handler(envelope: Any) -> Dict[str, Any]:
    """Mock integration for testing.

    Integration decides: answer OR reintent based on critic feedback.
    """
    synthesizer = envelope.outputs.get("synthesizer", {})
    execution = envelope.outputs.get("execution", {})
    critic = envelope.outputs.get("critic", {})
    cycle_context = envelope.metadata.get("_cycle_data", {})

    # Get critic's assessment
    recommendation = critic.get("recommendation", "partial")
    issues = critic.get("issues", [])

    # Get files_examined from execution output
    files_examined = execution.get("files_examined", [])

    # Integration decides: answer or reintent
    # - "sufficient" from critic → answer
    # - "insufficient" with no files → reintent (search failed)
    # - "partial" → answer with caveats (don't loop forever)

    if recommendation == "insufficient" and not files_examined:
        # Need to reintent - search completely failed
        return {
            "action": "reintent",
            "reason": "Search produced no results - need different search targets",
            "cycle_context": cycle_context,
        }
    else:
        # Answer (even if partial)
        findings = synthesizer.get("findings", [])
        summary = "; ".join(f.get("summary", "") for f in findings[:3]) if findings else "Analysis complete"

        response = f"Code Analysis Result:\n\n{summary}"
        if issues and recommendation != "sufficient":
            response += f"\n\nNote: {'; '.join(issues[:2])}"

        return {
            "action": "answer",
            "final_response": response,
            "citations": [],
            "files_examined": files_examined,
        }


def integration_post_process(envelope: Any, output: Dict[str, Any], agent: Any = None) -> Any:
    """Handle integration decision: answer or reintent.

    If action=answer: Mark as complete
    If action=reintent: Pass cycle context to intent (routing handled by routing_rules)

    NOTE: We store formatted context in metadata so it's available to prompts
    via context.update(envelope.metadata) in jeeves-core. This avoids core changes.

    REINTENT LIMIT: Enforces MAX_REINTENT_CYCLES to prevent infinite loops.
    """
    from jeeves_mission_system.contracts_core import TerminalReason
    import structlog
            logger = structlog.get_logger()

    logger = get_logger()
    action = output.get("action", "answer")

    # Track reintent count
    reintent_count = envelope.metadata.get("reintent_count", 0)

    # Log the integration decision and output structure
    logger.info(
        "integration_decision",
        envelope_id=envelope.envelope_id,
        action=action,
        reintent_count=reintent_count,
        max_reintent_cycles=MAX_REINTENT_CYCLES,
        has_final_response="final_response" in output,
        has_reason="reason" in output,
        output_keys=list(output.keys()) if isinstance(output, dict) else [],
    )

    # Enforce reintent limit - prevent infinite loops
    # NOTE: Check >= MAX - 1 because reintent_count is checked BEFORE increment.
    # If we've already done (MAX-1) reintents, the next one would hit MAX, so force answer now.
    if action == "reintent" and reintent_count >= MAX_REINTENT_CYCLES - 1:
        logger.warning(
            "reintent_limit_reached",
            envelope_id=envelope.envelope_id,
            reintent_count=reintent_count,
            max_reintent_cycles=MAX_REINTENT_CYCLES,
        )
        # Force answer with best-effort response
        action = "answer"
        output["action"] = "answer"
        output["final_response"] = output.get("final_response") or (
            "I was unable to find the specific code you're looking for after multiple search attempts. "
            "The search terms may not match the codebase, or the code may not exist. "
            "Please try rephrasing your question with different terms or specifying file paths directly."
        )

    # Validate output based on action
    if action == "answer" and "final_response" not in output:
        logger.error(
            "integration_missing_final_response",
            envelope_id=envelope.envelope_id,
            output_keys=list(output.keys()),
            hint="LLM output did not include required 'final_response' field for action=answer",
        )

    if action == "reintent":
        # Increment reintent counter
        new_count = reintent_count + 1
        envelope.metadata["reintent_count"] = new_count

        logger.info(
            "reintent_triggered",
            envelope_id=envelope.envelope_id,
            reintent_count=new_count,
            max_reintent_cycles=MAX_REINTENT_CYCLES,
        )

        # Pass cycle context to Intent for the next cycle
        # The routing_rules will handle the actual routing to intent
        cycle_context = output.get("cycle_context", envelope.metadata.get("_cycle_data", {}))
        reason = output.get("reason", "Need different search approach")

        envelope.metadata["reintent_context"] = {
            "prior_cycle": cycle_context,
            "reason": reason,
        }

        # Format context_summary for Intent prompt on reintent
        # This appends reintent info to the existing context_summary
        prior_targets = cycle_context.get("prior_search_targets", [])
        prior_files = cycle_context.get("files_examined", [])
        refine_hint = cycle_context.get("critic_feedback", {}).get("refine_hint", "")

        reintent_info = f"""
**REINTENT - Prior search failed. Extract DIFFERENT search targets.**
- Prior search targets (did not work): {prior_targets}
- Files found: {len(prior_files)}
- Reason for reintent: {reason}
- Hint: {refine_hint}

Do NOT repeat the same search targets. Try different keywords, synonyms, or approaches."""

        # Append to existing context_summary or create new
        existing_summary = envelope.metadata.get("context_summary", "")
        envelope.metadata["context_summary"] = existing_summary + reintent_info

        # Don't mark as terminated - routing will send to intent
        return envelope
    else:
        # Mark as complete
        envelope.terminated = True
        envelope.termination_reason = "completed"
        envelope.terminal_reason = TerminalReason.COMPLETED
        return envelope


# ─────────────────────────────────────────────────────────────────
# PIPELINE CONFIGURATION
# ─────────────────────────────────────────────────────────────────

CODE_ANALYSIS_PIPELINE = PipelineConfig(
    name="code_analysis",
    max_iterations=5,
    max_llm_calls=30,
    max_agent_hops=50,
    enable_arbiter=False,  # Read-only pipeline, no arbiter needed
    # Capability-defined resume stages (not hardcoded in runtime)
    clarification_resume_stage="intent",  # REINTENT architecture: clarifications go through Intent
    confirmation_resume_stage="executor",  # Confirmations resume at tool execution
    agents=[
        # ─── Agent 1: Perception ───
        AgentConfig(
            name="perception",
            stage_order=0,
            has_llm=False,
            has_tools=False,
            tool_access=ToolAccess.READ,
            output_key="perception",
            pre_process=perception_pre_process,
            mock_handler=perception_mock_handler,
            default_next="intent",
        ),

        # ─── Agent 2: Intent ───
        AgentConfig(
            name="intent",
            stage_order=1,
            has_llm=True,
            model_role="planner",
            prompt_key="code_analysis.intent",
            output_key="intent",
            required_output_fields=["intent", "goals", "search_targets"],
            max_tokens=8000,
            temperature=0.3,
            pre_process=intent_pre_process,
            mock_handler=intent_mock_handler,
            post_process=intent_post_process,
            routing_rules=[
                RoutingRule("clarification_needed", True, "clarification"),
            ],
            default_next="planner",
        ),

        # ─── Agent 3: Planner ───
        AgentConfig(
            name="planner",
            stage_order=2,
            has_llm=True,
            model_role="planner",
            prompt_key="code_analysis.planner",
            tool_access=ToolAccess.READ,  # For tool listing
            output_key="plan",
            required_output_fields=["steps"],
            max_tokens=8000,
            temperature=0.3,
            pre_process=planner_pre_process,
            mock_handler=planner_mock_handler,
            default_next="executor",
        ),

        # ─── Agent 4: Executor (Traverser) ───
        AgentConfig(
            name="executor",
            stage_order=3,
            has_llm=False,
            has_tools=True,
            tool_access=ToolAccess.ALL,
            output_key="execution",
            pre_process=executor_pre_process,
            post_process=executor_post_process,
            default_next="synthesizer",
        ),

        # ─── Agent 5: Synthesizer ───
        AgentConfig(
            name="synthesizer",
            stage_order=4,
            has_llm=True,
            model_role="planner",
            prompt_key="code_analysis.synthesizer",
            output_key="synthesizer",
            required_output_fields=["findings", "goal_status"],
            max_tokens=8000,
            temperature=0.3,
            pre_process=synthesizer_pre_process,
            mock_handler=synthesizer_mock_handler,
            post_process=synthesizer_post_process,
            default_next="critic",
        ),

        # ─── Agent 6: Critic ───
        # Critic provides FEEDBACK ONLY - no routing decisions
        # Integration uses critic feedback to decide answer vs reintent
        AgentConfig(
            name="critic",
            stage_order=5,
            has_llm=True,
            model_role="critic",
            prompt_key="code_analysis.critic",
            output_key="critic",
            required_output_fields=["recommendation", "confidence"],
            max_tokens=8000,
            temperature=0.2,
            pre_process=critic_pre_process,
            mock_handler=critic_mock_handler,
            post_process=critic_post_process,
            default_next="integration",
        ),

        # ─── Agent 7: Integration ───
        # Integration DECIDES: answer OR reintent (with cycle context)
        # When action=answer, must include final_response
        # When action=reintent, must include reason
        AgentConfig(
            name="integration",
            stage_order=6,
            has_llm=True,
            model_role="planner",
            prompt_key="code_analysis.integration",
            tool_access=ToolAccess.WRITE,
            output_key="integration",
            required_output_fields=["action"],  # action: answer|reintent
            max_tokens=8000,
            temperature=0.3,
            pre_process=integration_pre_process,
            mock_handler=integration_mock_handler,
            post_process=integration_post_process,
            routing_rules=[
                RoutingRule("action", "reintent", "intent"),  # Route to intent on reintent
            ],
            default_next="end",
        ),
    ],
)


# ─────────────────────────────────────────────────────────────────
# PIPELINE MODE VARIANTS
# ─────────────────────────────────────────────────────────────────
# Per k8s-aligned architecture: PipelineConfig IS the mode.
# Different modes = different pipeline configurations.

# Standard mode: faster, skips critic validation
# Use for simple queries where quick responses are preferred
CODE_ANALYSIS_PIPELINE_STANDARD = PipelineConfig(
    name="code_analysis_standard",
    max_iterations=3,  # Fewer iterations
    max_llm_calls=20,  # Fewer LLM calls
    max_agent_hops=30,
    enable_arbiter=False,
    clarification_resume_stage="intent",
    confirmation_resume_stage="executor",
    agents=[
        # Perception (same as full)
        AgentConfig(
            name="perception",
            stage_order=0,
            has_llm=False,
            has_tools=False,
            tool_access=ToolAccess.READ,
            output_key="perception",
            pre_process=perception_pre_process,
            mock_handler=perception_mock_handler,
            default_next="intent",
        ),
        # Intent (same as full)
        AgentConfig(
            name="intent",
            stage_order=1,
            has_llm=True,
            model_role="planner",
            prompt_key="code_analysis.intent",
            output_key="intent",
            required_output_fields=["intent", "goals", "search_targets"],
            max_tokens=8000,
            temperature=0.3,
            pre_process=intent_pre_process,
            mock_handler=intent_mock_handler,
            post_process=intent_post_process,
            routing_rules=[
                RoutingRule("clarification_needed", True, "clarification"),
            ],
            default_next="planner",
        ),
        # Planner (same as full)
        AgentConfig(
            name="planner",
            stage_order=2,
            has_llm=True,
            model_role="planner",
            prompt_key="code_analysis.planner",
            tool_access=ToolAccess.READ,
            output_key="plan",
            required_output_fields=["steps"],
            max_tokens=8000,
            temperature=0.3,
            pre_process=planner_pre_process,
            mock_handler=planner_mock_handler,
            default_next="executor",
        ),
        # Executor (same as full)
        AgentConfig(
            name="executor",
            stage_order=3,
            has_llm=False,
            has_tools=True,
            tool_access=ToolAccess.ALL,
            output_key="execution",
            pre_process=executor_pre_process,
            post_process=executor_post_process,
            default_next="synthesizer",
        ),
        # Synthesizer (same as full)
        AgentConfig(
            name="synthesizer",
            stage_order=4,
            has_llm=True,
            model_role="planner",
            prompt_key="code_analysis.synthesizer",
            output_key="synthesizer",
            required_output_fields=["findings", "goal_status"],
            max_tokens=8000,
            temperature=0.3,
            pre_process=synthesizer_pre_process,
            mock_handler=synthesizer_mock_handler,
            post_process=synthesizer_post_process,
            default_next="integration",  # Skip critic in standard mode
        ),
        # Integration (modified - no critic feedback in standard mode)
        AgentConfig(
            name="integration",
            stage_order=5,  # Stage 5 (not 6) since critic is skipped
            has_llm=True,
            model_role="planner",
            prompt_key="code_analysis.integration",
            tool_access=ToolAccess.WRITE,
            output_key="integration",
            required_output_fields=["action"],
            max_tokens=8000,
            temperature=0.3,
            pre_process=integration_pre_process,
            mock_handler=integration_mock_handler,
            post_process=integration_post_process,
            routing_rules=[
                RoutingRule("action", "reintent", "intent"),
            ],
            default_next="end",
        ),
    ],
)

# Full mode: thorough, with critic validation
# This is the default CODE_ANALYSIS_PIPELINE
CODE_ANALYSIS_PIPELINE_FULL = CODE_ANALYSIS_PIPELINE

# Mode registry
PIPELINE_MODES: Dict[str, PipelineConfig] = {
    "standard": CODE_ANALYSIS_PIPELINE_STANDARD,
    "full": CODE_ANALYSIS_PIPELINE_FULL,
}


def get_pipeline_for_mode(mode: str = "full") -> PipelineConfig:
    """Get pipeline configuration for a specific mode.

    Args:
        mode: Pipeline mode ("standard" or "full")

    Returns:
        PipelineConfig for the specified mode

    Raises:
        ValueError: If mode is not recognized
    """
    if mode not in PIPELINE_MODES:
        raise ValueError(f"Unknown pipeline mode: {mode}. Valid modes: {list(PIPELINE_MODES.keys())}")
    return PIPELINE_MODES[mode]


def get_code_analysis_pipeline() -> PipelineConfig:
    """Get the default (full) code analysis pipeline configuration."""
    return CODE_ANALYSIS_PIPELINE


__all__ = [
    "CODE_ANALYSIS_PIPELINE",
    "CODE_ANALYSIS_PIPELINE_STANDARD",
    "CODE_ANALYSIS_PIPELINE_FULL",
    "PIPELINE_MODES",
    "CodeAnalysisError",
    "get_code_analysis_pipeline",
    "get_pipeline_for_mode",
]
