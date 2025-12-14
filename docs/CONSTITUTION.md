# Jeeves Code Analysis Capability Constitution

**Status:** Governing Document
**Updated:** 2025-12-14

---

## Overview

This document defines the constitutional rules for the **jeeves-capability-code-analyser** - a 7-agent pipeline for read-only code analysis with citation-backed responses.

> **Detailed Rules:** See [jeeves-capability-code-analyser/CONSTITUTION.md](../jeeves-capability-code-analyser/CONSTITUTION.md) for the complete capability constitution.

---

## Core Principles

### P1: Accuracy First

Every claim requires `[file:line]` citation from tool execution.

**Rules:**
- Never hallucinate code that wasn't read
- Always cite source file and line number
- Prefer "I don't know" over guessing

### P2: Code Context Priority

Read source before claiming.

**Rules:**
- Execute read tools before making claims
- Verify symbols exist before describing them
- Check file contents before analyzing structure

### P3: Bounded Efficiency

Be efficient within limits.

**Rules:**
- Respect context bounds (max tokens, max files)
- Degrade gracefully when limits reached
- Prioritize high-value information

**Hierarchy:** P1 > P2 > P3 (when principles conflict)

---

## Architecture Rules

### R1: Configuration-Driven Agents

Agents are defined via `AgentConfig` in `pipeline_config.py`, not as concrete classes.

```python
# Correct
AgentConfig(
    name="intent",
    has_llm=True,
    model_role="planner",
    prompt_key="code_analysis.intent",
)

# Wrong - No concrete agent classes
class CodeAnalysisIntentAgent(Agent):
    pass
```

### R2: Hook Functions for Logic

Capability-specific logic is provided via hook functions:

```python
AgentConfig(
    name="intent",
    post_process=intent_post_process,
    mock_handler=intent_mock_handler,
)
```

### R3: Import from Protocols

Always import agent types from `jeeves_protocols`:

```python
# Correct
from jeeves_protocols import (
    AgentConfig,
    PipelineConfig,
    GenericEnvelope,
)

# Wrong
from coreengine.agents import Agent
```

### R4: Tool Boundary

Only 5 tools exposed to agents. Internal tools are used by `analyze` internally.

**Exposed Tools:**
- `analyze` - Primary orchestration tool
- `read_code` - File reading with retry
- `find_related` - Semantic search
- `git_status` - Repository state
- `list_tools` - Tool discovery

### R5: Capability Registration

The capability MUST register its resources at application startup:

```python
from jeeves_capability_code_analyser import register_capability

# Call before infrastructure initialization
register_capability()
```

---

## Pipeline Configuration

| # | Agent | has_llm | has_tools | Purpose |
|---|-------|---------|-----------|---------|
| 1 | perception | False | False | Normalize query, load context |
| 2 | intent | True | False | Classify query type |
| 3 | planner | True | False | Plan tool execution |
| 4 | executor | False | True | Execute read-only tools |
| 5 | synthesizer | True | False | Synthesize findings |
| 6 | critic | True | False | Validate against code |
| 7 | integration | True | False | Build final response |

---

## Context Bounds

| Limit | Value | Purpose |
|-------|-------|---------|
| `max_tree_depth` | 10 | Prevent runaway exploration |
| `max_file_slice_tokens` | 4000 | Context window management |
| `max_grep_results` | 50 | Limit search volume |
| `max_files_per_query` | 10 | Bound per-query scope |
| `max_total_code_tokens` | 25000 | Total budget per query |

---

## Dependency Rules

### What This Capability Imports

1. **From jeeves_protocols** (required)
   - `AgentConfig`, `PipelineConfig`, `GenericEnvelope`
   - `CapabilityResourceRegistry`, `CapabilityModeConfig`
   - Protocol definitions

2. **From jeeves_mission_system** (required)
   - `contracts` - Tool catalog, logging, persistence
   - `adapters` - Logger, database

3. **From jeeves_avionics** (for infrastructure)
   - `wiring.py` - ToolExecutor
   - `settings.py` - Configuration

### What This Capability Exports

1. **registration.py**
   - `register_capability()` - Resource registration
   - `CAPABILITY_ID` - "code_analysis"
   - `get_schema_path()` - Database schema path

2. **pipeline_config.py**
   - `CODE_ANALYSIS_PIPELINE` - Pipeline configuration
   - Hook functions for each agent

3. **tools/**
   - `initialize_all_tools()` - Tool initialization
   - All code analysis tools

---

## Forbidden Patterns

- Creating concrete agent classes
- Importing from `coreengine/` directly
- Hallucinating code without tool execution
- Bypassing context bounds
- Modifying files (read-only operations only)

---

*This constitution governs the jeeves-capability-code-analyser package.*
