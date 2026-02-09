# Documentation Index

**Your guide to understanding the Jeeves ecosystem**

---

## Getting Started

| Document | Description |
|----------|-------------|
| [README.md](../README.md) | Project overview and quick start |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | How to contribute |
| [SECURITY.md](../SECURITY.md) | Security policy |

---

## Architecture

### This Capability

| Document | Description |
|----------|-------------|
| [CONSTITUTION.md](CONSTITUTION.md) | Capability layer constitution and rules |
| [CAPABILITY_CONSTITUTION.md](CAPABILITY_CONSTITUTION.md) | Detailed capability architecture |
| [Package CONSTITUTION](../jeeves_capability_hello_world/CONSTITUTION.md) | Internal capability rules |

### Jeeves Core (Micro-Kernel)

| Document | Description |
|----------|-------------|
| [jeeves-core README](../jeeves-core/README.md) | Rust micro-kernel overview |
| [jeeves-core CONSTITUTION](../jeeves-core/CONSTITUTION.md) | Kernel layer rules |
| [jeeves-core CONTRIBUTING](../jeeves-core/CONTRIBUTING.md) | Contributing to the kernel |

### Infrastructure Layer

| Document | Description |
|----------|-------------|
| [jeeves-airframe README](../jeeves-airframe/README.md) | Infrastructure layer overview |
| [mission_system CONSTITUTION](../jeeves-airframe/mission_system/CONSTITUTION.md) | Orchestration framework rules |
| [mission_system INDEX](../jeeves-airframe/mission_system/INDEX.md) | Mission system documentation |

---

## Integration Guides

| Document | Description |
|----------|-------------|
| [CAPABILITY_INTEGRATION_GUIDE.md](CAPABILITY_INTEGRATION_GUIDE.md) | How capabilities integrate with jeeves-core |
| [PIPELINE_PATTERNS.md](PIPELINE_PATTERNS.md) | Advanced routing, DAGs, branching |
| [envelope_json_schema.md](envelope_json_schema.md) | Envelope state JSON schema |

---

## Deployment

| Document | Description |
|----------|-------------|
| [k8s/README.md](../k8s/README.md) | Kubernetes deployment |
| [docker/](../docker/) | Docker Compose files |

---

## Understanding the Layers

### Layer 0: Protocols (jeeves_infra.protocols)

Zero-dependency type definitions:
- **Protocols** - Interface contracts (LLMProviderProtocol, etc.)
- **Types** - Enums, dataclasses (AgentConfig, PipelineConfig, Envelope)
- **Utilities** - Shared helpers

### Layer 1: Rust Kernel (jeeves-core/src)

The Rust micro-kernel (accessed via `KernelClient` gRPC bridge):
- **Process lifecycle** - NEW → READY → RUNNING → TERMINATED
- **Resource quotas** - Limits on iterations, LLM calls, agent hops
- **Pipeline orchestration** - Multi-stage agent execution

### Layer 2: Memory (mission_system.memory)

Memory and event sourcing:
- **Session state** - Working memory, focus state
- **Semantic search** - pgvector integration
- **Event sourcing** - Domain events with deduplication

### Layer 3: Infrastructure (jeeves_infra)

Infrastructure implementations:
- **LLM providers** - OpenAI, Anthropic, llama.cpp adapters
- **Database clients** - PostgreSQL, pgvector
- **KernelClient** - gRPC bridge to Rust kernel
- **Gateway** - HTTP/WebSocket translation

### Layer 4: Mission System & Capabilities

Orchestration + domain logic:
- **mission_system** - Adapters, agent profiles, prompt registry
- **Capabilities** - Prompts, tools, pipeline config

---

## Key Patterns

### Import Boundaries (Constitution R7)

```python
# CORRECT - Capabilities use adapters
from mission_system.adapters import create_llm_provider_factory

# INCORRECT - Don't bypass the adapter layer
from jeeves_infra.llm import LLMProvider  # DON'T DO THIS
```

> **Note:** `avionics` was the legacy name for `jeeves_infra`.

### Agent Configuration

```python
AgentConfig(
    name="understand",
    has_llm=True,           # Uses LLM
    has_tools=False,        # No tool access
    prompt_key="chatbot.understand",
    output_key="understanding",
    required_output_fields=["intent", "topic"],
    pre_process=understand_pre_process,
    post_process=understand_post_process,
)
```

### Conditional Routing

For non-linear pipelines, use `RoutingRule`:

```python
AgentConfig(
    name="router",
    routing_rules=[
        RoutingRule(condition="type", value="A", target="handler_a"),
        RoutingRule(condition="type", value="B", target="handler_b"),
    ],
    default_next="default_handler",
)
```

See [PIPELINE_PATTERNS.md](PIPELINE_PATTERNS.md) for DAG and fan-out/fan-in examples.

### Intent-Based Knowledge Retrieval

The chatbot uses a sectioned knowledge base with intent-based retrieval:

```python
# In pipeline hooks (pipeline_config.py)
def _get_knowledge_sections_for_intent(intent: str, topic: str) -> list:
    section_map = {
        "architecture": ["ecosystem_overview", "layer_details"],
        "concept": ["key_concepts", "code_examples"],
        "getting_started": ["hello_world_structure", "how_to_guides"],
        "component": ["ecosystem_overview", "layer_details"],
        "general": ["ecosystem_overview"],
    }
    return section_map.get(intent, ["ecosystem_overview"])

# In think_pre_process
targeted_knowledge = get_knowledge_for_sections(knowledge_sections)
envelope.metadata["targeted_knowledge"] = targeted_knowledge
```

This pattern avoids dumping all knowledge into the prompt, reducing token usage and improving relevance.

### Tool Registration

```python
catalog.register(
    tool_id="my_tool",
    func=my_tool_function,
    description="What it does",
    category="standalone",
    risk_level="read_only",
)
```

---

*Last Updated: 2026-02-02*
