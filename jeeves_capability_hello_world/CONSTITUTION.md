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
    ↓
UNDERSTAND (LLM)     ← Intent classification
    ↓
THINK (Tools)        ← Tool execution (optional)
    ↓
RESPOND (LLM)        ← Response synthesis
    ↓
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
- `protocols` - Type definitions and protocols
- `mission_system.adapters` - Infrastructure access
- `mission_system.contracts_core` - Pipeline configuration types

### Forbidden Imports

Capability code MUST NOT import from:
- `avionics.*` - Direct infrastructure access forbidden
- `memory_module.*` - Use mission_system.adapters instead

### Correct Pattern

```python
# Constitution R7: Register capability FIRST
from jeeves_capability_hello_world import register_capability
register_capability()

# Then use adapters for infrastructure
from mission_system.adapters import (
    create_llm_provider_factory,
    create_tool_executor,
    get_settings,
)
```

### Incorrect Pattern (FORBIDDEN)

```python
# WRONG: Direct avionics import
from avionics.llm.factory import LLMFactory
from avionics.wiring import ToolExecutor
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

### Infrastructure Owns (via adapters)

- LLM provider factory
- Tool executor
- Settings management
- Logging

## Registration Contract

### Startup Sequence

1. Call `register_capability()` at module/startup level
2. Import infrastructure via `mission_system.adapters`
3. Initialize tools via `initialize_all_tools()`
4. Create service via `create_hello_world_service()`

### What register_capability() Returns

```python
{
    "capability_id": "hello_world",
    "capability_version": "0.1.0",
    "service_factory": Callable,  # Creates ChatbotService
    "tools_initializer": Callable,  # Initializes tools
    "prompts": Dict[str, Any],  # Prompt metadata
    "agents": List[Dict],  # Agent definitions
}
```

## Principles (from P1)

### P1: NLP-First

- Queries are answered via conversation, not code execution
- LLM generates natural language responses
- Tool results are synthesized into human-readable text

### P2: Accuracy First (Simplified)

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
