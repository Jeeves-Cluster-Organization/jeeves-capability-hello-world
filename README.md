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
│  - Analyzes user intent                 │
│  - Decides if web search is needed      │
│  - Output: {intent, needs_search}       │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  THINK (Tools Only - No LLM)            │
│  - Executes tools if needed             │
│  - Pure tool execution, no inference    │
│  - Output: {information, sources}       │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  RESPOND (LLM)                          │
│  - Synthesizes information              │
│  - Crafts helpful response              │
│  - Streams tokens to user               │
└─────────────────────────────────────────┘
    ↓
Response to User
```

**Key insight**: The middle agent has **no LLM** - it only executes tools. This is a common pattern that separates reasoning from action.

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
# Option A: OpenAI
export LLM_PROVIDER=openai
export OPENAI_API_KEY=your_key_here

# Option B: Anthropic
export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=your_key_here

# Option C: Local llama.cpp (see Docker section)
export LLM_PROVIDER=llamaserver
export LLAMASERVER_HOST=http://localhost:8080
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
│   ├── prompts/chatbot/             # LLM prompts
│   │   ├── understand.py            # Intent classification
│   │   ├── respond.py               # Response synthesis
│   │   └── respond_streaming.py     # Streaming-optimized
│   │
│   ├── tools/                       # Available tools
│   │   ├── hello_world_tools.py     # web_search, get_time, list_tools
│   │   ├── catalog.py               # Tool metadata
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
    max_tokens=2000,
    temperature=0.3,
)
```

### Constitution R7

Capabilities must follow import boundaries:

```python
# CORRECT - Use adapters
from mission_system.adapters import create_llm_provider_factory

# INCORRECT - Don't import avionics directly
from avionics.llm import LLMProvider  # DON'T DO THIS
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
| `web_search` | Search the web for current information | Yes |
| `get_time` | Get current UTC date/time | No |
| `list_tools` | List available tools (introspection) | No |

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
