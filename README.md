# Jeeves Hello World

**Your starting point for understanding the Jeeves AI agent ecosystem**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE.txt)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)

## What is This?

Jeeves Hello World is a **learning-focused chatbot** that demonstrates the core patterns of the Jeeves multi-agent orchestration system. It serves two purposes:

1. **A working chatbot** - Real LLM inference with a 3-agent pipeline
2. **An onboarding guide** - Understand how jeeves-core, jeeves-infra, and mission_system work together

## The Jeeves Ecosystem

```
┌─────────────────────────────────────────────────────────────────┐
│  Capabilities (User Space)                                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  jeeves-capability-hello-world  ← YOU ARE HERE          │    │
│  │  - 3-agent chatbot pipeline                             │    │
│  │  - Custom prompts and tools                             │    │
│  │  - Gradio web interface                                 │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  jeeves-infra + mission_system (Infrastructure Layer)           │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  jeeves-infra:                                          │    │
│  │  - LLM providers (OpenAI, Anthropic, llama.cpp)        │    │
│  │  - Database clients (PostgreSQL, pgvector)             │    │
│  │  - Protocols and type definitions                       │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │  mission_system:                                        │    │
│  │  - Orchestration framework                              │    │
│  │  - Agent profiles and configuration                     │    │
│  │  - Adapters for capabilities                            │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │ gRPC
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  jeeves-core (Micro-Kernel - Go)                                │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  - Pipeline orchestration engine                        │    │
│  │  - Envelope state management                            │    │
│  │  - Resource quotas (iterations, LLM calls, agent hops) │    │
│  │  - Circuit breakers for fault tolerance                 │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

| Layer | Language | What It Does |
|-------|----------|--------------|
| **jeeves-core** | Go | Micro-kernel: pipeline execution, state management, resource limits |
| **jeeves-infra** | Python | Infrastructure: LLM providers, database, protocols |
| **mission_system** | Python | Framework: orchestration, agent profiles, adapters |
| **Capabilities** | Python | Your code: prompts, tools, domain logic |

## The 3-Agent Pipeline

This chatbot uses a minimal but complete multi-agent pattern:

```
User Message
    ↓
┌─────────────────────────────────────────┐
│  UNDERSTAND (LLM)                       │
│  - Classifies user intent               │
│  - Identifies topic for knowledge       │
│  - Output: {intent, topic, reasoning}   │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  THINK (Knowledge Retrieval - No LLM)   │
│  - Retrieves targeted knowledge         │
│  - Maps intent → knowledge sections     │
│  - Output: {targeted_knowledge}         │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  RESPOND (LLM - Streaming)              │
│  - Synthesizes information              │
│  - Crafts helpful response              │
│  - Streams tokens to user               │
└─────────────────────────────────────────┘
    ↓
Response to User
```

### Intent Classification

The chatbot classifies questions into categories for targeted knowledge retrieval:

| Intent | Description | Example |
|--------|-------------|---------|
| `architecture` | System design, layers, data flow | "How do the layers connect?" |
| `concept` | Core concepts: Envelope, AgentConfig | "What is an Envelope?" |
| `getting_started` | Setup, running, adding tools | "How do I add a tool?" |
| `component` | Specific components: jeeves-core, etc. | "What is jeeves-core?" |
| `general` | Greetings, conversation, off-topic | "Hello!", "Summarize our chat" |

**Key insight**: The middle agent has **no LLM** - it retrieves relevant knowledge based on the classified intent, avoiding the cost of unnecessary inference.

> **Note:** This is a linear pipeline for simplicity. Jeeves supports DAG topologies, conditional branching via `RoutingRule`, and parallel execution. See [Pipeline Patterns](docs/PIPELINE_PATTERNS.md).

## Quick Start

### Prerequisites

- Python 3.11+
- Git (for submodules)
- Docker (optional, for full deployment)

### 1. Clone with Submodules

```bash
git clone --recursive <repository-url>
cd jeeves-capability-hello-world

# If you already cloned without --recursive
git submodule update --init --recursive
```

### 2. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements/all.txt
```

### 3. Configure LLM Provider

```bash
# Option A: Ollama (default - recommended for local development)
# No configuration needed if Ollama is running on default port
# Or explicitly set:
export JEEVES_LLM_BASE_URL=http://localhost:11434/v1
export JEEVES_LLM_MODEL=llama3.2

# Option B: OpenAI
export JEEVES_LLM_BASE_URL=https://api.openai.com/v1
export JEEVES_LLM_API_KEY=sk-your-key-here
export JEEVES_LLM_MODEL=gpt-4o-mini

# Option C: Any OpenAI-compatible endpoint
export JEEVES_LLM_BASE_URL=http://your-server:8080/v1
export JEEVES_LLM_MODEL=your-model
export JEEVES_LLM_API_KEY=your-key  # if required
```

### 4. Run the Chatbot

```bash
python gradio_app.py
# Open http://localhost:8001
```

## Project Structure

```
jeeves-capability-hello-world/
├── gradio_app.py                    # Entry point - Gradio web UI
│
├── jeeves_capability_hello_world/   # Main capability package
│   ├── __init__.py                  # Exports register_capability()
│   ├── pipeline_config.py           # 3-agent pipeline configuration
│   ├── CONSTITUTION.md              # Architectural rules
│   │
│   ├── prompts/                     # LLM prompts and knowledge
│   │   ├── knowledge_base.py        # Embedded knowledge (sectioned)
│   │   └── chatbot/
│   │       ├── understand.py        # Intent classification
│   │       ├── respond.py           # Response synthesis (JSON)
│   │       └── respond_streaming.py # Streaming plain text
│   │
│   ├── tools/                       # Available tools
│   │   ├── hello_world_tools.py     # get_time, list_tools
│   │   ├── catalog.py               # Tool registry and metadata
│   │   └── registration.py          # Tool registration
│   │
│   ├── capability/                  # Registration with framework
│   │   └── wiring.py                # Dependency injection
│   │
│   └── orchestration/               # Service layer
│       ├── chatbot_service.py       # Pipeline execution wrapper
│       └── wiring.py                # Service factory
│
├── jeeves-core/                     # Go micro-kernel (submodule)
├── jeeves-airframe/                 # Python infrastructure (submodule)
│   ├── jeeves_infra/                # Infrastructure implementations
│   └── mission_system/              # Orchestration framework
│
├── docker/                          # Docker deployment
├── docs/                            # Documentation
└── requirements/                    # Python dependencies
```

## Key Concepts

### Envelope

The `Envelope` is the state container that flows through the pipeline:

```python
envelope = {
    "envelope_id": "task-123",
    "task": "What's the weather?",
    "current_stage": "understand",
    "outputs": {
        "understanding": {"intent": "weather_query", "needs_search": True},
        "think_results": {"information": "...", "sources": [...]},
        "response": "Based on current data..."
    }
}
```

### Agent Configuration

Agents are defined declaratively:

```python
AgentConfig(
    name="understand",
    stage_order=0,
    has_llm=True,           # Uses LLM for inference
    model_role="planner",
    prompt_key="chatbot.understand",
    output_key="understanding",
    required_output_fields=["intent", "topic"],
    max_tokens=4000,        # Supports 8k context models
    temperature=0.3,
    pre_process=understand_pre_process,   # Build context
    post_process=understand_post_process, # Map intent → knowledge
)
```

### Routing Rules

For non-linear pipelines, agents can define conditional routing:

```python
AgentConfig(
    name="classifier",
    routing_rules=[
        RoutingRule(condition="type", value="urgent", target="priority_handler"),
        RoutingRule(condition="type", value="routine", target="batch_handler"),
    ],
    default_next="general_handler",
)
```

### Constitution R7

Capabilities must follow import boundaries:

```python
# CORRECT - Use adapters
from mission_system.adapters import create_llm_provider_factory

# INCORRECT - Don't import jeeves_infra directly
from jeeves_infra.llm import LLMProvider  # DON'T DO THIS

# Note: "avionics" was the legacy name for jeeves_infra
```

## Docker Deployment

For a complete local setup with llama.cpp:

```bash
# 1. Run setup (downloads ~2GB model)
bash docker/setup_hello_world.sh --build

# 2. Start services
docker compose -f docker/docker-compose.hello-world.yml up -d

# 3. Wait for healthy status
docker compose -f docker/docker-compose.hello-world.yml ps

# 4. Open http://localhost:8000
```

Services:
- **PostgreSQL** (port 5432) - Conversation history
- **llama.cpp** (port 8080) - Local LLM inference
- **Chatbot** (port 8000) - Gradio web interface

## Available Tools

| Tool | Description | Async |
|------|-------------|-------|
| `get_time` | Get current UTC date/time | No |
| `list_tools` | List available tools (introspection) | No |

## Knowledge Base

The chatbot includes an embedded knowledge base in `prompts/knowledge_base.py` with sections:

| Section | Content |
|---------|---------|
| `ecosystem_overview` | High-level architecture overview |
| `layer_details` | Detailed explanation of each layer |
| `key_concepts` | Core concepts (Envelope, AgentConfig, etc.) |
| `code_examples` | Practical code snippets |
| `hello_world_structure` | This capability's file structure |
| `how_to_guides` | Step-by-step guides for common tasks |

Knowledge is retrieved based on the classified intent, enabling targeted and relevant responses.

## Customization

### Adding a New Tool

1. Implement in `tools/hello_world_tools.py`:

```python
async def my_tool(query: str) -> Dict[str, Any]:
    """Your tool implementation."""
    return {"status": "success", "result": "..."}
```

2. Register in `capability/wiring.py`:

```python
catalog.register(
    tool_id="my_tool",
    func=my_tool,
    description="What my tool does",
    category="standalone",
    risk_level="read_only",
)
```

### Modifying Prompts

Edit files in `prompts/chatbot/`:
- `understand.py` - How intents are classified
- `respond.py` - How responses are generated
- `respond_streaming.py` - Streaming response format

## Learning Path

1. **Start here** - Understand the 3-agent pattern
2. **Read the prompts** - See how LLMs are instructed
3. **Trace a request** - Follow a message through the pipeline
4. **Add a tool** - Extend functionality
5. **Modify prompts** - Customize behavior
6. **Explore jeeves-core** - Understand the micro-kernel

## Documentation

| Document | Description |
|----------|-------------|
| [README.md](README.md) | This file |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute |
| [SECURITY.md](SECURITY.md) | Security policy |
| [CONSTITUTION.md](jeeves_capability_hello_world/CONSTITUTION.md) | Architectural rules |
| [docs/INDEX.md](docs/INDEX.md) | Documentation hub |
| [jeeves-core/README.md](jeeves-core/README.md) | Micro-kernel docs |
| [jeeves-airframe/README.md](jeeves-airframe/README.md) | Infrastructure docs |

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Apache License 2.0 - see [LICENSE.txt](LICENSE.txt)
