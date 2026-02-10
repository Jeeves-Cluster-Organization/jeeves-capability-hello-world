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
"""

from typing import List


# =============================================================================
# SECTION: ECOSYSTEM OVERVIEW
# =============================================================================

ECOSYSTEM_OVERVIEW = """
## The Jeeves Ecosystem

Jeeves is a multi-layered AI agent orchestration system designed for building
production-grade AI applications. It follows a micro-kernel architecture where
a Rust core handles orchestration while Python provides the AI/ML capabilities.

### The Three Layers

1. **jeeves-core** (Rust) - The micro-kernel that orchestrates everything
2. **jeeves-infra** (Python) - Infrastructure & orchestration framework: LLM providers, database protocols, adapters, pipeline runner, config
3. **Capabilities** (Python) - Your domain-specific code: prompts, tools, services

### Data Flow

User Request -> Gateway -> Pipeline (Agents) -> Tools -> Response

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

**Responsibilities:**
- Pipeline orchestration engine - routes envelopes through agent stages
- Envelope state management - immutable state transitions with full history
- Resource quotas - limits on iterations, LLM calls, agent hops
- Circuit breakers - fault tolerance for external service failures
- gRPC services - communication bridge to Python layer

**Key Files:**
- `src/` - Core orchestration logic
- `proto/` - gRPC protocol definitions
- `tests/` - Integration tests

### Layer 2: jeeves-infra (Python Infrastructure)

Shared infrastructure used by all Python components.

**Responsibilities:**
- LLM providers - unified interface to OpenAI, Anthropic, llama.cpp
- Database clients - Protocol-based registry (capabilities own concrete backends)
- Protocols - type definitions shared across layers
- Gateway - HTTP/WebSocket/gRPC translation layer
- kernel_client - Python interface to jeeves-core
- Agent profiles - declarative agent configuration
- Adapters - Constitution R7 compliant wrappers (create_llm_provider_factory)
- PipelineRunner - executes agent pipelines
- Event handling - streaming events to clients
- Orchestrator - event context, governance, flow, vertical service
- Memory handlers - CommBus handler registration, message types
- Bootstrap - AppContext creation, composition root

**Key Modules:**
- `jeeves_infra.llm` - LLM provider implementations
- `jeeves_infra.protocols` - Envelope, AgentConfig, PipelineConfig, PipelineEvent
- `jeeves_infra.gateway` - API translation layer
- `jeeves_infra.kernel_client` - gRPC client to jeeves-core
- `jeeves_infra.wiring` - Factory functions (create_llm_provider_factory, create_tool_executor)
- `jeeves_infra.orchestrator` - Event orchestration and governance
- `jeeves_infra.config` - Agent profiles, registry, constants
- `jeeves_infra.bootstrap` - AppContext composition root

### Layer 3: Capabilities (Python User Space)

Your domain-specific implementations.

**Responsibilities:**
- Domain prompts - LLM prompts for your use case
- Custom tools - functions agents can call
- Pipeline configuration - agent definitions and hooks
- Service layer - ChatbotService wraps PipelineRunner

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

Declarative configuration for an agent in the pipeline.

**Key Fields:**
- `name` - Agent identifier (e.g., "understand", "respond")
- `stage_order` - Execution order (0, 1, 2...)
- `has_llm` - Whether this agent calls an LLM
- `has_tools` - Whether this agent can execute tools
- `prompt_key` - Which prompt to use (e.g., "chatbot.respond")
- `output_key` - Where to store results in envelope.outputs
- `pre_process` / `post_process` - Hook functions

### PipelineConfig

Configuration for an entire multi-agent pipeline.

**Key Fields:**
- `name` - Pipeline identifier
- `agents` - List of AgentConfig
- `max_iterations` - Circuit breaker for loops
- `max_llm_calls` - Budget for LLM usage

### Constitution R7 (Import Boundaries)

A strict rule: Capabilities MUST NOT import infrastructure directly.

**CORRECT:**
```python
from jeeves_infra.bootstrap import create_app_context
app_context = create_app_context()
llm_factory = app_context.llm_provider_factory
```

**WRONG:**
```python
from avionics.llm import LLMProvider  # Violates R7!
```

**Why?** This ensures capabilities remain portable and the infrastructure
can be upgraded without breaking user code.

### The Pipeline Pattern

Jeeves uses a staged pipeline pattern: **Understand -> Think -> Respond**

1. **Understand** (LLM): Analyzes user intent, classifies the request
2. **Think** (Tools): Executes tools, retrieves data, performs actions
3. **Respond** (LLM): Synthesizes a response from all gathered context

This separation enables:
- Clear responsibility boundaries
- Easier testing (mock each stage)
- Flexible tool execution without LLM overhead
"""


# =============================================================================
# SECTION: CODE EXAMPLES
# =============================================================================

CODE_EXAMPLES = """
## Code Examples

### Creating a Simple Tool

```python
# In tools/my_tools.py
def get_time(timezone: str = "UTC") -> dict:
    \"\"\"Get current time in specified timezone.\"\"\"
    from datetime import datetime, timezone as tz
    now = datetime.now(tz.utc)
    return {
        "status": "success",
        "current_time": now.isoformat(),
        "timezone": timezone
    }
```

### Registering a Tool

```python
# In tools/registration.py
from .catalog import tool_catalog, ToolId

tool_catalog.register(
    tool_id=ToolId.GET_TIME.value,
    func=get_time,
    description="Get current date and time",
    category="utility",
    risk_level="read_only",
    parameters={"timezone": "string? - default UTC"},
    is_async=False,
)
```

### Creating an Agent Prompt

```python
# In prompts/chatbot/my_prompt.py
from jeeves_capability_hello_world.prompts.registry import register_prompt

@register_prompt(
    name="chatbot.my_agent",
    version="1.0",
    description="My custom agent prompt",
)
def my_agent_prompt() -> str:
    return \"\"\"You are a helpful assistant.

## User Message
{user_message}

## Task
Respond helpfully.

## Output (JSON)
{{"response": "<your response>"}}
\"\"\"
```

### Defining an Agent in the Pipeline

```python
# In pipeline_config.py
from jeeves_infra.protocols import AgentConfig

AgentConfig(
    name="my_agent",
    stage_order=0,
    has_llm=True,
    model_role="planner",
    prompt_key="chatbot.my_agent",
    output_key="my_output",
    required_output_fields=["response"],
    pre_process=my_pre_process,  # Optional hook
    post_process=my_post_process,  # Optional hook
    default_next="next_agent",
)
```

### Pre/Post Process Hooks

```python
async def my_pre_process(envelope, agent=None):
    \"\"\"Prepare context before agent runs.\"\"\"
    envelope.metadata["extra_context"] = "some value"
    return envelope

async def my_post_process(envelope, output, agent=None):
    \"\"\"Process agent output before next stage.\"\"\"
    # Modify output or envelope as needed
    output["processed"] = True
    return envelope
```

### Using Factories (Constitution R7)

```python
# CORRECT way to get LLM provider (via AppContext, K8s-style bootstrap)
from jeeves_infra.bootstrap import create_app_context

app_context = create_app_context()
llm = app_context.llm_provider_factory(role="planner")
response = await llm.generate(model, prompt, options)
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
├── gradio_app.py                    # Entry point - Gradio web UI
├── jeeves_capability_hello_world/   # Main capability package
│   ├── __init__.py
│   ├── pipeline_config.py           # 3-agent pipeline configuration
│   │
│   ├── prompts/                     # LLM prompts
│   │   ├── __init__.py
│   │   ├── knowledge_base.py        # Embedded knowledge (this file!)
│   │   └── chatbot/
│   │       ├── understand.py        # Intent classification prompt
│   │       ├── respond.py           # Response synthesis prompt
│   │       └── respond_streaming.py # Streaming variant
│   │
│   ├── tools/                       # Available tools
│   │   ├── __init__.py
│   │   ├── catalog.py               # Tool registry
│   │   ├── registration.py          # Tool registration
│   │   └── hello_world_tools.py     # get_time, list_tools
│   │
│   ├── orchestration/               # Service layer
│   │   ├── __init__.py
│   │   ├── chatbot_service.py       # Pipeline execution wrapper
│   │   └── wiring.py                # Dependency injection
│   │
│   ├── capability/                  # Capability registration
│   │   └── wiring.py                # Register with jeeves-core
│   │
│   └── tests/                       # Unit tests
│
├── jeeves-core/                     # Rust micro-kernel (git submodule)
└── jeeves-airframe/                 # Python infrastructure (git submodule)
```

### Key Files Explained

- **gradio_app.py**: Starts the web UI, initializes the capability
- **pipeline_config.py**: Defines the 3-agent pipeline with hooks
- **prompts/chatbot/*.py**: LLM prompts for each agent
- **tools/hello_world_tools.py**: Simple demonstration tools
- **orchestration/chatbot_service.py**: Wraps PipelineRunner
- **capability/wiring.py**: Registers with jeeves-core registry
"""


# =============================================================================
# SECTION: HOW-TO GUIDES
# =============================================================================

HOW_TO_GUIDES = """
## How-To Guides

### How to Add a New Tool

1. **Create the function** in `tools/hello_world_tools.py`:
   ```python
   def my_tool(param1: str) -> dict:
       return {"status": "success", "result": param1.upper()}
   ```

2. **Add to ToolId enum** in `tools/catalog.py`:
   ```python
   class ToolId(str, Enum):
       MY_TOOL = "my_tool"
   ```

3. **Add to EXPOSED_TOOL_IDS** in `tools/catalog.py`:
   ```python
   EXPOSED_TOOL_IDS = frozenset([ToolId.MY_TOOL.value, ...])
   ```

4. **Register in** `tools/registration.py`:
   ```python
   tool_catalog.register(
       tool_id=ToolId.MY_TOOL.value,
       func=my_tool,
       description="Does something useful",
       category=ToolCategory.UTILITY.value,
       risk_level=RiskLevel.READ_ONLY.value,
   )
   ```

5. **Export from** `tools/__init__.py`

### How to Create a New Agent

1. **Create the prompt** in `prompts/chatbot/my_agent.py`
2. **Add AgentConfig** to `pipeline_config.py`
3. **Create pre/post hooks** if needed
4. **Update EXPOSED_TOOL_IDS** if agent needs tools

### How to Modify the Pipeline Flow

Edit `pipeline_config.py`:
- Change `stage_order` to reorder agents
- Change `default_next` to alter flow
- Add/remove agents from the `agents` list

### How to Run the Capability

```bash
# Start jeeves-core (Rust kernel)
cd jeeves-core && cargo run

# In another terminal, start the Gradio UI
python gradio_app.py
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

**Import Error: Cannot import from protocols**
- Use `from jeeves_infra.protocols import ...`
- NOT `from protocols import ...`

**Agent not receiving context**
- Check `pre_process` hook is updating `envelope.metadata`
- Check prompt uses `{variable_name}` placeholders

**Tool not executing**
- Verify tool is in `EXPOSED_TOOL_IDS`
- Verify agent has `has_tools=True` and `tool_access=ToolAccess.ALL`
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
    # Registry and functions
    "KNOWLEDGE_SECTIONS",
    "get_knowledge_for_sections",
    "get_onboarding_context",
    "get_section_names",
]
