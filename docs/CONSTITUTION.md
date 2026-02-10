# Jeeves Hello World Capability Constitution

**Status:** Governing Document
**Updated:** 2025-01-27

---

## Overview

This document defines the constitutional rules for the **jeeves-capability-hello-world** - a 3-agent pipeline for general-purpose chatbot conversations.

> **Detailed Rules:** See [jeeves_capability_hello_world/CONSTITUTION.md](../jeeves_capability_hello_world/CONSTITUTION.md) for the complete capability constitution.

---

## Core Principles

### P1: Helpful Responses

Every response should be helpful, accurate, and relevant to the user's query.

**Rules:**
- Provide clear, concise answers
- Acknowledge uncertainty when appropriate
- Cite sources when using web search results

### P2: Tool Usage

Use tools appropriately based on user intent.

**Rules:**
- Use web search for current events and factual queries
- Don't use tools when not needed (e.g., creative writing, general chat)
- Report tool errors gracefully

### P3: Bounded Efficiency

Be efficient within limits.

**Rules:**
- Respect context bounds (max tokens)
- Keep responses focused and relevant
- Don't over-explain simple concepts

**Hierarchy:** P1 > P2 > P3 (when principles conflict)

---

## Architecture Rules

### R1: Configuration-Driven Agents

Agents are defined via `AgentConfig` in `pipeline_config.py`, not as concrete classes.

```python
# Correct
AgentConfig(
    name="understand",
    has_llm=True,
    model_role="planner",
    prompt_key="hello_world.understand",
)

# Wrong - No concrete agent classes
class HelloWorldUnderstandAgent(Agent):
    pass
```

### R2: Hook Functions for Logic

Capability-specific logic is provided via hook functions:

```python
AgentConfig(
    name="understand",
    post_process=understand_post_process,
    mock_handler=understand_mock_handler,
)
```

### R3: Import from Protocols

Always import agent types from `protocols`:

```python
# Correct
from protocols import (
    AgentConfig,
    PipelineConfig,
    GenericEnvelope,
)

# Wrong
from coreengine.agents import Agent
```

### R4: Tool Boundary

Only 3 tools exposed to agents:

**Exposed Tools:**
- `web_search` - Search the web for information
- `get_time` - Get current date/time
- `list_tools` - Tool discovery

### R5: Capability Registration

The capability MUST register its resources at application startup:

```python
from jeeves_capability_hello_world import register_capability

# Call before infrastructure initialization
register_capability()
```

### R6: Pipeline Topology

Capabilities may use any supported topology:
- **Linear:** Sequential agent chain (simplest)
- **Branching:** Conditional routing via `RoutingRule`
- **DAG:** Parallel execution via `requires`/`after`/`JoinStrategy`

The kernel evaluates routing rules; capabilities define them declaratively.

---

## Pipeline Configuration

| # | Agent | has_llm | has_tools | Purpose |
|---|-------|---------|-----------|---------|
| 1 | understand | True | False | Analyze user intent, plan approach |
| 2 | think | False | True | Execute tools if needed |
| 3 | respond | True | False | Synthesize response |

---

## Context Bounds

| Limit | Value | Purpose |
|-------|-------|---------|
| `max_tokens` | 4000 | Response length limit |
| `max_search_results` | 5 | Limit search volume |
| `max_iterations` | 2 | Bound pipeline iterations |

---

## Dependency Rules

### What This Capability Imports

1. **From protocols** (required)
   - `AgentConfig`, `PipelineConfig`, `GenericEnvelope`
   - `CapabilityResourceRegistry`, `CapabilityModeConfig`
   - Protocol definitions

2. **From jeeves_infra** (infrastructure and orchestration)
   - `contracts` - Tool catalog, logging, persistence
   - `adapters` - Logger, database

3. **From jeeves_infra** (for infrastructure, via adapters preferred)
   - `wiring.py` - ToolExecutor
   - `settings.py` - Configuration

### What This Capability Exports

1. **registration.py**
   - `register_capability()` - Resource registration
   - `CAPABILITY_ID` - "hello_world"
   - `get_schema_path()` - Database schema path

2. **pipeline_config.py**
   - `HELLO_WORLD_PIPELINE` - Pipeline configuration
   - Hook functions for each agent

3. **tools/**
   - `initialize_all_tools()` - Tool initialization
   - All hello world tools

---

## Forbidden Patterns

- Creating concrete agent classes
- Importing from `coreengine/` directly
- Making external API calls without user consent
- Bypassing context bounds

---

*This constitution governs the jeeves-capability-hello-world package.*
