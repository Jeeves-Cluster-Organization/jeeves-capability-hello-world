use std::collections::HashMap;

const ECOSYSTEM_OVERVIEW: &str = r#"
## The Jeeves Ecosystem

Jeeves is a multi-layered AI agent orchestration system built on a Rust
micro-kernel. It follows a library-first architecture: consumers import
jeeves-core as a crate dependency and compose pipelines declaratively.

### Architecture

1. **jeeves-core** (Rust library) — The micro-kernel: pipeline orchestration,
   routing engine, bounds checking, agent execution, multi-provider LLM via
   genai (OpenAI, Anthropic, Gemini, Ollama, Groq, DeepSeek, Cohere, xAI),
   tool registry, checkpoint/resume, OTEL tracing.
2. **Capabilities** (Rust or Python) — Domain-specific consumers: tools as
   ToolExecutor impls, pipeline configs (JSON), prompt templates (.txt),
   HTTP servers (Axum) or Python apps (PyO3).

### Data Flow

Request → Kernel Pipeline (Agents) → Tools → Result

The Envelope carries state through the pipeline, accumulating outputs from
each stage. The kernel is sole orchestration authority — agents have no
control over what runs next.
"#;

const LAYER_DETAILS: &str = r#"
## Layer Details

### jeeves-core (Rust Micro-Kernel)

The foundation. Written in Rust for performance and reliability.

**Core Modules:**
- Pipeline orchestration — routes envelopes through agent stages
- Envelope state management — immutable transitions with full audit trail
- Resource bounds — max_iterations, max_llm_calls, max_agent_hops, edge_limits
- GenaiProvider — 8 native LLM providers via genai crate
- Model roles — abstract roles (fast, reasoning) resolved via MODEL_* env vars
- ToolRegistry — composable tool registration with per-stage ACL
- AgentFactoryBuilder — auto-creates agents from pipeline stage config
- NodeKind: Agent, Gate, Fork — three graph node types
- Checkpoint/resume — serializable pipeline state for durability
- OTEL bridge — feature-gated OpenTelemetry tracing

**Consumption modes:**
- Rust crate: `use jeeves_core::prelude::*;`
- PyO3 module: `from jeeves_core import PipelineRunner`
- MCP stdio: `jeeves-kernel` binary (feature-gated)

### Capabilities (Consumer Layer)

Domain-specific implementations that use jeeves-core as a library.

**Rust consumers** (Axum HTTP servers):
- jeeves-capability-hello-world — onboarding chatbot
- assistant-7agent — personal assistant with 24 tools
- game-server — game NPC dialogue system

**Python consumers** (PyO3 import):
- jeeves-capability-mini-swe-agent — SWE agent with Gradio UI
"#;

const KEY_CONCEPTS: &str = r#"
## Key Concepts

### Envelope

The state container flowing through the pipeline. Carries:
- `raw_input` — original user message
- `outputs` — dict mapping stage output_keys to their outputs
- `state` — persistent fields with merge strategies (Replace/Append/MergeDict)
- `metadata` — context dict (user_id, session_id, custom fields)
- `bounds` — iteration/LLM/hop counters and terminal_reason

### PipelineConfig (pipeline.json)

Declarative pipeline definition:
- `stages` — ordered list of PipelineStage definitions
- `max_iterations`, `max_llm_calls`, `max_agent_hops` — termination bounds
- `edge_limits` — per-edge transition caps
- `state_schema` — typed state fields with merge strategies

### PipelineStage

Each stage declares:
- `agent` — agent name to dispatch
- `has_llm` — whether agent makes LLM calls
- `model_role` — abstract model role (e.g. "fast", "reasoning")
- `prompt_key` — prompt template key
- `node_kind` — Agent, Gate, or Fork
- `routing_fn` — name of registered routing function
- `output_schema` — JSON Schema for output validation
- `allowed_tools` — per-stage tool whitelist
- `max_context_tokens` + `context_overflow` — context window safety

### NodeKind (Graph Node Types)

| Kind | Behavior |
|------|----------|
| **Agent** | Runs agent, then calls routing_fn (or default_next) |
| **Gate** | Calls routing_fn without running an agent |
| **Fork** | Calls routing_fn, dispatches returned targets in parallel |

### Routing

Routing is code, not data. Consumers register named routing functions on
the Kernel before spawning. Stages reference them by name via `routing_fn`.
Static wiring (`default_next`, `error_next`) remains declarative.

Evaluation order:
1. `agent_failed` + `error_next` -> error_next
2. `routing_fn` registered -> call it
3. `default_next`
4. Terminate COMPLETED

### Model Roles

Stages set `model_role` to an abstract role name. The GenaiProvider resolves
roles via `MODEL_*` environment variables:
- `MODEL_FAST=gpt-4o-mini` → `model_role: "fast"` uses gpt-4o-mini
- `MODEL_REASONING=claude-3-5-sonnet` → `model_role: "reasoning"` uses claude-3-5-sonnet
- Explicit model names pass through unchanged
"#;

const CODE_EXAMPLES: &str = r#"
## Code Examples

### Rust Consumer Pattern

```rust
use jeeves_core::prelude::*;
use jeeves_core::worker::llm::genai_provider::GenaiProvider;

// LLM provider (reads API keys from env, model roles from MODEL_* vars)
let llm: Arc<dyn LlmProvider> = Arc::new(GenaiProvider::new("gpt-4o-mini"));

// Load pipeline + prompts
let config: PipelineConfig = serde_json::from_str(&std::fs::read_to_string("pipeline.json")?)?;
let prompts = Arc::new(PromptRegistry::from_dir("prompts"));

// Build tools + agents
let tools = ToolRegistryBuilder::new().add_executor(my_tools).build();
let agents = AgentFactoryBuilder::new(llm, prompts, tools)
    .add_pipeline(config.clone())
    .build();

// Run pipeline
let envelope = Envelope::new_minimal(user_id, session_id, input, None);
let result = run_pipeline_with_envelope(&handle, pid, config, envelope, &agents).await?;
```

### Implementing a ToolExecutor

```rust
#[derive(Debug)]
struct MyTools;

#[async_trait]
impl ToolExecutor for MyTools {
    async fn execute(&self, name: &str, params: Value) -> jeeves_core::Result<ToolOutput> {
        match name {
            "get_time" => Ok(ToolOutput::json(json!({"time": chrono::Utc::now().to_rfc3339()}))),
            _ => Err(jeeves_core::Error::not_found(format!("Unknown tool: {name}"))),
        }
    }
    fn list_tools(&self) -> Vec<ToolInfo> {
        vec![ToolInfo {
            name: "get_time".into(),
            description: "Get current UTC time".into(),
            parameters: json!({"type": "object", "properties": {}}),
        }]
    }
}
```

### Python Consumer Pattern (PyO3)

```python
from jeeves_core import PipelineRunner, tool

@tool(name="my_tool", description="Does something")
def my_tool(params):
    return {"result": params.get("input")}

runner = PipelineRunner.from_json("pipeline.json", model="gpt-4o-mini")
runner.register_tool(my_tool)
result = runner.run("hello", user_id="user1")
```

### Pipeline JSON

```json
{
  "name": "my_pipeline",
  "stages": [
    {"name": "classify", "agent": "classify", "has_llm": true,
     "model_role": "fast", "prompt_key": "classify",
     "default_next": "respond"},
    {"name": "respond", "agent": "respond", "has_llm": true,
     "prompt_key": "respond"}
  ],
  "max_iterations": 4, "max_llm_calls": 7, "max_agent_hops": 12
}
```
"#;

const HELLO_WORLD_STRUCTURE: &str = r#"
## Hello World Capability Structure

This capability demonstrates the minimal Rust consumer pattern.

```
jeeves-capability-hello-world/
├── src/
│   ├── main.rs          # Axum HTTP server (chat + streaming endpoints)
│   ├── tools.rs         # ToolExecutor impl (knowledge retrieval + time)
│   └── knowledge.rs     # Embedded knowledge sections
├── pipeline.json        # 4-stage pipeline with routing
├── prompts/             # Prompt templates (.txt)
│   ├── chatbot.understand.txt
│   ├── chatbot.respond.txt
│   └── chatbot.respond_streaming.txt
├── chat.html            # Simple chat UI
├── Cargo.toml           # Depends on jeeves-core
└── .env                 # OPENAI_API_KEY, DEFAULT_MODEL, PORT
```

### How It Works

1. `main.rs` creates GenaiProvider, Kernel, PromptRegistry, ToolRegistry
2. AgentFactoryBuilder auto-creates agents from pipeline.json stages
3. Axum serves `/chat` (buffered) and `/chat/stream` (SSE) endpoints
4. Pipeline: understand → think_knowledge/think_tools → respond
5. The `understand` stage (model_role: fast) classifies intent cheaply
6. The `respond` stage uses the deployment default model for quality
"#;

const HOW_TO_GUIDES: &str = r#"
## How-To Guides

### How to Add a New Tool

1. Add a match arm in `tools.rs`:
   ```rust
   "my_tool" => Ok(json!({"result": "done"})),
   ```
2. Add a `ToolInfo` entry in `list_tools()`:
   ```rust
   ToolInfo { name: "my_tool".into(), description: "...".into(), parameters: json!({...}) }
   ```

### How to Add a New Stage

1. Create a prompt template in `prompts/my_stage.txt`
2. Add a stage to `pipeline.json`:
   ```json
   {"name": "my_stage", "agent": "my_stage", "has_llm": true,
    "prompt_key": "my_stage", "default_next": "respond"}
   ```
3. Agents are auto-created — no manual registration needed

### How to Use a Different LLM Provider

Set the appropriate API key environment variable:
- `OPENAI_API_KEY` for OpenAI models (gpt-4o, gpt-4o-mini)
- `ANTHROPIC_API_KEY` for Anthropic models (claude-3-5-sonnet)
- `GEMINI_API_KEY` for Google models

Set `DEFAULT_MODEL` to the desired model name. Model roles resolve via:
- `MODEL_FAST=gpt-4o-mini` → stages with `"model_role": "fast"` use this
- `MODEL_REASONING=claude-3-5-sonnet` → stages with `"model_role": "reasoning"` use this

### How to Run

```bash
# Set API key
export OPENAI_API_KEY=sk-...

# Optional: configure model roles
export MODEL_FAST=gpt-4o-mini
export MODEL_REASONING=claude-3-5-sonnet
export DEFAULT_MODEL=gpt-4o-mini

# Run
cargo run
# → listening on 0.0.0.0:8001
```

### Routing

Routing is code. Stages set `routing_fn` to reference a registered function.
The `understand` stage uses `intent_router` to route getting_started/general
intents to think_tools, and everything else to think_knowledge. The `respond`
stage uses `respond_loop` to loop back to understand when needs_more_context is true.

Bounds guarantee termination: max_llm_calls=7, max_agent_hops=12, max_iterations=4.
"#;

pub fn get_for_sections(sections: &[String]) -> String {
    let map: HashMap<&str, &str> = HashMap::from([
        ("ecosystem_overview", ECOSYSTEM_OVERVIEW),
        ("layer_details", LAYER_DETAILS),
        ("key_concepts", KEY_CONCEPTS),
        ("code_examples", CODE_EXAMPLES),
        ("hello_world_structure", HELLO_WORLD_STRUCTURE),
        ("how_to_guides", HOW_TO_GUIDES),
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
