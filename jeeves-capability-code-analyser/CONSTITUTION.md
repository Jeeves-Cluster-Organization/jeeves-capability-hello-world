# Code Analysis Capability Constitution

**Parent:** [docs/CONSTITUTION.md](../docs/CONSTITUTION.md)
**Updated:** 2025-12-14

---

## Overview

This constitution defines the rules for **jeeves-capability-code-analyser**—the code analysis capability that implements the 7-agent pipeline for analyzing codebases.

**Core architecture:**
- Agents defined via `AgentConfig` in `pipeline_config.py`
- Pipeline defined via `PipelineConfig`
- No concrete agent classes - capability provides hooks only
- `UnifiedRuntime` executes the pipeline (from `jeeves_protocols.agents`)
- Capability OWNS all domain-specific configuration (language config, tool access matrix, deployment profiles, product identity)
- Mission system provides only generic mechanisms

**Capability responsibilities:**
- Pipeline configuration (`pipeline_config.py`)
- Domain configuration (`config/`)
- Hook functions for agent-specific logic
- Code analysis tools (composite, resilient, and base tools)
- Prompt templates and versioning
- **Capability registration** (`registration.py`) — Register schemas and modes at startup
- **Orchestration** (`orchestration/`) — LangGraph nodes and flow service

**Capability dependencies:**
- Depends on `jeeves_protocols` for agent types (AgentConfig, PipelineConfig, GenericEnvelope)
- Depends on `jeeves_mission_system` for orchestration primitives
- Depends on `jeeves_avionics.wiring` for ToolExecutor
- MUST NOT import directly from `coreengine/` (Go package)

---

## Layer Contract

### Inputs

**What this layer imports:**

1. **From jeeves_protocols** (REQUIRED)
   ```python
   from jeeves_protocols import (
       # Agent types (from config.py and agents.py)
       AgentConfig,
       PipelineConfig,
       RoutingRule,
       ToolAccess,
       UnifiedAgent,
       UnifiedRuntime,
       create_runtime_from_config,

       # Generic envelope (from envelope.py)
       GenericEnvelope,
       create_generic_envelope,

       # Enums (from core.py)
       TerminalReason,
       CriticVerdict,

       # Protocols (from protocols.py)
       LLMProviderProtocol,
       ToolExecutorProtocol,

       # Capability registration (from capability.py)
       CapabilityResourceRegistry,
       CapabilityModeConfig,
   )
   ```

2. **From jeeves_avionics** (for infrastructure)
   - `wiring.py`: ToolExecutor, create_llm_provider_factory
   - `settings.py`: Settings, get_settings
   - `database/factory.py`: create_database_client

3. **External libraries**
   - Pydantic (for models)
   - AsyncIO (for async execution)

**FORBIDDEN imports:**
```python
# ❌ NEVER DO THIS
from coreengine.agents import Agent           # Go package
from coreengine.envelope import CoreEnvelope  # Go package

# ✅ ALWAYS DO THIS
from jeeves_protocols import (
    AgentConfig,
    PipelineConfig,
    GenericEnvelope,
    UnifiedRuntime,
)
```

### Outputs

**What this layer exports:**

1. **config/** — Domain-specific configuration (OWNED by capability)
   - `language_config.py` — LanguageId, LanguageSpec, LANGUAGE_SPECS
   - `tool_access.py` — AgentToolAccess, TOOL_CATEGORIES
   - `modes.py` — AGENT_MODES, pipeline mode configuration
   - `deployment.py` — NodeProfile, PROFILES, CODE_ANALYSIS_AGENTS
   - `identity.py` — PRODUCT_NAME, PRODUCT_VERSION, PRODUCT_DESCRIPTION

2. **pipeline_config.py** — Pipeline configuration
   - `CODE_ANALYSIS_PIPELINE` — PipelineConfig with 7 agents
   - `get_code_analysis_pipeline()` — Factory function
   - Hook functions for each agent

3. **tools/** — Code analysis tools
   - Composite tools: locate, explore_symbol_usage, map_module, etc.
   - Resilient tools: read_code, find_related
   - Base tools: read_file, glob_files, grep_search, etc.

4. **prompts/** — LLM prompt templates
   - Versioned prompts for each agent
   - Prompt registry and mapping

---

## Centralized Agent Architecture

### Pipeline Configuration

All agents defined in `pipeline_config.py`:

```python
CODE_ANALYSIS_PIPELINE = PipelineConfig(
    name="code_analysis",
    max_iterations=3,
    max_llm_calls=10,
    max_agent_hops=21,
    enable_arbiter=False,  # Read-only pipeline

    agents=[
        AgentConfig(
            name="perception",
            stage_order=0,
            has_llm=False,
            pre_process=perception_pre_process,
            default_next="intent",
        ),
        AgentConfig(
            name="intent",
            stage_order=1,
            has_llm=True,
            model_role="planner",
            prompt_key="code_analysis.intent",
            routing_rules=[
                RoutingRule("clarification_needed", True, "clarification"),
            ],
            default_next="planner",
        ),
        # ... 5 more agents
    ],
)
```

### Hook Functions

Capability-specific logic provided via hooks:

```python
def perception_pre_process(envelope, agent=None):
    """Normalize input, load context."""
    output = {
        "normalized_input": envelope.raw_input.strip(),
        "context_summary": envelope.metadata.get("context_summary", ""),
    }
    envelope.outputs["perception"] = output
    return envelope

def intent_post_process(envelope, output, agent=None):
    """Initialize goals after intent."""
    goals = output.get("goals", [])
    if goals:
        envelope.initialize_goals(goals)
    return envelope

def critic_post_process(envelope, output, agent=None):
    """Handle critic verdict routing."""
    verdict = output.get("verdict", "approved")
    # Handle goal updates, store feedback for reintent
    return envelope
```

### No Concrete Agent Classes

**REMOVED:**
- `CodeAnalysisPerceptionAgent`
- `CodeAnalysisIntentAgent`
- `CodeAnalysisPlannerAgent`
- `CodeAnalysisTraverserAgent`
- `CodeAnalysisSynthesizerAgent`
- `CodeAnalysisCriticAgent`
- `CodeAnalysisIntegrationAgent`

**REPLACED WITH:**
- `AgentConfig` definitions in `pipeline_config.py`
- Hook functions for capability-specific logic
- Mock handlers for testing

---

## Agent Configuration

| # | Agent | has_llm | has_tools | tool_access | Hooks |
|---|-------|---------|-----------|-------------|-------|
| 1 | perception | False | False | READ | pre_process |
| 2 | intent | True | False | NONE | post_process, mock_handler |
| 3 | planner | True | False | READ | mock_handler |
| 4 | executor | False | True | ALL | post_process |
| 5 | synthesizer | True | False | NONE | mock_handler |
| 6 | critic | True | False | NONE | post_process, mock_handler |
| 7 | integration | True | False | WRITE | post_process, mock_handler |

---

## Architecture Principles

### P1: Accuracy First (Inherited)

Every claim requires `[file:line]` citation from tool execution.

### P2: Code Context Priority (Inherited)

Read source before claiming.

### P3: Bounded Efficiency (Inherited)

Respect limits, degrade gracefully.

### P4: Tool Boundary

Only 9 tools exposed to agents (composite + resilient).

### P5: Configuration over Code

Agents defined via `AgentConfig`, not class inheritance.

---

## Tool Organization

### Composite Tools

**Location:** `tools/composite/`

**Examples:**
- `locate` — Find symbol via index → grep → semantic search
- `explore_symbol_usage` — Find symbol + get usages + related files
- `map_module` — Tree structure + file symbols + imports

### Resilient Tools

**Location:** `tools/resilient/`

**Examples:**
- `read_code` — Try exact path → extension swap → glob patterns
- `find_related` — Find related files without requiring file to exist

### Base Tools

**Location:** `tools/base/`

**Examples:**
- `read_file`, `glob_files`, `grep_search`, `tree_structure`
- `find_symbol`, `get_file_symbols`, `get_imports`

---

## Operational Rules

### R1: Import from jeeves_protocols

**Always:**
```python
from jeeves_protocols import (
    AgentConfig,
    PipelineConfig,
    GenericEnvelope,
    UnifiedRuntime,
)
```

**Never:**
```python
from coreengine.agents import Agent        # ❌ Go package
from coreengine.envelope import CoreEnvelope  # ❌ Go package
```

### R2: Define Agents via Config

**Always:**
```python
AgentConfig(
    name="intent",
    has_llm=True,
    model_role="planner",
    prompt_key="code_analysis.intent",
)
```

**Never:**
```python
class CodeAnalysisIntentAgent(Agent):  # ❌ No concrete classes
    pass
```

### R3: Capability Logic via Hooks

**Always:**
```python
AgentConfig(
    name="intent",
    post_process=intent_post_process,
    mock_handler=intent_mock_handler,
)
```

**Never:**
```python
class IntentAgent:
    def process(self, envelope):  # ❌ No process methods
        pass
```

### R4: Evidence Chain Integrity

Executor executes tools → Synthesizer aggregates → Integration responds

### R5: Bounded Retry

- Max 2 retries per tool step
- Partial results acceptable

### R6: Domain Config Ownership

**Capability owns domain-specific configuration:**

```python
# ✅ CORRECT - Import from capability config
from jeeves_capability_code_analyser.config import (
    LanguageId,
    LanguageConfig,
    AgentToolAccess,
    PROFILES,
    PRODUCT_NAME,
)

# ❌ INCORRECT - Import from mission_system (removed)
from jeeves_mission_system.config.language_config import LanguageId  # Deleted
from jeeves_mission_system.config.node_profiles import PROFILES       # Deleted
```

**Mission system provides generic mechanisms only:**
- `ConfigRegistry` — Generic config injection
- `AgentProfile` — Generic per-agent config types (LLM, thresholds)
- Operational thresholds (not domain-specific)

### R7: Capability Registration

**Capability MUST register its resources at application startup:**

```python
# registration.py
from jeeves_protocols import get_capability_resource_registry, CapabilityModeConfig

def register_capability() -> None:
    """Register code_analysis capability resources with infrastructure.

    Call at application startup, BEFORE infrastructure initialization.
    """
    registry = get_capability_resource_registry()

    # Register database schema (owned by capability)
    schema_path = str(CAPABILITY_ROOT / "database" / "schemas" / "002_code_analysis_schema.sql")
    registry.register_schema("code_analysis", schema_path)

    # Register gateway mode configuration
    registry.register_mode("code_analysis", CapabilityModeConfig(
        mode_id="code_analysis",
        response_fields=["files_examined", "citations", "thread_id"],
        requires_repo_path=False,
    ))
```

**Usage at startup:**
```python
# At application entry point
from jeeves_capability_code_analyser import register_capability
register_capability()  # MUST be called before infrastructure init
```

**Why registration is required:**
- Infrastructure (avionics) must NOT have hardcoded capability knowledge
- Enables non-capability layers to be extracted as a separate package
- Supports multiple capabilities with different schemas and modes
- Follows Avionics R3 (No Domain Logic) and R4 (Swappable Implementations)

---

## Forbidden Patterns

**Do NOT:**
- Create concrete agent classes
- Import deprecated types (Agent, CoreEnvelope, EnvelopeStage, AgentStage)
- Bypass mission_system.contracts
- Hallucinate code without tool execution
- Import domain config from mission_system (LanguageConfig, NodeProfiles, etc. are in capability)

---

*This constitution defines the rules for the jeeves-capability-code-analyser package. See [docs/CONSTITUTION.md](../docs/CONSTITUTION.md) for the overview constitution.*
