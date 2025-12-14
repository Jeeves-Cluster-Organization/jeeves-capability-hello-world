"""
Code Analysis Pipeline Configuration - Declarative agent definitions.

This replaces the 7 concrete agent classes with configuration-driven definitions.
The UnifiedRuntime uses this config to execute the pipeline.

Migration:
- CodeAnalysisPerceptionAgent → AgentConfig(name="perception", ...)
- CodeAnalysisIntentAgent → AgentConfig(name="intent", has_llm=True, ...)
- etc.

Capability-specific logic (prompts, mock handlers, normalizers) is provided
via hook functions defined here.
"""

from typing import Any, Dict, List, Optional
from jeeves_mission_system.contracts_core import (
    AgentConfig,
    PipelineConfig,
    RoutingRule,
    ToolAccess,
    TerminalReason,
)


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
    """Initialize goals after intent."""
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
    if goals:
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
            from jeeves_mission_system.adapters import get_logger
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


def executor_post_process(envelope: Any, output: Dict[str, Any], agent: Any = None) -> Any:
    """Post-process executor results."""
    # Update traversal state in metadata from tool_results
    tool_results = output.get("tool_results", [])
    explored_files = []

    for result in tool_results:
        tool_result = result.get("result", {})
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

    if "traversal_state" not in envelope.metadata:
        envelope.metadata["traversal_state"] = {}
    envelope.metadata["traversal_state"]["explored_files"] = unique_files

    # Store results in output for downstream agents
    output["results"] = tool_results
    output["files_examined"] = unique_files

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
    """
    # Store synthesizer output as string for critic prompt
    findings = output.get("findings", [])
    envelope.metadata["synthesizer_output"] = str(findings) if findings else "No findings"

    # Also store structured data for downstream access
    envelope.metadata["synthesizer_findings"] = findings
    envelope.metadata["synthesizer_quality_score"] = output.get("quality_score", 0.5)
    envelope.metadata["synthesizer_gaps"] = output.get("gaps", [])

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
    """
    # Store critic fields directly in metadata for prompt template access
    # These become {critic_recommendation}, {critic_feedback} in prompts
    envelope.metadata["critic_recommendation"] = output.get("recommendation", "partial")

    # Format critic feedback as string for prompt
    issues = output.get("issues", [])
    refine_hint = output.get("refine_hint", "")
    feedback_parts = []
    if issues:
        feedback_parts.append(f"Issues: {'; '.join(issues)}")
    if refine_hint:
        feedback_parts.append(f"Hint: {refine_hint}")
    envelope.metadata["critic_feedback"] = "\n".join(feedback_parts) if feedback_parts else "No issues"

    # Store complete cycle context for potential reintent
    # Integration will pass this to Intent if it decides to reintent
    envelope.metadata["cycle_context"] = {
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
    cycle_context = envelope.metadata.get("cycle_context", {})

    # Get critic's assessment
    recommendation = critic.get("recommendation", "partial")
    issues = critic.get("issues", [])

    # Get files_examined from execution output or traversal_state metadata
    files_examined = (
        execution.get("files_examined", []) or
        envelope.metadata.get("traversal_state", {}).get("explored_files", [])
    )

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
    """
    from jeeves_mission_system.contracts_core import TerminalReason

    action = output.get("action", "answer")

    if action == "reintent":
        # Pass cycle context to Intent for the next cycle
        # The routing_rules will handle the actual routing to intent
        cycle_context = output.get("cycle_context", envelope.metadata.get("cycle_context", {}))
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
    max_iterations=3,
    max_llm_calls=10,
    max_agent_hops=21,
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
            required_output_fields=["intent", "goals"],
            max_tokens=2000,
            temperature=0.3,
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
            max_tokens=2500,
            temperature=0.3,
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
            max_tokens=2000,
            temperature=0.3,
            mock_handler=synthesizer_mock_handler,
            post_process=synthesizer_post_process,  # Store output in metadata for critic
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
            required_output_fields=["recommendation"],  # Changed from verdict
            max_tokens=2500,
            temperature=0.2,
            mock_handler=critic_mock_handler,
            post_process=critic_post_process,
            # NO routing rules - critic provides feedback only
            default_next="integration",
        ),

        # ─── Agent 7: Integration ───
        # Integration DECIDES: answer OR reintent (with cycle context)
        AgentConfig(
            name="integration",
            stage_order=6,
            has_llm=True,
            model_role="planner",
            prompt_key="code_analysis.integration",
            tool_access=ToolAccess.WRITE,
            output_key="integration",
            required_output_fields=["action"],  # action: answer|reintent
            max_tokens=2000,
            temperature=0.3,
            mock_handler=integration_mock_handler,
            post_process=integration_post_process,
            routing_rules=[
                RoutingRule("action", "reintent", "intent"),  # Route to intent on reintent
            ],
            default_next="end",
        ),
    ],
)


def get_code_analysis_pipeline() -> PipelineConfig:
    """Get the code analysis pipeline configuration."""
    return CODE_ANALYSIS_PIPELINE


__all__ = [
    "CODE_ANALYSIS_PIPELINE",
    "get_code_analysis_pipeline",
]
