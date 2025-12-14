# Jeeves Code Analysis Capability - Repository Index

**Version:** 1.0.0 | **Status:** Development | **Updated:** 2025-12-14

---

## Overview

This repository contains the **Jeeves Code Analysis Capability** - a 7-agent pipeline for read-only code analysis with citation-backed responses.

**Architecture:** Configuration-driven agents with hook functions (no concrete agent classes)

**Dependencies:** Requires `jeeves-core` submodule for core infrastructure.

```bash
# Initialize submodule
git submodule update --init --recursive
```

---

## Directory Structure

```
jeeves-capability-code-analysis/
|
+-- jeeves-capability-code-analyser/    # Main capability package
|   +-- agents/                         # Agent helpers (context, summarizer)
|   +-- tools/                          # Code analysis tools
|   +-- config/                         # Domain configuration
|   +-- orchestration/                  # LangGraph workflow
|   +-- contracts/                      # Data contracts
|   +-- models/                         # Domain models
|   +-- prompts/                        # LLM prompts
|   +-- tests/                          # Unit tests
|
+-- tests/                              # Integration/deployment tests
+-- docs/                               # Documentation
+-- docker/                             # Docker configuration
+-- requirements/                       # Python dependencies
+-- scripts/                            # Utility scripts
+-- jeeves-core/                        # Core infrastructure (submodule)
```

---

## Key Documentation

| Document | Purpose |
|----------|---------|
| [README.md](README.md) | Project overview and quick start |
| [docs/CONSTITUTION.md](docs/CONSTITUTION.md) | Capability layer constitution |
| [docs/TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md) | Test organization and strategy |
| [jeeves-capability-code-analyser/CONSTITUTION.md](jeeves-capability-code-analyser/CONSTITUTION.md) | Detailed capability rules |

---

## Main Package

### jeeves-capability-code-analyser/

| File/Directory | Purpose |
|----------------|---------|
| `__init__.py` | Package init, exports `register_capability()` |
| `registration.py` | Capability resource registration |
| `pipeline_config.py` | 7-agent pipeline configuration |
| `server.py` | gRPC capability server |
| `CONSTITUTION.md` | Capability layer constitution |

### agents/

| File | Purpose |
|------|---------|
| `context_builder.py` | Context building for agents |
| `summarizer.py` | Tool result summarization |
| `prompt_mapping.py` | Prompt mapping utilities |
| `protocols.py` | Agent protocols/interfaces |

### tools/

| File | Purpose |
|------|---------|
| `__init__.py` | Tool initialization, `initialize_all_tools()` |
| `registration.py` | Tool registration with catalog |
| `unified_analyzer.py` | Primary analyzer tool |
| `code_parser.py` | Code parsing utilities |
| `file_navigator.py` | File system navigation |
| `module_mapper.py` | Module dependency mapping |
| `flow_tracer.py` | Control flow tracing |
| `symbol_explorer.py` | Symbol resolution |
| `git_historian.py` | Git history analysis |
| `safe_locator.py` | Safe file locator |

### tools/base/

| File | Purpose |
|------|---------|
| `code_tools.py` | Core code analysis tools |
| `git_tools.py` | Git operations |
| `index_tools.py` | Symbol indexing |
| `resilient_ops.py` | Retry logic |
| `semantic_tools.py` | Semantic search |
| `session_tools.py` | Session management |
| `citation_validator.py` | Citation validation |
| `path_helpers.py` | Path utilities |

### config/

| File | Purpose |
|------|---------|
| `language_config.py` | Language-specific settings |
| `tool_profiles.py` | Tool profile definitions |
| `tool_access.py` | Tool access control |
| `deployment.py` | Deployment configuration |
| `modes.py` | Operational modes |
| `identity.py` | Product identity |
| `llm_config.py` | LLM provider settings |

### orchestration/

| File | Purpose |
|------|---------|
| `service.py` | CodeAnalysisService |
| `servicer.py` | gRPC servicer |
| `wiring.py` | Dependency wiring |
| `types.py` | Type definitions |

---

## Testing

| Directory | Purpose |
|-----------|---------|
| `jeeves-capability-code-analyser/tests/` | Unit tests for capability |
| `jeeves-capability-code-analyser/tests/fixtures/` | Test fixtures and mocks |
| `tests/integration/` | Service integration tests |
| `tests/deployment/` | Docker infrastructure tests |
| `tests/ui_ux/` | API endpoint tests |

### Test Commands

```bash
# Unit tests
pytest jeeves-capability-code-analyser/tests -v

# Integration tests (requires services)
pytest tests/integration -v

# All tests
pytest -v
```

---

## Core Principles

1. **P1: Accuracy First** - Never hallucinate code. Every claim requires `[file:line]` citation.
2. **P2: Code Context Priority** - Understand fully before claiming.
3. **P3: Bounded Efficiency** - Be efficient within limits.

**Hierarchy:** P1 > P2 > P3

---

## Import Rules

```python
# Correct - Import from jeeves_protocols
from jeeves_protocols import (
    AgentConfig,
    PipelineConfig,
    GenericEnvelope,
    CapabilityResourceRegistry,
)

# Correct - Import from jeeves_mission_system
from jeeves_mission_system.contracts import (
    tool_catalog,
    ToolId,
    LoggerProtocol,
)

# Never - Direct imports from Go packages
from coreengine.agents import Agent  # Wrong
```

---

*Last Updated: 2025-12-14*
