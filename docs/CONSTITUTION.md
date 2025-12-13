# Jeeves Constitution

**Status:** Overview Document

---

## Overview

This document provides an overview of the Jeeves constitutional framework—a hierarchy of constitutions that govern the **Jeeves Code Analyser**, a three-component AI system for read-only code analysis.

> **Runtime Contract:** For the authoritative source of truth on capability integration with jeeves-core, see **[JEEVES_CORE_RUNTIME_CONTRACT.md](JEEVES_CORE_RUNTIME_CONTRACT.md)**.

**Note:** This is an overview document. The actual governing constitutions are in the component directories within the `jeeves-core/` submodule, following the dependency hierarchy.

> **Submodule Note:** Core packages are in the `jeeves-core/` git submodule. Initialize with: `git submodule update --init --recursive`

---

## Constitutional Hierarchy

The Jeeves system uses a decentralized model where each component's constitution extends its dependencies:

```
┌─────────────────────────────────────────────────────────┐
│ CommBus (FOUNDATION) - Go Implementation                │
│ jeeves-core/commbus/                                    │
│ • ZERO dependencies - foundation layer                  │
│ • Defines canonical protocols and messaging             │
│ • Used by all other components                          │
│ • Module: github.com/.../codeanalysis/commbus           │
└────────────────────┬────────────────────────────────────┘
                     │ extended by
                     ↓
┌─────────────────────────────────────────────────────────┐
│ Core Engine (BASE) - Go Implementation                  │
│ jeeves-core/coreengine/                                 │
│ • Depends on: CommBus only                              │
│ • Defines core principles (P1-P3)                       │
│ • Pure orchestration runtime                            │
│ • Module: github.com/.../codeanalysis/coreengine        │
└────────────────────┬────────────────────────────────────┘
                     │ extends
                     ↓
┌─────────────────────────────────────────────────────────┐
│ Avionics Constitution - Python                          │
│ jeeves-core/jeeves_avionics/CONSTITUTION.md             │
│ • Parent: Core Engine                                   │
│ • Inherits P1-P3 + adds infrastructure rules            │
│ • LLM, database, memory, gateway                        │
└────────────────────┬────────────────────────────────────┘
                     │ extends
                     ↓
┌─────────────────────────────────────────────────────────┐
│ Mission System Constitution - Python                    │
│ jeeves-core/jeeves_mission_system/CONSTITUTION.md       │
│ • Parent: Avionics Constitution                         │
│ • Inherits full dependency chain                        │
│ • 7-agent pipeline, tools, API                          │
└─────────────────────────────────────────────────────────┘
```

**Key principle:** Each constitution extends its dependencies, matching the code dependency hierarchy. CommBus and Core Engine are now **Go implementations** in the `jeeves-core/` submodule, providing the foundation layer with zero external dependencies.

---

## Why Four Layers?

The Jeeves system evolved into four layers for clear separation of concerns:

1. **Foundation Layer (CommBus)**
   - Zero dependencies - the true foundation
   - Canonical protocols used by all components
   - Messaging infrastructure (events, queries, commands)
   - Enables testability through dependency injection

2. **Core Runtime Stability**
   - Deterministic, minimal-dependency orchestration
   - Reusable across all verticals
   - No domain-specific logic
   - Pure abstractions and contracts only

3. **Infrastructure Flexibility**
   - Swappable external system integrations
   - Adapter pattern for all external dependencies
   - Replaceable without affecting core

4. **Vertical Isolation**
   - Independent domain implementations
   - Pluggable and composable
   - Never dependencies for core or infrastructure

### Dependency Matrix

```
                      ┌────────────────────────────────────────────────────────────────────────────┐
                      │                          CAN DEPEND ON...                                   │
                      ├───────────┬───────────┬───────────┬─────────────┬───────────────────────────┤
                      │ protocols │  shared   │ control_  │  avionics   │ mission_system            │
                      │           │           │  tower    │             │                           │
    ┌─────────────────┼───────────┼───────────┼───────────┼─────────────┼───────────────────────────┤
    │  protocols      │     ✓     │     ✗     │     ✗     │     ✗       │       ✗                   │
    ├─────────────────┼───────────┼───────────┼───────────┼─────────────┼───────────────────────────┤
    │  shared         │     ✓     │     ✓     │     ✗     │     ✗       │       ✗                   │
    ├─────────────────┼───────────┼───────────┼───────────┼─────────────┼───────────────────────────┤
    │  memory_module  │     ✓     │     ✓     │     ✗     │     ✗*      │       ✗                   │
    ├─────────────────┼───────────┼───────────┼───────────┼─────────────┼───────────────────────────┤
    │  control_tower  │     ✓     │     ✓     │     ✓     │     ✗       │       ✗                   │
    ├─────────────────┼───────────┼───────────┼───────────┼─────────────┼───────────────────────────┤
    │  avionics       │     ✓     │     ✓     │     ✓     │     ✓       │       ✗                   │
    ├─────────────────┼───────────┼───────────┼───────────┼─────────────┼───────────────────────────┤
    │  mission_system │     ✓     │     ✓     │     ✓     │     ✓       │       ✓                   │
    └─────────────────┴───────────┴───────────┴───────────┴─────────────┴───────────────────────────┘

    * memory_module uses avionics.database.factory ONLY for client creation

    Layer Stack (L0 = foundation):
    L0: jeeves_protocols (pure types, no dependencies)
    L0: jeeves_shared (logging, serialization, UUID - depends only on protocols)
    L1: jeeves_memory_module (persistence services)
    L2: jeeves_control_tower (orchestration kernel)
    L3: jeeves_avionics (infrastructure adapters)
    L4: jeeves_mission_system (application layer)
    L5: jeeves-capability-* (domain verticals)

    Amendment (2025-12): Added jeeves_shared at L0 for cross-cutting utilities
```

### Guarantees

1. **CommBus** remains zero-dependency foundation - never imports from other Jeeves packages
2. **Core Engine** remains deterministic, predictable, and formally analyzable
3. **Avionics** remains swappable without Core modifications
4. **Mission System** remains independent and pluggable
5. **No change may violate these boundaries without constitutional amendment**

---

## Component Constitutions

### 0. CommBus (Foundation) - Go

**Location:** `/commbus/` (Go package)

**Module:** `github.com/jeeves-cluster-organization/codeanalysis/commbus`

**Status:** Foundation — zero dependencies, used by all other components

**Language:** Go 1.21+

**Defines:**
- CommBus interface and InMemoryCommBus implementation
- Message, Query, Handler protocols
- RiskLevel enum (read_only, write, destructive)
- Middleware infrastructure
- Error types

**Key Files:**
- `bus.go` - InMemoryCommBus implementation
- `protocols.go` - Canonical protocol definitions
- `messages.go` - Message types
- `middleware.go` - Middleware infrastructure
- `errors.go` - Error definitions

**Dependencies:** None (self-standing foundation, only Go stdlib + uuid)

**Extends:** None

---

### 1. Core Engine (Base) - Go

**Location:** `/coreengine/` (Go package)

**Module:** `github.com/jeeves-cluster-organization/codeanalysis/coreengine`

**Status:** Base — all other constitutions build on this

**Language:** Go 1.21+

**Defines:**
- **Core Principles (P1-P3):** Accuracy First, Code Context Priority, Bounded Efficiency
- UnifiedAgent - single agent class driven by configuration
- GenericEnvelope - dynamic state container with outputs map
- UnifiedRuntime - pipeline orchestration engine
- PipelineConfig and AgentConfig structures
- ToolExecutor interface and StandardToolResult

**Key Packages:**
- `agents/` - UnifiedAgent, contracts, tool result normalization
- `config/` - PipelineConfig, AgentConfig, CoreConfig
- `envelope/` - GenericEnvelope, TerminalReason
- `runtime/` - UnifiedRuntime orchestration engine
- `tools/` - ToolExecutor, ToolDefinition

**Dependencies:** CommBus only (for RiskLevel)

**Extends:** CommBus

---

### 2. Avionics Constitution

**Location:** [jeeves_avionics/CONSTITUTION.md](jeeves_avionics/CONSTITUTION.md)

**Parent:** [Core Engine Constitution](jeeves_core_engine/CONSTITUTION.md)

**Defines:**
- Infrastructure adapter patterns
- LLM provider implementations (OpenAI, Anthropic, llamaserver, Azure)
- Database clients (PostgreSQL, pgvector)
- Memory services (L1-L4 layers)
- FastAPI gateway (HTTP/SSE endpoints)
- Settings and feature flag management

**Dependencies:** Core Engine

**Extends:** Core Engine Constitution (inherits P1-P3)

---

### 3. Mission System Constitution

**Location:** [jeeves_mission_system/CONSTITUTION.md](jeeves_mission_system/CONSTITUTION.md)

**Parent:** [Avionics Constitution](jeeves_avionics/CONSTITUTION.md)

**Defines:**
- 7-agent code analysis pipeline
- Tool implementations (read-only code analysis tools)
- LangGraph orchestration
- HTTP API server
- Evidence chain integrity rules
- Context bounds and thresholds

**Dependencies:** Avionics, Core Engine

**Extends:** Avionics Constitution (inherits full chain including P1-P3)

---

## Dependency Flow

### Code Dependencies
```
jeeves_mission_system  →  Application layer (Python)
        ↓ imports via jeeves_protocols
jeeves_avionics        →  Infrastructure layer (Python)
        ↓ imports via jeeves_protocols
coreengine/            →  Runtime layer (Go)
        ↓ imports
commbus/               →  Foundation layer (Go, zero dependencies)
```

### Go Module Structure
```
github.com/jeeves-cluster-organization/codeanalysis
├── commbus/           →  Foundation (no internal imports)
├── coreengine/        →  Runtime (imports commbus)
│   ├── agents/        →  imports commbus, config, envelope
│   ├── config/        →  no internal imports
│   ├── envelope/      →  no internal imports
│   ├── runtime/       →  imports agents, config, envelope
│   └── tools/         →  no internal imports
└── cmd/envelope/      →  CLI (imports coreengine/envelope)
```

### Python-Go Interop
```
jeeves_protocols/      →  Python type stubs + GoClient
        ↓ calls
cmd/envelope           →  Go CLI (JSON over stdin/stdout)
        ↓ uses
coreengine/envelope    →  GenericEnvelope operations
```

**The constitutional hierarchy mirrors the code dependency hierarchy.**

---

## Import Boundary Rules

The constitutional hierarchy enforces strict import boundaries:

```
RULE 0: CommBus is standalone (zero dependencies on other Jeeves packages)
RULE 1: Core Engine may depend on CommBus only (not avionics or mission system)
RULE 2: Avionics may depend on Core Engine and CommBus (not mission system)
RULE 3: Mission System may depend on Avionics, Core Engine, and CommBus
RULE 4: Capabilities access Core only through mission_system.contracts (not directly)
```

**Enforcement:**
- Static analysis: `jeeves_mission_system/scripts/check_import_boundaries.py`
- Contract tests: `jeeves_mission_system/tests/contract/test_import_boundaries.py`
- CI validation: Runs on every commit

---

## Repository Organization

```
/
├── go.mod                      # Go module: github.com/.../codeanalysis
├── go.sum                      # Go dependency lock
│
├── commbus/                    # ⭐ FOUNDATION LAYER (Go, ZERO dependencies)
│   ├── bus.go                  # InMemoryCommBus implementation
│   ├── protocols.go            # Canonical protocol definitions
│   ├── messages.go             # Message types
│   ├── middleware.go           # Middleware infrastructure
│   ├── errors.go               # Error definitions
│   └── bus_test.go             # Tests
│
├── coreengine/                 # BASE LAYER (Go, depends on commbus only)
│   ├── agents/                 # UnifiedAgent, contracts
│   │   ├── contracts.go        # ToolStatus, AgentOutcome, StandardToolResult
│   │   ├── unified.go          # UnifiedAgent implementation
│   │   └── contracts_test.go   # Tests
│   ├── config/                 # Pipeline and agent configuration
│   │   ├── core_config.go      # CoreConfig structure
│   │   ├── pipeline.go         # PipelineConfig, AgentConfig
│   │   └── core_config_test.go # Tests
│   ├── envelope/               # GenericEnvelope state container
│   │   ├── generic.go          # GenericEnvelope implementation
│   │   ├── enums.go            # TerminalReason enum
│   │   └── generic_test.go     # Tests
│   ├── runtime/                # Pipeline orchestration
│   │   └── runtime.go          # UnifiedRuntime engine
│   └── tools/                  # Tool execution
│       └── executor.go         # ToolExecutor, ToolDefinition
│
├── cmd/                        # Go CLI tools
│   └── envelope/               # Envelope CLI for Python-Go interop
│       └── main.go             # create, process, validate commands
│
├── jeeves_protocols/           # Python-Go bridge layer
│   └── ...                     # Type stubs, GoClient
│
├── jeeves_avionics/            # Infrastructure layer (Python)
│   ├── CONSTITUTION.md         # Extends Core Engine
│   ├── database/               # PostgreSQL/pgvector
│   ├── llm/                    # LLM providers
│   ├── memory/                 # L1-L4 memory services
│   └── gateway/                # FastAPI gateway
│
├── jeeves_mission_system/      # Application layer (Python)
│   ├── CONSTITUTION.md         # Extends Avionics Constitution
│   ├── verticals/              # Domain implementations
│   ├── orchestrator/           # LangGraph orchestration
│   ├── api/                    # HTTP API
│   └── tests/                  # Test suites
│
└── JEEVES_CORE_CONSTITUTION.md # THIS FILE (Overview Document)
```

**Note:** The ⭐ marks the foundation layer. CommBus and CoreEngine are now **Go implementations** at the repository root, following standard Go project layout with `go.mod` at root.

---

## Amendment Process

**Core Principles (P1-P3)** are defined in the Core Engine Constitution and are **immutable across all components**.

**To propose an amendment:**
1. Identify the appropriate constitution (component-level or cross-component)
2. Document proposed change in that constitution
3. Verify no contradiction with parent constitutions
4. Update version number
5. Add to version history

**Amendment authority:**
- **Core Engine changes** → Core Engine Constitution (affects all components)
- **Avionics-specific changes** → Avionics Constitution (affects Mission System)
- **Mission System changes** → Mission System Constitution (affects only Mission System)
- **Cross-component framework** → This overview document

---

## Removed Features

The following features are **permanently removed** (not deprecated):

- Task Management System
- Journal/Notes functionality
- Key-Value Store
- Kanban Board
- Redis-based state (PostgreSQL only)

Use git history to reference prior implementations.

---

## Quick Reference

**Where to find what:**

| Topic | Location |
|-------|----------|
| **Runtime Contract** | [JEEVES_CORE_RUNTIME_CONTRACT.md](JEEVES_CORE_RUNTIME_CONTRACT.md) |
| Canonical protocols | `/commbus/protocols.go` (Go) |
| Message types | `/commbus/messages.go` (Go) |
| CommBus interface | `/commbus/bus.go` (Go) |
| RiskLevel enum | `/commbus/protocols.go` (Go) |
| Core principles (P1-P3) | This document (Section: Component Constitutions) |
| UnifiedAgent | `/coreengine/agents/unified.go` (Go) |
| Agent contracts | `/coreengine/agents/contracts.go` (Go) |
| GenericEnvelope | `/coreengine/envelope/generic.go` (Go) |
| PipelineConfig | `/coreengine/config/pipeline.go` (Go) |
| UnifiedRuntime | `/coreengine/runtime/runtime.go` (Go) |
| LLM adapters | [Avionics](jeeves_avionics/CONSTITUTION.md) (Python) |
| Database clients | [Avionics](jeeves_avionics/CONSTITUTION.md) (Python) |
| Memory services | [Avionics](jeeves_avionics/CONSTITUTION.md) (Python) |
| Settings management | [Avionics](jeeves_avionics/CONSTITUTION.md) (Python) |
| 7-agent pipeline | [Mission System](jeeves_mission_system/CONSTITUTION.md) (Python) |
| Tools | [Mission System](jeeves_mission_system/CONSTITUTION.md) (Python) |
| Evidence chain | [Mission System](jeeves_mission_system/CONSTITUTION.md) (Python) |
| API endpoints | [Mission System](jeeves_mission_system/CONSTITUTION.md) (Python) |
| Python-Go interop | `/jeeves_protocols/` |

---

## Cross-References

- **Runtime Contract:** [JEEVES_CORE_RUNTIME_CONTRACT.md](JEEVES_CORE_RUNTIME_CONTRACT.md) - **SOURCE OF TRUTH** for capability integration
- **Architecture:** [NORTH_STAR_TRAJECTORY.md](NORTH_STAR_TRAJECTORY.md)
- **Repository Index:** [INDEX.md](../INDEX.md)
- **Capability Integration:** [CAPABILITY_INTEGRATION_GUIDE.md](CAPABILITY_INTEGRATION_GUIDE.md)
- **Audit Reports:**
  - [CENTRALIZATION_AUDIT_2025_12_10.md](CENTRALIZATION_AUDIT_2025_12_10.md) - Code pattern centralization opportunities
  - [POST_INTEGRATION_ARCHITECTURE_AUDIT.md](POST_INTEGRATION_ARCHITECTURE_AUDIT.md) - Control Tower integration audit
- **Go Packages (Foundation):**
  - `/commbus/` - Foundation layer (Go)
  - `/coreengine/` - Runtime layer (Go)
  - `/cmd/envelope/` - CLI for Python-Go interop
- **Python Constitutions:**
  - [Control Tower Constitution](../jeeves-core/jeeves_control_tower/CONSTITUTION.md)
  - [Avionics Constitution](../jeeves-core/jeeves_avionics/CONSTITUTION.md)
  - [Mission System Constitution](../jeeves-core/jeeves_mission_system/CONSTITUTION.md)

---

*This is an overview document. CommBus and CoreEngine are **Go implementations** at `/commbus/` and `/coreengine/`. Python layers (Avionics, Mission System) interact via `jeeves_protocols`. For the authoritative runtime contract, see [JEEVES_CORE_RUNTIME_CONTRACT.md](JEEVES_CORE_RUNTIME_CONTRACT.md).*
