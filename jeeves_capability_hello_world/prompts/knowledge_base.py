"""Embedded knowledge about the Jeeves ecosystem for onboarding.

This module provides sectioned knowledge that can be retrieved based on
the user's intent, enabling more targeted and relevant responses.

Sections:
- ecosystem_overview: High-level architecture overview
- layer_details: Detailed explanation of each layer
- key_concepts: Core concepts (Envelope, AgentConfig, etc.)
- code_examples: Practical code snippets
- hello_world_structure: This capability's structure
- how_to_guides: Step-by-step guides for common tasks
- conditional_routing: RoutingRule, loop-back, bounds, error_next
"""

from typing import List


# =============================================================================
# SECTION: ECOSYSTEM OVERVIEW
# =============================================================================

ECOSYSTEM_OVERVIEW = """
## The Jeeves Ecosystem

Jeeves is a multi-layered AI agent orchestration system designed for building
production-grade AI applications. It follows a micro-kernel architecture where
a Rust core handles all orchestration decisions.

### The Three Layers

1. **jeeves-core** (Rust) - The micro-kernel: HTTP gateway, pipeline orchestration,
   routing engine, bounds checking, agent execution, LLM providers, MCP tool client
2. **jeeves-mcp-bridge** (Python) - Thin MCP tool server library: exposes Python
   domain logic as tools the kernel can call via JSON-RPC 2.0
3. **Capabilities** (Python) - Your domain-specific code: MCP tool servers,
   pipeline configs (JSON), prompt templates (.txt), Gradio/FastAPI UIs

### Data Flow

User Request -> HTTP Gateway -> Kernel Pipeline (Agents) -> MCP Tools -> Response

The Envelope carries state through this entire flow, ensuring immutable state
transitions and full auditability.
"""


# =============================================================================
# SECTION: LAYER DETAILS
# =============================================================================

LAYER_DETAILS = """
## Layer Details

### Layer 1: jeeves-core (Rust Micro-Kernel)

The foundation of Jeeves, written in Rust for performance and reliability.
This is the sole orchestration authority.

**Responsibilities:**
- Pipeline orchestration engine - routes envelopes through agent stages
- Envelope state management - immutable state transitions with full history
- Resource quotas - limits on iterations, LLM calls, agent hops
- HTTP gateway (axum) - REST API + SSE streaming for clients
- LLM providers - OpenAI-compatible HTTP client for LLM calls
- MCP tool client - JSON-RPC 2.0 client for calling Python tools
- Agent profiles - LlmAgent, McpDelegatingAgent, DeterministicAgent
- PipelineRunner - executes agent pipelines via kernel instruction loop

**Key Endpoints:**
- `POST /api/v1/chat/messages` - Run pipeline (buffered response)
- `POST /api/v1/chat/stream` - Run pipeline (SSE streaming)
- `GET /health` - Health check

### Layer 2: jeeves-mcp-bridge (Python Bridge)

Lightweight Python library for building MCP tool servers.

**Responsibilities:**
- `@mcp_tool` decorator - mark Python functions as MCP tools
- `McpToolServer` - JSON-RPC 2.0 server (stdio or HTTP transport)
- Tool discovery (`tools/list`) and execution (`tools/call`)
- Zero dependencies (stdlib only)

### Layer 3: Capabilities (Python User Space)

Your domain-specific implementations.

**Responsibilities:**
- Domain prompts - `.txt` prompt templates loaded by kernel
- Custom tools - Python functions exposed via MCP tool server
- Pipeline configuration - `pipeline.json` defining stages + routing
- UI layer - Gradio or FastAPI frontends that call kernel HTTP API
- Database clients - capability-owned persistence (SQLite, etc.)

**This is where hello-world lives!**
"""


# =============================================================================
# SECTION: KEY CONCEPTS
# =============================================================================

KEY_CONCEPTS = """
## Key Concepts

### Envelope

The state container that flows through the pipeline. Think of it as a "request
context" that accumulates results from each processing stage.

**Properties:**
- `envelope_id` - Unique identifier for tracing
- `raw_input` - The original user message
- `metadata` - Context dict passed between agents
- `outputs` - Dict mapping agent names to their outputs
- `current_stage` - Which agent is currently processing
- `terminated` - Whether pipeline should stop

**Immutability:** Each state transition creates a new snapshot, enabling
full replay and debugging.

### AgentConfig

Declarative configuration for an agent, passed via JEEVES_AGENTS env var.

**Key Fields:**
- `name` - Agent identifier (e.g., "understand", "respond")
- `type` - Agent type: "llm", "mcp_delegate", "deterministic"
- `has_llm` - Whether this agent calls an LLM (set in pipeline.json)
- `has_tools` - Whether this agent can execute tools
- `prompt_key` - Which prompt template to use (e.g., "chatbot.respond")
- `output_key` - Where to store results in envelope.outputs

### PipelineConfig

JSON configuration for an entire multi-agent pipeline (pipeline.json).

**Key Fields:**
- `name` - Pipeline identifier
- `stages` - List of PipelineStage definitions
- `max_iterations` - Circuit breaker for loops
- `max_llm_calls` - Budget for LLM usage
- `max_agent_hops` - Maximum stage transitions

### Constitution R7 (Import Boundaries)

A strict rule: Capabilities communicate with the kernel only via HTTP API
and MCP protocol. No direct Rust imports.

**CORRECT:**
```python
import requests
resp = requests.post("http://localhost:8080/api/v1/chat/messages", json=payload)
```

**WRONG:**
```python
from jeeves_core import PipelineRunner  # No Python package exists!
```

**Why?** This ensures capabilities remain portable and the kernel
can be upgraded without breaking user code.

### The Pipeline Pattern

Jeeves uses a staged pipeline with declarative routing:

**Linear flow:** Understand → Think-Knowledge → Respond
**Conditional routing:** Understand can route to Think-Tools for general/getting_started intents
**Loop-back:** Respond can route back to Understand when knowledge is insufficient

Agent types:
1. **Understand** (LLM): Classifies intent, determines routing
2. **Think-Knowledge** (No LLM): Retrieves embedded knowledge sections via MCP
3. **Think-Tools** (No LLM, Has Tools): Executes tools (get_time, list_tools) via MCP
4. **Respond** (LLM): Synthesizes response, may loop back

Routing rules use expression trees in JSON, evaluated by the Rust kernel:
```json
{"expr": {"op": "Eq", "field": {"scope": "Current", "key": "intent"}, "value": "general"}, "target": "think_tools"}
{"expr": {"op": "Eq", "field": {"scope": "Current", "key": "needs_more_context"}, "value": true}, "target": "understand"}
```

Bounds guarantee termination: `max_llm_calls=7` means max 3 loops.
"""


# =============================================================================
# SECTION: CODE EXAMPLES
# =============================================================================

CODE_EXAMPLES = """
## Code Examples

### Creating an MCP Tool

```python
# In mcp_server.py
from jeeves_mcp_bridge import mcp_tool, McpToolServer

@mcp_tool(
    name="get_time",
    description="Get current date and time",
    parameters={"type": "object", "properties": {}}
)
def get_time(params: dict) -> dict:
    from datetime import datetime, timezone as tz
    now = datetime.now(tz.utc)
    return {
        "status": "success",
        "current_time": now.isoformat(),
        "timezone": "UTC"
    }

server = McpToolServer()
server.register(get_time)
server.run_stdio()  # Kernel spawns this process
```

### Registering Tools with the Kernel

Tools are registered via MCP server config in `run.py`:
```python
mcp_servers = [{"name": "hello_tools", "transport": "stdio",
                "command": sys.executable, "args": ["mcp_server.py"]}]
os.environ["JEEVES_MCP_SERVERS"] = json.dumps(mcp_servers)
```

The kernel discovers tools automatically via `tools/list` JSON-RPC call.

### Creating a Prompt Template

```python
# In prompts/chatbot.respond.txt (loaded by kernel PromptRegistry)
You are a helpful assistant.

## User Message
{raw_input}

## Context
{understand_intent}

## Task
Respond helpfully based on the context provided.
```

Templates use `{variable_name}` placeholders. The kernel's PromptRegistry
loads all `.txt` files from the prompts directory.

### Defining a Pipeline (JSON)

```json
{
  "name": "my_pipeline",
  "stages": [
    {"name": "understand", "agent": "understand", "has_llm": true,
     "prompt_key": "chatbot.understand", "default_next": "respond"},
    {"name": "respond", "agent": "respond", "has_llm": true,
     "prompt_key": "chatbot.respond"}
  ],
  "max_iterations": 4, "max_llm_calls": 7, "max_agent_hops": 12
}
```

### Registering Agents with the Kernel

```python
agents = [
    {"name": "understand", "type": "llm", "prompt_key": "chatbot.understand"},
    {"name": "think_knowledge", "type": "mcp_delegate", "tool_name": "think_knowledge"},
    {"name": "respond", "type": "llm", "prompt_key": "chatbot.respond"},
]
os.environ["JEEVES_AGENTS"] = json.dumps(agents)
```

### Calling the Kernel HTTP API

```python
import requests

resp = requests.post("http://localhost:8080/api/v1/chat/messages", json={
    "pipeline_config": pipeline_config,  # loaded from pipeline.json
    "input": "What is the Jeeves architecture?",
    "user_id": "user1",
    "session_id": "session1",
})
result = resp.json()  # {"process_id": "...", "outputs": {...}, "terminated": true}
```
"""


# =============================================================================
# SECTION: HELLO WORLD STRUCTURE
# =============================================================================

HELLO_WORLD_STRUCTURE = """
## Hello World Capability Structure

This capability demonstrates the minimal Jeeves pattern.

```
jeeves-capability-hello-world/
├── run.py                           # Starts kernel + Gradio UI
├── gradio_app.py                    # HTTP-based Gradio web UI
├── mcp_server.py                    # MCP tool server (4 tools)
├── pipeline.json                    # Pipeline definition (JSON)
├── prompts/                         # Prompt templates for kernel
│   ├── chatbot.understand.txt       # Intent classification prompt
│   ├── chatbot.respond.txt          # Response synthesis prompt
│   └── chatbot.respond_streaming.txt
├── jeeves_capability_hello_world/   # Python package
│   ├── __init__.py
│   ├── prompts/
│   │   └── knowledge_base.py        # Embedded knowledge (this file!)
│   └── tests/
│       └── test_onboarding.py       # Knowledge base tests
└── pyproject.toml
```

### Key Files Explained

- **run.py**: Configures agents + MCP servers, starts kernel subprocess, launches Gradio
- **gradio_app.py**: HTTP client to kernel API, Gradio chat UI
- **mcp_server.py**: Exposes 4 tools (get_time, list_tools, think_knowledge, think_tools)
- **pipeline.json**: 4-stage pipeline with conditional routing rules
- **prompts/*.txt**: Prompt templates loaded by kernel's PromptRegistry
- **knowledge_base.py**: Embedded knowledge sections for onboarding responses
"""


# =============================================================================
# SECTION: HOW-TO GUIDES
# =============================================================================

HOW_TO_GUIDES = """
## How-To Guides

### How to Add a New Tool

1. **Create the function** in `mcp_server.py`:
   ```python
   @mcp_tool(name="my_tool", description="Does something useful",
             parameters={"type": "object", "properties": {"input": {"type": "string"}}})
   def my_tool(params: dict) -> dict:
       return {"status": "success", "result": params.get("input", "").upper()}
   ```

2. **Register it** with the server:
   ```python
   server.register(my_tool)
   ```

That's it -- the kernel discovers the tool automatically via MCP `tools/list`.

### How to Create a New Agent

1. **Create the prompt** as a `.txt` file in `prompts/`
2. **Add a stage** to `pipeline.json` with the agent name and prompt_key
3. **Register the agent** in `run.py` via the `agents` list
4. **Add routing rules** in pipeline.json if conditional routing is needed

### How to Modify the Pipeline Flow

Edit `pipeline.json`:
- Change `default_next` to alter the default flow
- Add `routing` rules to create conditional branches
- Set `error_next` to define fallback agents on failure
- Add/remove stages from the `stages` list
- Adjust bounds (`max_iterations`, `max_llm_calls`, `max_agent_hops`)

### How to Run the Capability

```bash
# Start kernel + Gradio UI
python run.py

# Or kernel only (for testing with curl)
python run.py --kernel-only
```

Then open http://localhost:8001 in your browser.

### How to Test Your Changes

```bash
# Run all tests
pytest

# Run specific test file
pytest jeeves_capability_hello_world/tests/test_onboarding.py

# Run with verbose output
pytest -v
```

### Common Troubleshooting

**Cannot connect to kernel**
- Ensure kernel is running: `python run.py --kernel-only`
- Check `http://localhost:8080/health` returns 200

**Agent not receiving context**
- Check prompt template uses `{variable_name}` placeholders
- Check pipeline.json has correct `output_key` and routing

**Tool not executing**
- Verify tool is registered in `mcp_server.py` via `server.register(fn)`
- Verify MCP server config in `run.py` points to correct script
- Check kernel logs for MCP connection errors
"""


# =============================================================================
# SECTION: CONDITIONAL ROUTING
# =============================================================================

CONDITIONAL_ROUTING = """
## Conditional Routing

### RoutingRule

Stages define routing rules as JSON expression trees that the Rust kernel evaluates
after each agent completes. Rules are checked against the agent's output dict.

```json
{
  "name": "understand",
  "agent": "understand",
  "routing": [
    {"expr": {"op": "Eq", "field": {"scope": "Current", "key": "intent"}, "value": "general"}, "target": "think_tools"},
    {"expr": {"op": "Eq", "field": {"scope": "Current", "key": "intent"}, "value": "getting_started"}, "target": "think_tools"}
  ],
  "default_next": "think_knowledge",
  "error_next": "respond"
}
```

### Loop-Back Routing (Temporal Pattern)

The respond stage uses the Temporal pattern: routing expresses when to CONTINUE.
When no rule matches and no default_next is set, the kernel terminates naturally.

```json
{
  "name": "respond",
  "agent": "respond",
  "routing": [
    {"expr": {"op": "Eq", "field": {"scope": "Current", "key": "needs_more_context"}, "value": true}, "target": "understand"}
  ]
}
```

No `default_next` = kernel terminates with COMPLETED when no rule matches.

### Tight Bounds

Circular routes require bounds to guarantee termination:
- `max_llm_calls=7`: Each loop uses 2 LLM calls (understand + respond), so max 3 loops
- `max_agent_hops=12`: Each loop uses ~4 hops, so max 3 loops
- `max_iterations=4`: Explicit iteration cap

When bounds are exceeded, the kernel terminates with a reason like
`MaxLlmCallsExceeded`. The response includes `terminal_reason` so the
client can display a partial response if available.

### error_next

Each stage can define a fallback stage via `error_next`. If the agent fails,
the kernel routes to error_next instead of terminating the pipeline.

```json
{
  "name": "think_knowledge",
  "agent": "think_knowledge",
  "error_next": "respond"
}
```
"""


# =============================================================================
# SECTION REGISTRY
# =============================================================================

KNOWLEDGE_SECTIONS = {
    "ecosystem_overview": ECOSYSTEM_OVERVIEW,
    "layer_details": LAYER_DETAILS,
    "key_concepts": KEY_CONCEPTS,
    "code_examples": CODE_EXAMPLES,
    "hello_world_structure": HELLO_WORLD_STRUCTURE,
    "how_to_guides": HOW_TO_GUIDES,
    "conditional_routing": CONDITIONAL_ROUTING,
}


# =============================================================================
# PUBLIC API
# =============================================================================

def get_knowledge_for_sections(sections: List[str]) -> str:
    """
    Get knowledge content for specified sections.

    Args:
        sections: List of section names to retrieve

    Returns:
        Combined knowledge text for the requested sections
    """
    parts = []
    for section in sections:
        if section in KNOWLEDGE_SECTIONS:
            parts.append(KNOWLEDGE_SECTIONS[section])
    return "\n\n".join(parts) if parts else ECOSYSTEM_OVERVIEW


def get_onboarding_context() -> str:
    """Get full onboarding context for prompts (all sections)."""
    return "\n\n".join(KNOWLEDGE_SECTIONS.values())


def get_section_names() -> List[str]:
    """Get list of available knowledge section names."""
    return list(KNOWLEDGE_SECTIONS.keys())


__all__ = [
    # Section constants
    "ECOSYSTEM_OVERVIEW",
    "LAYER_DETAILS",
    "KEY_CONCEPTS",
    "CODE_EXAMPLES",
    "HELLO_WORLD_STRUCTURE",
    "HOW_TO_GUIDES",
    "CONDITIONAL_ROUTING",
    # Registry and functions
    "KNOWLEDGE_SECTIONS",
    "get_knowledge_for_sections",
    "get_onboarding_context",
    "get_section_names",
]
