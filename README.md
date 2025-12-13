# Jeeves Code Analyser

**A multi-agent AI system for read-only code analysis with citation-backed responses**

## Overview

Jeeves Code Analyser is a production-ready system that explores codebases, parses code symbols, traces dependencies, and explains code with accurate `[file:line]` citations. The system uses a 7-agent pipeline to process user queries and provide grounded responses based on actual source code.

**Tech Stack:** Go 1.21+ (commbus, envelope CLI) + Python 3.11+ (application layer)

### Core Capabilities

1. **File Navigation** - List, read, and search files across codebases
2. **Code Parsing** - Extract functions, classes, and symbols using language-specific parsers
3. **Dependency Tracking** - Map and query import relationships via symbol explorer
4. **Citation-Based Responses** - Every claim includes `[file:line]` references
5. **Memory Services** - L1-L7 memory layers for episodic, semantic, graph, and working memory

### Design Principles

```
1. ACCURACY          (never hallucinate, always cite sources)
2. CODE CONTEXT      (understand fully before claiming)
3. SPEED             (efficient exploration within bounds)
```

**Hierarchy:** P1 > P2 > P3 (when principles conflict)

## Architecture

### 7-Agent Pipeline

```
User Query
    ↓
PERCEPTION    → Normalize query, load session context
    ↓
INTENT        → Classify: trace_flow / find_definition / explain / search
    ↓
PLANNER       → Plan traversal steps, respect context bounds
    ↓ (loop until Critic approves)
TRAVERSER     → Execute read-only code operations
    ↓
SYNTHESIZER   → Build structured understanding from results
    ↓
CRITIC        → Validate answer against actual code (anti-hallucination)
    ↓ (if APPROVED)
INTEGRATION   → Build response with [file:line] citations
    ↓
Response with citations
```

### Hybrid Go-Python Architecture

The system uses a hybrid architecture with Go for messaging infrastructure and Python for application logic, with **Control Tower** as the central orchestration kernel:

```
┌─────────────────────────────────────────────────────────────────┐
│                          GO CORE                                 │
├─────────────────────────────────────────────────────────────────┤
│  commbus/              →  Go messaging bus & protocols          │
│  coreengine/           →  Go envelope types & agent contracts   │
│  cmd/envelope/         →  Go CLI for envelope operations        │
└─────────────────────────────────────────────────────────────────┘
                              ↑
                        JSON/stdio bridge
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  PYTHON FOUNDATION (L0)                          │
├─────────────────────────────────────────────────────────────────┤
│  jeeves_protocols/         →  Type bridge to Go (protocols, enums)│
│  jeeves_shared/            →  Shared utilities (logging, UUID)   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   CONTROL TOWER (Kernel)                         │
├─────────────────────────────────────────────────────────────────┤
│  jeeves_control_tower/     →  LifecycleManager, ResourceTracker  │
│                            →  CommBusCoordinator, EventAggregator│
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    Dispatches to services
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                       PYTHON LAYERS                              │
├─────────────────────────────────────────────────────────────────┤
│  jeeves_avionics/          →  Infrastructure (DB, LLM, gateway) │
│  jeeves_memory_module/     →  Memory services (L1-L7)           │
│  jeeves_mission_system/    →  Application (orchestration, API)  │
│  jeeves-capability-*/      →  Domain capabilities (code analysis)│
└─────────────────────────────────────────────────────────────────┘
```

**Dependency Flow:** `capability → mission_system → avionics → control_tower → protocols/shared → Go core`

**Import Boundary Rules:**
- Go Core (commbus, coreengine): Self-contained, no Python dependencies
- Control Tower: Only imports from jeeves_protocols and jeeves_shared
- Avionics: Infrastructure layer, bridges to Go via subprocess/JSON
- Memory Module: Imports from protocols, shared, and avionics.database.factory only
- Mission System: May depend on all lower layers
- Capabilities: Must use jeeves_protocols types (not direct imports from lower layers)

See [JEEVES_CORE_CONSTITUTION.md](JEEVES_CORE_CONSTITUTION.md) for the complete governance framework.

## Quick Start

### Prerequisites

- Docker and Docker Compose (recommended)
- Go 1.21+ (for Go core components)
- Python 3.11+ (for application layer)
- PostgreSQL 15+ (included in Docker setup)

### Docker Deployment (Recommended)

```bash
# 1. Clone the repository
git clone <repository-url>
cd codeanalysis-7agent

# 2. Build with cache-busting (ensures latest code)
# PowerShell: $env:CODE_VERSION = $(git rev-parse --short HEAD)
# Bash:       export CODE_VERSION=$(git rev-parse --short HEAD)
docker compose -f docker/docker-compose.yml build

# 3. Start all services
docker compose -f docker/docker-compose.yml up -d

# 4. Check health
curl http://localhost:8001/health

# 5. Access the system
# Gateway UI:   http://localhost:8001/chat
# Gateway API:  http://localhost:8001/docs
# gRPC Service: localhost:50051
```

> **Note:** The `CODE_VERSION` build arg ensures Docker invalidates its cache when code changes. Without it, Docker may serve stale code even with `--no-cache`.

### Development Setup

```bash
# 1. Start PostgreSQL
docker compose -f docker/docker-compose.yml up -d postgres

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements/all.txt

# 3. Initialize database
python jeeves_mission_system/scripts/database/init.py

# 4. Start orchestrator service (gRPC)
python jeeves_mission_system/scripts/run/orchestrator.py

# 5. (Optional) Start gateway service (HTTP/REST)
python jeeves_mission_system/scripts/run/gateway.py
```

## Testing

### PowerShell (Windows - Recommended)

```powershell
# Quick CI tests (< 10s, no external dependencies)
.\test.ps1 ci

# Run specific layer
.\test.ps1 core       # Core engine (128 tests, < 1s)
.\test.ps1 avionics   # Avionics (33 tests, < 2s)
.\test.ps1 memory     # Memory module (< 5s)
.\test.ps1 app        # Capability layer (< 3s)

# Full flow testing (all tiers)
docker compose -f docker/docker-compose.yml up -d
.\test.ps1 full

# Show all available commands
.\test.ps1 help
```

### Bash (Linux/Mac)

```bash
# Unit tests (fast, no external dependencies)
make test-tier1

# Integration tests (requires PostgreSQL)
docker compose -f docker/docker-compose.yml up -d postgres
make test-tier2

# Full test suite
docker compose -f docker/docker-compose.yml up -d
make test-nightly
```

### Go Tests

```bash
# Run all Go tests
go test ./...

# Run Go tests with verbose output
go test -v ./commbus/... ./coreengine/...

# Run specific package
go test -v ./coreengine/envelope/...

# Run with coverage
go test -cover ./...
```

### Direct pytest Commands (Python)

```bash
# Memory module
pytest jeeves_memory_module/tests -v

# Mission system
pytest jeeves_mission_system/tests/unit/ -v

# Avionics
pytest jeeves_avionics/tests -v
```

**Test Organization:**
- `tests/unit/` - Unit tests (no I/O, mocked dependencies)
- `tests/integration/` - Integration tests (database, LLM, external services)
- `tests/contract/` - Contract tests (API compliance)
- `tests/e2e/` - End-to-end tests (full pipeline)

See [POWERSHELL_TESTING.md](POWERSHELL_TESTING.md) for comprehensive PowerShell testing guide.

## Project Structure

```
codeanalysis-7agent/
│
│ ═══════════════════ GO CORE (root level) ═══════════════════════
│
├── go.mod                     # Go module: github.com/jeeves-cluster-organization/codeanalysis
├── go.sum                     # Go dependency checksums
├── commbus/                   # Go messaging bus (foundation)
│   ├── bus.go                 # CommBus implementation
│   ├── protocols.go           # Protocol definitions
│   ├── messages.go            # Message types
│   ├── middleware.go          # Middleware chain
│   └── errors.go              # Error types
│
├── coreengine/                # Go core runtime structures
│   ├── agents/                # Agent contracts
│   ├── config/                # Core configuration
│   ├── envelope/              # GenericEnvelope implementation
│   ├── runtime/               # Runtime structures
│   └── tools/                 # Tool contracts
│
├── cmd/                       # Go CLI entry points
│   └── envelope/              # Envelope CLI (create, validate, etc.)
│
│ ═══════════════════ PYTHON FOUNDATION (L0) ═════════════════════
│
├── jeeves_protocols/          # Python bridge to Go (v3.0.0)
│   ├── core.py                # Core enums (RiskLevel, ToolCategory, etc.)
│   ├── protocols.py           # Protocol definitions (LLM, DB, Memory, etc.)
│   ├── interrupts.py          # InterruptKind, FlowInterrupt, RateLimiting
│   ├── envelope.py            # GenericEnvelope, ProcessingRecord
│   ├── config.py              # AgentConfig, PipelineConfig, CoreConfig
│   ├── memory.py              # WorkingMemory, FocusState, EntityRef
│   ├── agents.py              # UnifiedAgent, UnifiedRuntime stubs
│   ├── capability.py          # CapabilityResourceRegistry
│   ├── client.py              # GoClient for subprocess calls
│   └── utils.py               # JSONRepairKit, string utilities
│
├── jeeves_shared/             # Shared utilities (L0)
│   ├── logging/               # JeevesLogger, configure_logging
│   ├── serialization.py       # to_json, from_json, utc_now
│   ├── uuid_utils.py          # uuid_str, uuid_read
│   └── testing.py             # Test utilities
│
│ ═══════════════════ PYTHON LAYERS ══════════════════════════════
│
├── jeeves_control_tower/      # Kernel layer (v1.0.0)
│   ├── kernel.py              # ControlTower main class
│   ├── lifecycle/manager.py   # LifecycleManager (process scheduling)
│   ├── resources/tracker.py   # ResourceTracker (quota enforcement)
│   ├── resources/rate_limiter.py # Rate limiting
│   ├── ipc/coordinator.py     # CommBusCoordinator (IPC)
│   ├── events/aggregator.py   # EventAggregator (interrupt handling)
│   ├── services/interrupt_service.py # Interrupt handling
│   ├── types.py               # ProcessState, ResourceQuota, etc.
│   └── protocols.py           # Kernel protocols
│
├── jeeves_avionics/           # Infrastructure layer
│   ├── settings.py            # Settings, get_settings
│   ├── feature_flags.py       # FeatureFlags
│   ├── thresholds.py          # CRITIC_APPROVAL_THRESHOLD, etc.
│   ├── context.py             # AppContext (DI container)
│   ├── context_bounds.py      # ContextBounds
│   ├── wiring.py              # ToolExecutor, create_llm_provider_factory
│   ├── runtime.py             # AgentRuntime, TimingContext
│   ├── capability_registry.py # CapabilityLLMConfigRegistry
│   ├── database/              # PostgreSQL/Redis clients, repositories
│   ├── llm/                   # LLM providers (openai, anthropic, azure, llamaserver)
│   ├── gateway/               # FastAPI gateway, SSE, WebSocket
│   ├── distributed/           # RedisDistributedBus
│   ├── checkpoint/            # PostgresCheckpointAdapter
│   ├── interop/               # Go bridge (subprocess wrapper)
│   ├── logging/               # Logging adapters
│   ├── observability/         # OpenTelemetry tracing
│   └── tools/                 # Tool executor core
│
├── jeeves_memory_module/      # Memory services (v1.0.0)
│   ├── manager.py             # MemoryManager coordinator
│   ├── intent_classifier.py   # IntentClassifier
│   ├── services/              # Memory layer implementations
│   │   ├── session_state_service.py  # L4 working memory
│   │   ├── event_emitter.py          # L2 domain events
│   │   ├── embedding_service.py      # L3 semantic search
│   │   ├── trace_recorder.py         # Agent traces
│   │   ├── graph_service.py          # L5 entity relationships
│   │   ├── tool_health_service.py    # L7 tool governance
│   │   └── ...                       # Other services
│   ├── repositories/          # Data access layer
│   │   ├── session_state_repository.py
│   │   ├── event_repository.py
│   │   ├── trace_repository.py
│   │   ├── graph_repository.py
│   │   └── ...
│   └── adapters/              # SQLAdapter, etc.
│
├── jeeves_mission_system/     # Application layer (v1.0.0)
│   ├── orchestrator/          # Flow orchestration
│   │   ├── flow_service.py    # FlowService
│   │   ├── vertical_service.py # VerticalService
│   │   ├── governance_service.py
│   │   └── events.py          # Event types
│   ├── api/                   # HTTP API (chat, health, governance)
│   ├── services/              # ChatService, WorkerCoordinator
│   ├── verticals/             # Vertical registry
│   ├── contracts/             # Contract definitions
│   ├── prompts/               # Core prompts
│   └── scripts/               # Operational scripts
│
├── jeeves-capability-code-analyser/  # Code analysis capability (v1.0.0)
│   ├── registration.py        # register_capability(), CAPABILITY_ID
│   ├── pipeline_config.py     # 7-agent pipeline configuration
│   ├── server.py              # gRPC capability server
│   ├── agents/                # Agent implementations
│   │   ├── context_builder.py # Context building
│   │   ├── summarizer.py      # Tool result summarization
│   │   ├── prompt_mapping.py  # Prompt mapping
│   │   └── protocols.py       # Agent protocols
│   ├── orchestration/         # LangGraph nodes and service
│   ├── tools/                 # Code analysis tools
│   │   ├── file_navigator.py  # File navigation
│   │   ├── code_parser.py     # Code parsing
│   │   ├── symbol_explorer.py # Symbol exploration
│   │   ├── flow_tracer.py     # Flow tracing
│   │   └── base/              # Base tool implementations
│   ├── config/                # Language config, tool access, modes
│   ├── prompts/               # Code analysis prompts
│   └── contracts/             # Schemas, validation
│
│ ═══════════════════ SUPPORTING FILES ═══════════════════════════
│
├── docker/                    # Docker configuration
│   ├── Dockerfile             # Multi-stage build (Go + Python)
│   └── docker-compose.yml     # Container orchestration
│
├── requirements/              # Python dependencies (all.txt, base.txt)
├── docs/                      # Documentation
├── app_bootstrap.py           # Vertical registration
├── conftest.py                # Pytest configuration
└── Makefile                   # Build automation
```

## Documentation

### Core Documents

| Document | Purpose |
|----------|---------|
| [INDEX.md](INDEX.md) | **START HERE** - Complete repository navigation |
| [docs/JEEVES_CORE_RUNTIME_CONTRACT.md](docs/JEEVES_CORE_RUNTIME_CONTRACT.md) | **SOURCE OF TRUTH** - Runtime contract for capabilities |
| [docs/CONSTITUTION.md](docs/CONSTITUTION.md) | Governance framework and constitutional hierarchy |
| [docs/NORTH_STAR_TRAJECTORY.md](docs/NORTH_STAR_TRAJECTORY.md) | Target architecture and roadmap |

### Component Documentation

Each component has its own INDEX.md or documentation:

- `commbus/` - Go CommBus foundation layer (messaging bus, protocols)
- `coreengine/` - Go Core Engine (runtime, envelope, agents)
- [jeeves_control_tower/CONSTITUTION.md](jeeves_control_tower/CONSTITUTION.md) - Control Tower (kernel layer)
- [jeeves_avionics/INDEX.md](jeeves_avionics/INDEX.md) - Infrastructure layer
- [jeeves_mission_system/INDEX.md](jeeves_mission_system/INDEX.md) - Application layer
- [jeeves_mission_system/tests/README.md](jeeves_mission_system/tests/README.md) - Test suite

### Audit Reports

- [CENTRALIZATION_AUDIT_2025_12_10.md](CENTRALIZATION_AUDIT_2025_12_10.md) - Code pattern centralization opportunities
- [docs/POST_INTEGRATION_ARCHITECTURE_AUDIT.md](docs/POST_INTEGRATION_ARCHITECTURE_AUDIT.md) - Control Tower integration audit

## Configuration

### Context Bounds

Critical limits for analyzing large repositories:

```python
max_tree_depth: 10           # Prevent runaway exploration
max_file_slice_tokens: 4000  # Context window management
max_grep_results: 50         # Limit search volume
max_files_per_query: 10      # Bound per-query scope
max_total_code_tokens: 25000 # Total budget per query
```

### Environment Variables

Key configuration options (see `.env` for full list):

```bash
# LLM Configuration
LLM_PROVIDER=llamaserver          # llamaserver, openai, anthropic, azure
LLAMASERVER_HOST=http://localhost:8080
DEFAULT_MODEL=qwen2.5-3b-instruct-q4_k_m

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=assistant
POSTGRES_USER=assistant
POSTGRES_PASSWORD=dev_password_change_in_production

# Services
API_PORT=8000                     # Gateway HTTP port
ORCHESTRATOR_PORT=50051           # gRPC port
LOG_LEVEL=INFO
LOG_FORMAT=json
```

## Deployment

### Docker Compose Profiles

```bash
# Production (API, gateway, postgres, LLM server)
docker compose -f docker/docker-compose.yml --profile prod up -d

# Development (all services)
docker compose -f docker/docker-compose.yml up -d

# Testing (all services + test runner)
docker compose -f docker/docker-compose.yml --profile test run --rm test pytest -v

# Minimal (core services only, no gateway)
docker compose -f docker/docker-compose.yml --profile minimal up -d
```

### Deployment Script

```bash
# Build and deploy production
python jeeves_mission_system/scripts/deployment/deploy.py --profile prod --build

# Run tests
python jeeves_mission_system/scripts/deployment/deploy.py --profile test

# Test gateway
python jeeves_mission_system/scripts/deployment/deploy.py --test-gateway
```

## API Access

### HTTP/REST Gateway

```bash
# Chat interface
http://localhost:8001/chat

# API documentation (OpenAPI/Swagger)
http://localhost:8001/docs

# Health check
curl http://localhost:8001/health

# Query endpoint
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What does the main function do?", "user_id": "user1", "session_id": "session1"}'
```

### gRPC Service

```bash
# Direct gRPC access
grpcurl -plaintext localhost:50051 list
grpcurl -plaintext localhost:50051 jeeves.Orchestrator/ProcessQuery
```

## Contributing

### Code Quality

```bash
# Run linters
ruff check .
mypy .

# Format code
ruff format .

# Run all quality checks
make quality
```

### Import Boundaries

The system enforces strict import boundaries between layers. See **[JEEVES_CORE_RUNTIME_CONTRACT.md](docs/JEEVES_CORE_RUNTIME_CONTRACT.md)** for the authoritative import rules.

```bash
# Check Python import boundaries
python jeeves_mission_system/scripts/check_import_boundaries.py

# Verify Go builds cleanly (Go dependencies self-contained)
go build ./...
```

**Rules:**
1. Go Core (commbus, coreengine): Self-contained, no external dependencies
2. Foundation (jeeves_protocols, jeeves_shared): L0 layer, no higher-layer imports
3. Control Tower: Only imports from jeeves_protocols and jeeves_shared (kernel isolation)
4. Memory Module: Imports from protocols, shared, and avionics.database.factory only
5. Avionics: Infrastructure layer; bridges to Go via subprocess/JSON
6. Mission System: May depend on all lower layers (orchestration, API)
7. Capabilities: Must use jeeves_protocols types; register via CapabilityResourceRegistry

## License

See repository root for license information.

## Support

For issues, questions, or contributions:
- GitHub Issues: <repository-url>/issues
- Documentation: [INDEX.md](INDEX.md)
- Runtime Contract: [docs/JEEVES_CORE_RUNTIME_CONTRACT.md](docs/JEEVES_CORE_RUNTIME_CONTRACT.md)
- Constitution: [docs/CONSTITUTION.md](docs/CONSTITUTION.md)
