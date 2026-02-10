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
- `jeeves_infra.wiring` - Factory functions (create_llm_provider_factory, create_tool_executor)
- `jeeves_infra.settings` - Settings management
- `jeeves_infra.bootstrap` - AppContext creation
- `jeeves_infra.kernel_client` - Rust kernel communication
- `jeeves_infra.orchestrator` - Event orchestration

### Forbidden Imports

Capability code MUST NOT import from:
- `jeeves_infra.llm.*` directly - Use `jeeves_infra.wiring` factories instead
- `jeeves_infra.gateway.*` - Internal server infrastructure
- `coreengine.*` - Rust kernel accessed via KernelClient only

### Correct Pattern

```python
# Constitution R7: Register capability FIRST
from jeeves_capability_hello_world import register_capability
register_capability()

# Then use jeeves_infra for infrastructure
from jeeves_infra.wiring import (
    create_llm_provider_factory,
    create_tool_executor,
)
from jeeves_infra.settings import get_settings
from jeeves_infra.bootstrap import create_app_context
```

## Tool Suite

### Available Tools

| Tool ID | Category | Risk Level | Description |
|---------|----------|------------|-------------|
| `web_search` | Search | External | Search the web for information |
| `get_time` | Utility | Read-only | Get current date/time |
| `list_tools` | Introspection | Read-only | List available tools |

### Tool Access Control

- All tools are READ-ONLY or EXTERNAL (no state modification)
- Tools are registered at startup via `initialize_all_tools()`
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
2. Import infrastructure via `jeeves_infra.wiring`
3. Initialize tools via `initialize_all_tools()`
4. Create service via `create_hello_world_service()`

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
- gRPC servicer (Gradio-only deployment)
- Control Tower integration (no event tracking)
- Persistence layer (stateless)
- Complex tool suites (3 tools only)

### Amendment II: Template Purpose

This capability serves as a template for building new capabilities:
- Follow the same registration pattern
- Follow the same import boundaries
- Extend tools and prompts as needed
