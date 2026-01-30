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
| [jeeves-core README](../jeeves-core/README.md) | Go micro-kernel overview |
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
| [JEEVES_CORE_RUNTIME_CONTRACT.md](JEEVES_CORE_RUNTIME_CONTRACT.md) | Runtime contract specification |
| [envelope_json_schema.md](envelope_json_schema.md) | Envelope state JSON schema |

---

## Deployment

| Document | Description |
|----------|-------------|
| [k8s/README.md](../k8s/README.md) | Kubernetes deployment |
| [docker/](../docker/) | Docker Compose files |

---

## Analysis & Audits

| Document | Description |
|----------|-------------|
| [CAPABILITY_LAYER_AUDIT_REPORT.md](CAPABILITY_LAYER_AUDIT_REPORT.md) | Import wiring audit |
| [analysis-reports/COVERAGE_ANALYSIS.md](analysis-reports/COVERAGE_ANALYSIS.md) | Test coverage analysis |
| [analysis-reports/JEEVES_CORE_ANALYSIS.md](analysis-reports/JEEVES_CORE_ANALYSIS.md) | jeeves-core integration analysis |

---

## Understanding the Layers

### Layer 1: jeeves-core (Go)

The micro-kernel provides:
- **Pipeline orchestration** - Multi-stage agent execution
- **Envelope state** - Immutable state transitions
- **Resource quotas** - Limits on iterations, LLM calls, agent hops
- **gRPC services** - Communication with Python layer

### Layer 2: jeeves-infra (Python)

Infrastructure implementations:
- **LLM providers** - OpenAI, Anthropic, llama.cpp adapters
- **Database clients** - PostgreSQL, pgvector
- **Protocols** - Type definitions and interfaces
- **Gateway** - HTTP/WebSocket/gRPC translation

### Layer 3: mission_system (Python)

Orchestration framework:
- **Agent profiles** - Per-agent configuration
- **Adapters** - Clean interface for capabilities
- **Event handling** - Pipeline event emission
- **Prompt registry** - Centralized prompt management

### Layer 4: Capabilities (Python)

Your domain logic:
- **Prompts** - LLM instructions for each agent
- **Knowledge Base** - Embedded domain knowledge (sectioned)
- **Tools** - Domain-specific actions
- **Pipeline config** - Agent orchestration with hooks
- **Service layer** - Business logic wrapper

---

## Key Patterns

### Import Boundaries (Constitution R7)

```python
# CORRECT - Capabilities use adapters
from mission_system.adapters import create_llm_provider_factory

# INCORRECT - Don't bypass the adapter layer
from avionics.llm import LLMProvider  # DON'T DO THIS
```

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

*Last Updated: 2026-01-30*
