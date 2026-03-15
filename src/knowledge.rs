use std::collections::HashMap;

const ECOSYSTEM_OVERVIEW: &str = r#"
## The Jeeves Ecosystem

Jeeves is a multi-layered AI agent orchestration system designed for building
production-grade AI applications. It follows a micro-kernel architecture where
a Rust core handles all orchestration decisions.

### The Two Layers

1. **jeeves-core** (Rust + PyO3) - The micro-kernel, importable as a Python library:
   pipeline orchestration, routing engine, bounds checking, agent execution,
   LLM providers, Python tool bridge. Optional HTTP gateway (feature-gated).
2. **Capabilities** (Python) - Your domain-specific code: tools as Python callables,
   pipeline configs (JSON), prompt templates (.txt), Gradio/FastAPI UIs

### Data Flow

Python: runner.run(input) → Kernel Pipeline (Agents) → Python Tools → Result dict

The Envelope carries state through the pipeline, ensuring immutable state
transitions and full auditability. Tools are Python callables registered via
`@tool` decorator — no subprocess, no IPC, no MCP.
"#;

const LAYER_DETAILS: &str = r#"
## Layer Details

### Layer 1: jeeves-core (Rust Micro-Kernel + PyO3)

The foundation of Jeeves, written in Rust for performance and reliability.
This is the sole orchestration authority. Python imports it directly as a library.

**Responsibilities:**
- Pipeline orchestration engine - routes envelopes through agent stages
- Envelope state management - immutable state transitions with full history
- Resource quotas - limits on iterations, LLM calls, agent hops
- LLM providers - OpenAI-compatible HTTP client for LLM calls
- Python tool bridge - calls `@tool`-decorated Python functions directly
- Agent auto-creation - LlmAgent, McpDelegatingAgent, DeterministicAgent
- PipelineRunner - high-level facade (run/stream methods)
- Optional HTTP gateway (axum, behind `http-server` feature flag)

**Python API:**
```python
from jeeves_core import PipelineRunner, tool

runner = PipelineRunner.from_json("pipeline.json", prompts_dir="prompts/")
result = runner.run("input", user_id="u1")       # Buffered
for event in runner.stream("input", user_id="u1"):  # Streaming
    print(event)
```

### Layer 2: Capabilities (Python User Space)

Your domain-specific implementations.

**Responsibilities:**
- Domain prompts - `.txt` prompt templates loaded by kernel
- Custom tools - Python functions registered via `@tool` decorator
- Pipeline configuration - `pipeline.json` defining stages + routing
- UI layer - Gradio or FastAPI frontends
- Database clients - capability-owned persistence (SQLite, etc.)

**This is where hello-world lives!**
"#;

const KEY_CONCEPTS: &str = r#"
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

### Integration Pattern (PyO3 Library)

Capabilities import the Rust kernel directly as a Python library via PyO3.
No HTTP, no subprocess, no IPC — single process.

```python
from jeeves_core import PipelineRunner, tool

@tool(name="my_tool", description="Does something")
def my_tool(params):
    return {"result": "done"}

runner = PipelineRunner.from_json("pipeline.json", prompts_dir="prompts/")
runner.register_tool(my_tool)
result = runner.run("hello", user_id="user1")
```

**Why direct import?** The kernel is fundamentally a library, not a service.
Like Temporal workers import the SDK, capabilities import jeeves-core.

### The Pipeline Pattern

Jeeves uses a staged pipeline with declarative routing:

**Linear flow:** Understand → Think-Knowledge → Respond
**Conditional routing:** Understand can route to Think-Tools for general/getting_started intents
**Loop-back:** Respond can route back to Understand when knowledge is insufficient

Agent types (auto-created from pipeline.json):
1. **Understand** (LLM, `has_llm: true`): Classifies intent, determines routing
2. **Think-Knowledge** (No LLM, `has_llm: false`): Calls Python tool via ToolRegistry
3. **Think-Tools** (No LLM, `has_llm: false`): Calls Python tool via ToolRegistry
4. **Respond** (LLM, `has_llm: true`): Synthesizes response, may loop back

Routing rules use expression trees in JSON, evaluated by the Rust kernel:
```json
{"expr": {"op": "Eq", "field": {"scope": "Current", "key": "intent"}, "value": "general"}, "target": "think_tools"}
{"expr": {"op": "Eq", "field": {"scope": "Current", "key": "needs_more_context"}, "value": true}, "target": "understand"}
```

Bounds guarantee termination: `max_llm_calls=7` means max 3 loops.
"#;

const CODE_EXAMPLES: &str = r#"
## Code Examples

### Creating a Tool

```python
from jeeves_core import PipelineRunner, tool

@tool(name="get_time", description="Get current date and time",
      parameters={"type": "object", "properties": {}})
def get_time(params):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    return {"status": "success", "current_time": now.isoformat(), "timezone": "UTC"}
```

The `@tool` decorator sets `_tool_name`, `_tool_description`, and `_tool_parameters`
attributes on the function. `register_tool()` reads these attributes.

### Registering Tools

```python
runner = PipelineRunner.from_json("pipeline.json", prompts_dir="prompts/")
runner.register_tool(get_time)
runner.register_tool(my_other_tool)
```

Agents are auto-created from pipeline.json stages. When a tool name matches
a `has_llm: false` agent name, the kernel creates an McpDelegatingAgent that
calls the Python tool directly.

### Creating a Prompt Template

```
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

### Running a Pipeline

```python
from jeeves_core import PipelineRunner

runner = PipelineRunner.from_json("pipeline.json", prompts_dir="prompts/",
                                   openai_api_key="sk-...")

# Buffered (blocks until done)
result = runner.run("What is Jeeves?", user_id="user1")
# result["outputs"], result["terminated"], result["terminal_reason"]

# Streaming (Python iterator, releases GIL while waiting)
for event in runner.stream("What is Jeeves?", user_id="user1"):
    if event["type"] == "delta":
        print(event["content"], end="", flush=True)
```

### Cross-Pipeline Coordination

```python
# Tool can call runner.run() for sub-pipeline (reentrant, uses block_in_place)
runner.register_pipeline("analysis", analysis_config_json)

@tool(name="analyze", description="Run sub-analysis")
def analyze(params):
    sub = runner.run(params["topic"], pipeline_name="analysis", user_id="system")
    return sub["outputs"]
```
"#;

const HELLO_WORLD_STRUCTURE: &str = r#"
## Hello World Capability Structure

This capability demonstrates the minimal Jeeves pattern.

```
jeeves-capability-hello-world/
├── app.py                           # Single entry point (PyO3 + Gradio)
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

- **app.py**: Single-file entry point — defines 4 tools, creates PipelineRunner,
  runs Gradio ChatInterface. One file, one process, ~150 LOC.
- **pipeline.json**: 4-stage pipeline with conditional routing rules
- **prompts/*.txt**: Prompt templates loaded by kernel's PromptRegistry
- **knowledge_base.py**: Embedded knowledge sections for onboarding responses

### How It Works

1. `app.py` imports `PipelineRunner` and `tool` from `jeeves_core` (Rust via PyO3)
2. 4 tools are defined as Python functions with `@tool` decorator
3. `PipelineRunner.from_json()` loads pipeline.json + prompts
4. `register_tool()` bridges Python callables into the Rust ToolRegistry
5. Agents are auto-created from pipeline stages (LlmAgent for understand/respond,
   McpDelegatingAgent for think_knowledge/think_tools)
6. Gradio ChatInterface calls `runner.stream()` for real-time responses
"#;

const HOW_TO_GUIDES: &str = r#"
## How-To Guides

### How to Add a New Tool

1. **Define the function** in `app.py` with the `@tool` decorator:
   ```python
   from jeeves_core import tool

   @tool(name="my_tool", description="Does something useful",
         parameters={"type": "object", "properties": {"input": {"type": "string"}}})
   def my_tool(params):
       return {"status": "success", "result": params.get("input", "").upper()}
   ```

2. **Register it** with the runner:
   ```python
   runner.register_tool(my_tool)
   ```

That's it — the kernel creates an McpDelegatingAgent for any `has_llm: false`
stage whose name matches a registered tool.

### How to Create a New Agent

1. **Create the prompt** as a `.txt` file in `prompts/`
2. **Add a stage** to `pipeline.json` with the agent name and prompt_key
3. Agents are auto-created — no manual registration needed!
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
# Install jeeves-core PyO3 module (once)
cd ../jeeves-core && pip install -e .

# Start Gradio UI (single process — kernel runs embedded)
python app.py
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

**Import error: `from jeeves_core import ...`**
- Build the PyO3 module: `cd ../jeeves-core && pip install -e .`
- On Windows, use `pip install -e .` (not `maturin develop`)

**Agent not receiving context**
- Check prompt template uses `{variable_name}` placeholders
- Check pipeline.json has correct `output_key` and routing

**Tool not executing**
- Verify tool is registered via `runner.register_tool(fn)`
- Verify tool name matches the agent name in pipeline.json for `has_llm: false` stages
- Check that `@tool` decorator has `name` and `description` set
"#;

const CONDITIONAL_ROUTING: &str = r#"
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
"#;

pub fn get_for_sections(sections: &[String]) -> String {
    let map: HashMap<&str, &str> = HashMap::from([
        ("ecosystem_overview", ECOSYSTEM_OVERVIEW),
        ("layer_details", LAYER_DETAILS),
        ("key_concepts", KEY_CONCEPTS),
        ("code_examples", CODE_EXAMPLES),
        ("hello_world_structure", HELLO_WORLD_STRUCTURE),
        ("how_to_guides", HOW_TO_GUIDES),
        ("conditional_routing", CONDITIONAL_ROUTING),
    ]);
    let result: Vec<&str> = sections
        .iter()
        .filter_map(|s| map.get(s.as_str()).copied())
        .collect();
    if result.is_empty() {
        ECOSYSTEM_OVERVIEW.to_string()
    } else {
        result.join("\n\n")
    }
}
