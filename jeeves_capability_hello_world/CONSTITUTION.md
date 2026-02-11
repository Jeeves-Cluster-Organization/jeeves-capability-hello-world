# Hello World Capability Constitution

## Overview

This document defines the architectural rules and ownership boundaries for the `jeeves-capability-hello-world` capability. It ensures compliance with the Jeeves Constitution R7 patterns while keeping the implementation minimal and focused.

## Capability Identity

- **Capability ID**: `hello_world`
- **Version**: `0.1.0`
- **Purpose**: Minimal 3-agent chatbot demonstrating multi-agent orchestration patterns
- **Scope**: General-purpose conversational AI template

## Architecture

### 3-Agent Pipeline

```
User Message
    |
UNDERSTAND (LLM)     <- Intent classification
    |
THINK (Tools)        <- Tool execution (optional)
    |
RESPOND (LLM)        <- Response synthesis
    |
Response to User
```

### Agent Responsibilities

| Agent | Has LLM | Layer | Purpose |
|-------|---------|-------|---------|
| Understand | Yes | Perception | Classify intent, decide if tools needed |
| Think | No | Execution | Execute tools based on intent |
| Respond | Yes | Synthesis | Generate final response |

## Import Boundaries (R7)

### Allowed Imports

Capability code MAY import from:
- `jeeves_infra.protocols` - Type definitions, protocols, pipeline types
- `jeeves_infra.bootstrap` - `create_app_context()` (eagerly provisions kernel, LLM, config)
- `jeeves_infra.wiring` - `create_tool_executor` (tool executor framework)
- `jeeves_infra.settings` - Settings management
- `jeeves_infra.kernel_client` - `KernelClient` class (instance via AppContext)
- `jeeves_infra.orchestrator` - Event orchestration

### Forbidden Imports

Capability code MUST NOT import from:
- `jeeves_infra.llm.*` directly - LLM factory provided via `AppContext.llm_provider_factory`
- `jeeves_infra.gateway.*` - Internal server infrastructure
- `coreengine.*` - Rust kernel accessed via KernelClient only

**Apps MUST NOT** import from `jeeves_infra` directly (except `bootstrap`). Apps use the capability layer entry point.

### Correct Pattern (App)

```python
# Constitution R7: Register capability FIRST
from jeeves_capability_hello_world import register_capability
register_capability()

# Bootstrap provisions everything (K8s-style eager provisioning)
from jeeves_infra.bootstrap import create_app_context
app_context = create_app_context()

# Capability creates fully-wired service from AppContext
from jeeves_capability_hello_world.capability.wiring import create_hello_world_from_app_context
service = create_hello_world_from_app_context(app_context)
```

## Tool Suite

### Available Tools

| Tool ID | Category | Risk Level | Description |
|---------|----------|------------|-------------|
| `get_time` | Utility | Read-only | Get current date/time |
| `list_tools` | Introspection | Read-only | List available tools |

### Tool Access Control

- All tools are READ-ONLY (no state modification)
- Tools are registered via `CapabilityToolCatalog` in `capability/wiring.py`
- Tool catalog provides metadata for access control

## Ownership Rules

### Capability Owns

1. **Pipeline Configuration** (`pipeline_config.py`)
   - Agent definitions
   - Routing rules
   - Generation parameters

2. **Prompts** (`prompts/chatbot/`)
   - Intent classification prompts
   - Response synthesis prompts
   - Streaming-specific prompts

3. **Tools** (`tools/`)
   - Tool implementations
   - Tool catalog and metadata
   - Tool registration

4. **Orchestration** (`orchestration/`)
   - Service wrapper (ChatbotService)
   - Wiring and dependency injection
   - Domain types

5. **Database** (`database/`)
   - Concrete database backends (SQLite, Postgres)
   - Schema definitions
   - Domain-specific services (code indexer, etc.)

### Infrastructure Owns (jeeves_infra)

- LLM provider factory
- Tool executor framework
- Settings management
- Logging infrastructure
- Pipeline runner
- Event orchestration
- Bootstrap / AppContext

## Registration Contract

### Startup Sequence

1. Call `register_capability()` at module/startup level
2. Call `create_app_context()` for bootstrap (provisions kernel, LLM, config)
3. Call `create_hello_world_from_app_context(app_context)` for fully-wired service

## Principles

### P1: NLP-First

- Queries are answered via conversation, not code execution
- LLM generates natural language responses
- Tool results are synthesized into human-readable text

### P2: Accuracy First

- No hallucination of tool results
- Citations included when web search used
- Confidence levels reported in responses

## Amendments

### Amendment I: Minimal Scope

This capability intentionally omits:
- Rust kernel IPC servicer (Gradio-only deployment)
- Control Tower integration (no event tracking)
- Persistence layer (stateless)
- Complex tool suites (3 tools only)

### Amendment II: Template Purpose

This capability serves as a template for building new capabilities:
- Follow the same registration pattern
- Follow the same import boundaries
- Extend tools and prompts as needed
