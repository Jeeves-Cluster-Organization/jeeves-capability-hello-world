# Jeeves Hello World Capability Constitution

**Status:** Governing Document
**Updated:** 2025-01-27

---

## Overview

This document defines the constitutional rules for the **jeeves-capability-hello-world** - a 3-agent pipeline for general-purpose chatbot conversations.

> **Complete Rules:** See [jeeves_capability_hello_world/CONSTITUTION.md](../jeeves_capability_hello_world/CONSTITUTION.md) for the full capability constitution including import boundaries, tool suite, ownership rules, registration contract, and amendment history.

---

## Core Principles

### P1: Helpful Responses

Every response should be helpful, accurate, and relevant to the user's query.

### P2: Tool Usage

Use tools appropriately based on user intent. Don't use tools when not needed (e.g., creative writing, general chat). Report tool errors gracefully.

### P3: Bounded Efficiency

Be efficient within limits. Respect context bounds, keep responses focused, and don't over-explain simple concepts.

**Hierarchy:** P1 > P2 > P3 (when principles conflict)

---

## Architecture Summary

### 3-Agent Pipeline

| # | Agent | has_llm | has_tools | Purpose |
|---|-------|---------|-----------|---------|
| 1 | understand | True | False | Analyze user intent, plan approach |
| 2 | think | False | True | Execute tools if needed |
| 3 | respond | True | False | Synthesize response |

### Key Rules

- **R1:** Agents are defined via `AgentConfig` in `pipeline_config.py`, not as concrete classes.
- **R2:** Capability-specific logic is provided via hook functions (`pre_process`, `post_process`, `mock_handler`).
- **R3:** Always import agent types from `protocols`, never from `coreengine`.
- **R5:** The capability MUST call `register_capability()` before infrastructure initialization.
- **R6:** Capabilities may use linear, branching, or DAG pipeline topologies.

### Dependency Rules

- **Allowed:** imports from `protocols`, `jeeves_core` (infrastructure and orchestration)
- **Forbidden:** imports from `coreengine/` directly, cross-capability imports

---

*For the complete constitution, see [jeeves_capability_hello_world/CONSTITUTION.md](../jeeves_capability_hello_world/CONSTITUTION.md).*
