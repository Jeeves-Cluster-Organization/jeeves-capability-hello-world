# Jeeves Code Analysis Capability

**A 7-agent pipeline for read-only code analysis with citation-backed responses**

## Overview

This repository contains `jeeves-capability-code-analyser`, a domain capability that implements a 7-agent pipeline for analyzing codebases. It is designed to be used with the Jeeves core infrastructure (via git submodule).

**Key Features:**
- 7-agent pipeline (Perception, Intent, Planner, Traverser, Synthesizer, Critic, Integration)
- Citation-backed responses with `[file:line]` references
- Read-only code analysis tools (no write operations)
- Configuration-driven agent architecture (no concrete agent classes)

## Architecture

### Pipeline Flow

```
User Query
    |
PERCEPTION    -> Normalize query, load session context
    |
INTENT        -> Classify: trace_flow / find_definition / explain / search
    |
PLANNER       -> Plan traversal steps, respect context bounds
    | (loop until Critic approves)
TRAVERSER     -> Execute read-only code operations
    |
SYNTHESIZER   -> Build structured understanding from results
    |
CRITIC        -> Validate answer against actual code (anti-hallucination)
    | (if APPROVED)
INTEGRATION   -> Build response with [file:line] citations
    |
Response with citations
```

### Project Structure

```
jeeves-capability-code-analysis/
|
+-- jeeves-capability-code-analyser/    # Main capability package
|   +-- __init__.py                     # Package init (register_capability)
|   +-- registration.py                 # Capability resource registration
|   +-- pipeline_config.py              # 7-agent pipeline configuration
|   +-- server.py                       # gRPC capability server
|   +-- CONSTITUTION.md                 # Capability layer constitution
|   |
|   +-- agents/                         # Agent helpers
|   |   +-- context_builder.py          # Context building for agents
|   |   +-- summarizer.py               # Tool result summarization
|   |   +-- prompt_mapping.py           # Prompt mapping utilities
|   |   +-- protocols.py                # Agent protocols/interfaces
|   |
|   +-- tools/                          # Code analysis tools
|   |   +-- __init__.py                 # Tool initialization
|   |   +-- registration.py             # Tool registration system
|   |   +-- unified_analyzer.py         # Primary analyzer tool
|   |   +-- code_parser.py              # Code parsing utilities
|   |   +-- file_navigator.py           # File system navigation
|   |   +-- module_mapper.py            # Module dependency mapping
|   |   +-- flow_tracer.py              # Control flow tracing
|   |   +-- symbol_explorer.py          # Symbol resolution
|   |   +-- git_historian.py            # Git history analysis
|   |   +-- safe_locator.py             # Safe file locator
|   |   +-- base/                       # Base tool implementations
|   |       +-- code_tools.py           # Core code analysis
|   |       +-- git_tools.py            # Git operations
|   |       +-- index_tools.py          # Symbol indexing
|   |       +-- resilient_ops.py        # Retry logic
|   |       +-- semantic_tools.py       # Semantic search
|   |       +-- session_tools.py        # Session management
|   |       +-- citation_validator.py   # Citation validation
|   |       +-- path_helpers.py         # Path utilities
|   |
|   +-- config/                         # Domain configuration
|   |   +-- language_config.py          # Language-specific settings
|   |   +-- tool_profiles.py            # Tool profile definitions
|   |   +-- tool_access.py              # Tool access control
|   |   +-- deployment.py               # Deployment configuration
|   |   +-- modes.py                    # Operational modes
|   |   +-- identity.py                 # Product identity
|   |   +-- llm_config.py               # LLM provider settings
|   |
|   +-- orchestration/                  # LangGraph workflow
|   |   +-- service.py                  # CodeAnalysisService
|   |   +-- servicer.py                 # gRPC servicer
|   |   +-- wiring.py                   # Dependency wiring
|   |   +-- types.py                    # Type definitions
|   |
|   +-- contracts/                      # Data contracts
|   |   +-- schemas.py                  # Data schemas
|   |   +-- validation.py               # Input validation
|   |   +-- registry.py                 # Contract registry
|   |
|   +-- models/                         # Domain models
|   |   +-- traversal_state.py          # Traversal state tracking
|   |   +-- types.py                    # Type definitions
|   |
|   +-- prompts/                        # LLM prompts
|   |   +-- code_analysis.py            # Code analysis prompts
|   |
|   +-- tests/                          # Test suite
|       +-- unit/                       # Unit tests
|       +-- fixtures/                   # Test fixtures and mocks
|
+-- tests/                              # Integration/deployment tests
|   +-- integration/                    # Service integration tests
|   +-- deployment/                     # Docker infrastructure tests
|   +-- ui_ux/                          # API endpoint tests
|
+-- frontend/                           # Web UI assets (capability-owned)
|   +-- static/
|   |   +-- js/                         # JavaScript modules
|   |   |   +-- config.js               # API & WebSocket configuration
|   |   |   +-- chat.js                 # Chat interface logic
|   |   |   +-- shared.js               # Shared utilities
|   |   |   +-- governance.js           # Governance dashboard
|   |   +-- css/                        # Stylesheets
|   |       +-- chat.css
|   |       +-- governance.css
|   |       +-- shared.css
|   +-- templates/                      # Jinja2 HTML templates
|       +-- base.html                   # Base template with navigation
|       +-- chat.html                   # Code analysis chat UI
|       +-- governance.html             # Governance dashboard
|
+-- docs/                               # Documentation
+-- docker/                             # Docker configuration
+-- requirements/                       # Python dependencies
+-- scripts/                            # Utility scripts
+-- jeeves-core/                        # Core infrastructure (git submodule)
```

## Dependencies

This capability depends on the `jeeves-core` submodule which provides:
- `jeeves_protocols` - Protocol definitions and type bridge
- `jeeves_mission_system` - Orchestration primitives and contracts
- `jeeves_avionics` - Infrastructure adapters (LLM, database, gateway)
- `jeeves_control_tower` - Kernel layer (lifecycle, resources)
- `jeeves_shared` - Shared utilities (logging, serialization)

### Initializing the Submodule

```bash
git submodule update --init --recursive
```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose (for full deployment)
- PostgreSQL 15+ (included in Docker setup)

### Development Setup

```bash
# 1. Clone and initialize submodule
git clone <repository-url>
cd jeeves-capability-code-analysis
git submodule update --init --recursive

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements/all.txt

# 3. Run tests
pytest jeeves-capability-code-analyser/tests -v
```

### Docker Deployment

```bash
# Build and start all services
docker compose -f docker/docker-compose.yml up -d

# Check health
curl http://localhost:8001/health
```

## Testing

### Run Unit Tests

```bash
# All capability tests
pytest jeeves-capability-code-analyser/tests -v

# Specific test file
pytest jeeves-capability-code-analyser/tests/unit/tools/test_code_tools.py -v

# With markers
pytest jeeves-capability-code-analyser/tests -v -m unit
```

### Test Markers

- `unit` - Unit tests with mocked dependencies
- `integration` - Integration tests with real services
- `slow` - Slow-running tests

## Exposed Tools

The capability exposes these tools to agents:

| Tool | Description |
|------|-------------|
| `search_code` | Primary tool - searches for code, never assumes paths exist |
| `read_code` | Direct file reading with retry logic |
| `find_related` | Semantic search for related files |
| `git_status` | Current repository state |
| `list_tools` | Tool discovery |

Internal tools (used by `search_code`):
- `locate` - Symbol location via index/grep/semantic
- `explore_symbol_usage` - Symbol usage analysis
- `map_module` - Module dependency mapping
- `trace_entry_point` - Control flow tracing
- `explain_code_history` - Git history explanation

## Core Principles

**P1: Accuracy First** - Never hallucinate code. Every claim requires `[file:line]` citation.

**P2: Code Context Priority** - Understand fully before claiming.

**P3: Bounded Efficiency** - Be efficient within limits.

**Hierarchy:** P1 > P2 > P3 (when principles conflict)

## Configuration

### Context Bounds

Limits for analyzing large repositories:

```python
max_tree_depth: 10           # Prevent runaway exploration
max_file_slice_tokens: 4000  # Context window management
max_grep_results: 50         # Limit search volume
max_files_per_query: 10      # Bound per-query scope
max_total_code_tokens: 25000 # Total budget per query
```

### Environment Variables

Key configuration (see `.env` for full list):

```bash
# LLM Configuration
LLM_PROVIDER=llamaserver
LLAMASERVER_HOST=http://localhost:8080
DEFAULT_MODEL=qwen2.5-3b-instruct-q4_k_m

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=assistant

# Services
API_PORT=8000
ORCHESTRATOR_PORT=50051
```

## Capability Registration

At application startup, register the capability:

```python
from jeeves_capability_code_analyser import register_capability

# Call before infrastructure initialization
register_capability()
```

This registers:
- Database schemas
- Gateway mode configuration
- Service configuration for Control Tower
- Orchestrator factory
- Tools initializer
- Agent definitions
- Prompts and contracts

## License

See LICENSE.txt for license information.
