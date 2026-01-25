# Capability Layer Audit Report

**Date:** December 13, 2025
**Scope:** jeeves-capability-code-analyser import wiring and compatibility layer
**Reference:** Capability Layer Integration Guide (docs/CAPABILITY_INTEGRATION_GUIDE.md)

## Executive Summary

The capability layer imports have been audited against the integration guide. **All imports are correctly wired** following the layer boundaries:

```
L3 Capability (jeeves-capability-code-analyser)
    ↓ imports from
L2 Mission System (mission_system)
    ↓ imports from
L1 Avionics (avionics) - restricted to scripts only
    ↓ imports from
L0 Protocols/Shared (protocols, shared)
```

## Audit Results

### 1. protocols Imports (L0) ✅ CORRECT

All protocol imports are from `protocols` as required:

| Import | Files Using |
|--------|-------------|
| `RiskLevel` | context_builder.py, session_tools.py, safe_locator.py, git_tools.py, index_tools.py, resilient_ops.py, semantic_tools.py, mocks/tools.py, test_tool_registry.py |
| `OperationStatus` | models/__init__.py, types.py, symbol_explorer.py, unified_analyzer.py, module_mapper.py |
| `ToolCategory` | tools/__init__.py, unified_analyzer.py, resilient_ops.py, registration.py |
| `ToolAccess` | config/__init__.py, tool_access.py |
| ~~`NodeProfile`~~ | ~~config/deployment.py~~ (removed in 2026-01-23 cleanup; now in k8s/) |
| `AgentLLMConfig` | config/llm_config.py |
| `CapabilityResourceRegistry` types | registration.py |

### 2. mission_system Imports (L2) ✅ CORRECT

Mission system imports use the proper adapters and contracts:

**Adapters (get_logger):**
- `from mission_system.adapters import get_logger` - 15+ files

**Contracts:**
- `LoggerProtocol`, `ContextBounds`, `PersistenceProtocol` - protocols
- `ToolId`, `tool_catalog`, `EXPOSED_TOOL_IDS` - tool contracts
- `ConfigKeys`, `get_config_registry` - config registry
- `WorkingMemory` - memory contracts

**Config:**
- `from mission_system.config.agent_profiles import LLMProfile, ThresholdProfile, AgentProfile`

**Contracts Core (orchestration):**
- `from mission_system.contracts_core import ...` - for pipeline/orchestration

**Orchestrator:**
- `from mission_system.orchestrator.state import JeevesState`
- `from mission_system.orchestrator.agent_events import AgentEvent, AgentEventType`

**Prompts:**
- `from mission_system.prompts.core.registry import register_prompt, PromptRegistry`

### 3. avionics Imports (L1) ✅ CORRECT

Avionics imports are **restricted to scripts only** as per the guide:

| File | Location | Status |
|------|----------|--------|
| `verify_configuration.py` | scripts/diagnostics/ | ✅ Allowed |
| `run_local_tests.py` | scripts/testing/ | ✅ Allowed |

**No direct avionics imports in core capability code.**

### 4. shared Imports ✅ CORRECT

Only in root `conftest.py` for test utilities:
- `from shared.uuid_utils import uuid_str`

### 5. Registration Pattern ✅ CORRECT

`registration.py` correctly implements Constitution R7:

```python
from protocols import (
    CapabilityServiceConfig,
    CapabilityModeConfig,
    CapabilityOrchestratorConfig,
    CapabilityToolsConfig,
    CapabilityAgentConfig,
    CapabilityContractsConfig,
    get_capability_resource_registry,
)
```

Registers:
- Database schema
- Gateway mode configuration
- Service configuration
- Orchestrator factory
- Tools initializer
- Agent definitions
- Prompts
- Contracts

### 6. Python Path Configuration ✅ CORRECT

All entry points include jeeves-core submodule in sys.path:

| File | Path Setup |
|------|------------|
| `conftest.py` (root) | ✅ `jeeves-core` added to sys.path |
| `run_worker.py` | ✅ `jeeves-core` added to sys.path |
| `jeeves-capability-code-analyser/tests/conftest.py` | ✅ `jeeves-core` added to sys.path |
| `jeeves-capability-code-analyser/scripts/testing/run_local_tests.py` | ✅ `jeeves-core` added to sys.path |
| `jeeves-capability-code-analyser/scripts/diagnostics/verify_configuration.py` | ✅ `jeeves-core` added to sys.path |

## Issues Found

**None.** All imports follow the layer boundaries defined in the integration guide.

## Previously Fixed Issues

The following issues were fixed in the previous session:

1. **RiskLevel import location** - Changed from `mission_system.contracts` to `protocols`
2. **ToolCategory import location** - Changed from `mission_system.contracts` to `protocols`
3. **sys.path configuration** - Added jeeves-core submodule path to all entry points

## Verification Checklist

- [x] L0 protocols imported from `protocols`
- [x] L2 mission system contracts imported from `mission_system.contracts`
- [x] L2 adapters imported from `mission_system.adapters`
- [x] L1 avionics imports restricted to scripts only
- [x] Registration uses `get_capability_resource_registry()` from `protocols`
- [x] Capability config classes imported from `protocols`
- [x] Python path includes `jeeves-core/` submodule directory
- [x] No direct imports from `jeeves_core_engine` in capability code
- [x] No direct imports from `avionics` in core capability code (only scripts)

## Runtime Verification Required

The audit confirms **static import correctness**. Runtime verification requires the jeeves-core submodule to be initialized with content. To verify:

```bash
# Initialize submodule
git submodule update --init --recursive

# Run tests
cd jeeves-capability-code-analyser
pytest tests/ -v

# Run diagnostic
python scripts/diagnostics/verify_configuration.py
```

## Cleanup Update (2026-01-23)

Following the initial audit, a k8s-aligned cleanup was performed:

### Removed/Simplified

| File | Change | Reason |
|------|--------|--------|
| `config/modes.py` | Deleted | Modes are now PipelineConfig variants in `pipeline_config.py` |
| `config/deployment.py` | Simplified | Functions extracted to `k8s/` manifests; only `CODE_ANALYSIS_AGENTS` remains |
| `tests/unit/config/test_deployment.py` | Deleted | Tested Python functions now in k8s manifests |
| `models/types.py` | Trimmed | Unused Pydantic models removed; kept `TargetKind`, `Operation` |

### Added

| File | Purpose |
|------|---------|
| `k8s/base/` | Single-node Kubernetes manifests |
| `k8s/overlays/distributed/` | Multi-node deployment manifests |
| `pipeline_config.py` | Added `PIPELINE_MODES`, `get_pipeline_for_mode()` |

### Updated Imports

- `NodeProfile` no longer imported from `protocols` in capability code
- `PROFILES` dict removed from capability (now in k8s manifests)
- Validation wired into `synthesizer_pre_process` via `contracts.validation`

---

## Conclusion

The capability layer is **correctly wired** according to the Capability Layer Integration Guide. The import hierarchy respects the constitutional boundaries:

- L0 (protocols) - Pure protocols, no side effects
- L2 (mission_system) - Contracts and adapters for capability use
- L1 (avionics) - Restricted to diagnostic scripts only
- L3 (capability) - Uses L0 and L2 only in core code

The capability is ready for layer extraction and can be deployed as a standalone package.

---

*Last Updated: 2026-01-23*
