# Code Analysis Capability Constitution

**Parent:** [docs/CONSTITUTION.md](../docs/CONSTITUTION.md)
**Updated:** 2026-01-06

---

## Overview

This constitution defines the rules for **jeeves-capability-code-analyser**—the code analysis capability that implements the 7-agent pipeline for analyzing codebases.

**Core architecture:**
- Agents defined via `AgentConfig` in `pipeline_config.py`
- Pipeline defined via `PipelineConfig`
- No concrete agent classes - capability provides hooks only
- `UnifiedRuntime` executes the pipeline (from `protocols.agents`)
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
- Depends on `protocols` for agent types (AgentConfig, PipelineConfig, GenericEnvelope)
- Depends on `mission_system.contracts_core` for protocols (ToolExecutorProtocol, LoggerProtocol)
- Receives infrastructure via **dependency injection** (ToolExecutor injected at bootstrap, not imported)
- MUST NOT import directly from `avionics` (layer violation)
- MUST NOT import directly from `coreengine/` (Go package)

---

## Layer Contract

### Inputs

**What this layer imports:**

1. **From protocols** (REQUIRED)
   ```python
   from protocols import (
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

2. **From mission_system** (for infrastructure access)
   ```python
   from mission_system.contracts_core import (
       ToolExecutorProtocol,
       LoggerProtocol,
       PersistenceProtocol,
       ContextBounds,
   )
   from mission_system.adapters import (
       get_logger,
       get_settings,
       get_feature_flags,
   )
   ```

   **NOTE:** Concrete implementations (ToolExecutor, LLM providers, database clients)
   are injected via dependency injection at bootstrap time. The capability layer
   NEVER imports these directly from avionics.

3. **External libraries**
   - Pydantic (for models)
   - AsyncIO (for async execution)

**FORBIDDEN imports:**
```python
# ❌ NEVER DO THIS - Go package
from coreengine.agents import Agent
from coreengine.envelope import CoreEnvelope

# ❌ NEVER DO THIS - Layer violation (L5 → L2)
from avionics.wiring import ToolExecutor
from avionics.settings import get_settings
from avionics.database.factory import create_database_client
from avionics.tools.catalog import ToolId  # Use capability's own ToolId

# ✅ CORRECT - Import protocols from L0 or L4
from protocols import (
    AgentConfig,
    PipelineConfig,
    GenericEnvelope,
    UnifiedRuntime,
    ToolExecutorProtocol,  # Interface, not concrete
)

# ✅ CORRECT - Import from mission_system adapters
from mission_system.adapters import get_logger, get_settings

# ✅ CORRECT - Import from capability's own modules
from tools.catalog import ToolId  # Capability-owned ToolId
```

### Outputs

**What this layer exports:**

1. **config/** — Domain-specific configuration (OWNED by capability)
   - `language_config.py` — LanguageId, LanguageSpec, LANGUAGE_SPECS
   - `tool_access.py` — AgentToolAccess, TOOL_CATEGORIES
   - `tool_profiles.py` — Tool selection based on (Operation, TargetKind)
   - `deployment.py` — CODE_ANALYSIS_AGENTS list
   - `identity.py` — PRODUCT_NAME, PRODUCT_VERSION, PRODUCT_DESCRIPTION

2. **pipeline_config.py** — Pipeline configuration
   - `CODE_ANALYSIS_PIPELINE` — PipelineConfig with 7 agents (full mode)
   - `CODE_ANALYSIS_PIPELINE_STANDARD` — 6 agents, skips critic (faster)
   - `PIPELINE_MODES` — Dict mapping mode names to PipelineConfig
   - `get_pipeline_for_mode(mode)` — Get pipeline by mode name
   - `get_code_analysis_pipeline()` — Factory function (returns full pipeline)
   - Hook functions for each agent

3. **k8s/** — Kubernetes deployment manifests (infrastructure-as-code)
   - `base/` — Single-node deployment (development)
   - `overlays/distributed/` — Multi-node deployment (node1, node2, node3)

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

### R1: Import from protocols

**Always:**
```python
from protocols import (
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
    CODE_ANALYSIS_AGENTS,
    PRODUCT_NAME,
)

# ✅ CORRECT - Import pipeline modes from pipeline_config
from pipeline_config import get_pipeline_for_mode, PIPELINE_MODES

# ❌ INCORRECT - Import from mission_system (removed)
from mission_system.config.language_config import LanguageId  # Deleted
```

**Deployment configuration extracted to k8s/ manifests:**
- Node profiles, GPU assignments, resource limits now in k8s/
- Python code only defines agent list (CODE_ANALYSIS_AGENTS)
- See `k8s/README.md` for deployment documentation

**Mission system provides generic mechanisms only:**
- `ConfigRegistry` — Generic config injection
- `AgentProfile` — Generic per-agent config types (LLM, thresholds)
- Operational thresholds (not domain-specific)

### R7: Dependency Injection Pattern

**Capability receives infrastructure via injection, never imports:**

```python
# orchestration/service.py - CORRECT PATTERN
class CodeAnalysisService:
    def __init__(
        self,
        *,
        llm_provider_factory,           # Injected factory
        tool_executor: ToolExecutorProtocol,  # Injected via protocol
        logger: LoggerProtocol,         # Injected via protocol
        persistence: Optional[PersistenceProtocol] = None,
        pipeline_config: Optional[PipelineConfig] = None,  # Mode-selected pipeline
    ):
        # Use provided pipeline or default to full
        config = pipeline_config or CODE_ANALYSIS_PIPELINE

        # Use injected dependencies - no avionics imports
        self._runtime = create_runtime_from_config(
            config=config,
            llm_provider_factory=llm_provider_factory,
            tool_executor=tool_executor,
            logger=logger,
        )
```

**Bootstrap (composition root) creates and injects:**

```python
# bootstrap.py (in mission_system) - COMPOSITION ROOT
from avionics.wiring import ToolExecutor  # Only bootstrap imports avionics

tool_executor = ToolExecutor(registry=tool_registry, logger=logger)
service = CodeAnalysisService(
    tool_executor=tool_executor,  # Inject as protocol
    ...
)
```

**Why this matters:**
- Capability depends on abstractions (protocols), not concretions (implementations)
- Enables testing with mocks
- Maintains layer boundaries (L5 never imports L2)
- Composition root is the ONLY place that wires concrete implementations

### R8: Capability Registration

**Capability MUST register its resources at application startup:**

```python
# registration.py
from protocols import get_capability_resource_registry, CapabilityModeConfig

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
- Import directly from `avionics` (use adapters or receive via DI)
- Import `ToolId` from avionics catalog (use capability's own `tools/catalog.py`)

---

*This constitution defines the rules for the jeeves-capability-code-analyser package. See [docs/CONSTITUTION.md](../docs/CONSTITUTION.md) for the overview constitution.*
