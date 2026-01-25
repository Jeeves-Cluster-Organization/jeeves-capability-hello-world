# Code Analyser Tests

**Constitutional Layer**: Application (depends on Mission System only)

**Location**: `jeeves-capability-code-analyser/tests/`

---

## Overview

Code analyser tests validate the 7-agent code analysis implementation. Tests use dependency injection with mocked infrastructure for unit testing.

### Constitutional Compliance

Per App Layer Constitution:

- **MUST** import from `mission_system.contracts` (not core_engine or avionics directly)
- **MUST** use dependency injection (not service locator pattern)
- **MUST** create own test fixtures (not import from mission_system tests)

---

## Test Structure

```
tests/
├── conftest.py                    # App test configuration
├── fixtures/
│   ├── envelope.py                # Envelope fixtures (from contracts)
│   ├── agents.py                  # 7-agent fixtures
│   └── mocks/
│       ├── database.py            # MockDatabaseClient
│       ├── llm.py                 # MockLLMProvider
│       ├── tools.py               # MockToolRegistry, MockToolExecutor
│       └── events.py              # MockEventBus
└── unit/
    ├── agents/                    # Agent unit tests
    │   ├── test_perception.py     # PerceptionAgent
    │   ├── test_intent.py         # IntentAgent
    │   ├── test_planner.py        # PlannerAgent
    │   ├── test_traverser.py      # TraverserAgent
    │   ├── test_synthesizer.py   # SynthesizerAgent
    │   ├── test_critic.py         # CriticAgent
    │   └── test_integration.py    # IntegrationAgent
    └── tools/                     # Tool unit tests
        ├── test_code_tools.py     # Base code analysis tools
        ├── test_composite_tools.py  # Composite tools (locate, explore, etc.)
        ├── test_tool_registry.py  # Tool registration and lookup
        ├── test_resilient_ops.py  # Resilient tool operations
        └── test_robust_tool_base.py  # Base tool patterns
```

---

## Dependencies

### Lightweight (Unit Tests)

```bash
pip install pytest pytest-asyncio pydantic structlog
```

**Note**: All app tests use mocks - NO external services required for unit tests!

---

## Running Tests

### Quick Start

```bash
# Run all app layer tests
pytest jeeves-capability-code-analyser/tests -v

# Expected: All tests pass with mocked dependencies
```

### Specific Test Categories

```bash
# Agent tests only
pytest jeeves-capability-code-analyser/tests/unit/agents -v

# Tool tests only
pytest jeeves-capability-code-analyser/tests/unit/tools -v

# Single agent
pytest jeeves-capability-code-analyser/tests/unit/agents/test_planner.py -v
```

---

## Fixtures Provided

### Envelope Fixtures (from contracts)

- **`envelope_factory`** - Creates envelopes via `mission_system.contracts`
- **`sample_envelope`** - Basic envelope
- **`envelope_with_perception/intent/plan/execution/synthesizer/critic`** - Pre-populated states

**Example**:
```python
from mission_system.contracts import EnvelopeStage

def test_agent(envelope_with_intent):
    """Test agent with pre-populated envelope."""
    envelope = envelope_with_intent
    assert envelope.stage == EnvelopeStage.PLANNING
    assert envelope.intent is not None
```

### Service Mocks

- **`mock_llm_provider`** - MockLLMProvider with canned responses
- **`mock_tool_registry`** - MockToolRegistry tracking tool calls
- **`mock_tool_executor`** - MockToolExecutor for tool execution
- **`mock_db`** - MockDatabaseClient (no real database)
- **`mock_event_bus`** - MockEventBus capturing events

**Example**:
```python
def test_planner_with_mock_llm(mock_llm_provider, mock_tool_registry):
    """Test planner agent with mocked dependencies."""
    planner = PlannerAgent(
        llm=mock_llm_provider,
        tool_registry=mock_tool_registry,
        context_bounds=ContextBounds()
    )

    # Planner uses injected dependencies (no globals!)
    result = await planner.run(envelope, context)
    assert mock_llm_provider.call_count == 1
```

### Agent Fixtures

- **`perception_agent`** - PerceptionAgent instance
- **`intent_agent`** - IntentAgent with mocked LLM
- **`planner_agent`** - PlannerAgent with mocked LLM and tools
- **`traverser_agent`** - TraverserAgent with mocked tool executor
- **`synthesizer_agent`** - SynthesizerAgent with mocked LLM
- **`critic_agent`** - CriticAgent with mocked LLM
- **`integration_agent`** - IntegrationAgent

**Example**:
```python
async def test_intent_agent(intent_agent, sample_envelope):
    """Test intent agent with pre-configured mock."""
    result = await intent_agent.run(sample_envelope, context)
    assert result.status == Status.SUCCESS
    assert result.output.goals is not None
```

### Run Context Mock

- **`mock_run_context`** - Complete RunContext with all mocked services

**Example**:
```python
async def test_agent_with_context(planner_agent, envelope_with_intent, mock_run_context):
    """Test agent with full run context."""
    result = await planner_agent.run(envelope_with_intent, mock_run_context)
    assert result.output.steps is not None
```

---

## Test Coverage

### ✅ Agent Tests (7 agents)

**Files**: `unit/agents/test_*.py`

**What's Tested**:
- **PerceptionAgent**: Load session state, normalize input
- **IntentAgent**: Extract goals, detect clarification needs
- **PlannerAgent**: Create execution plan, select tools
- **TraverserAgent**: Execute tools, collect evidence
- **SynthesizerAgent**: Aggregate findings, structure analysis
- **CriticAgent**: Validate goal satisfaction, decide next action
- **IntegrationAgent**: Format response, persist state

**Example**:
```python
async def test_planner_creates_valid_plan(planner_agent, envelope_with_intent):
    """Planner creates plan with valid steps."""
    result = await planner_agent.run(envelope_with_intent, mock_context)

    assert result.status == Status.SUCCESS
    assert len(result.output.steps) > 0
    assert all(step.tool in VALID_TOOLS for step in result.output.steps)
```

### ✅ Tool Tests (5 files)

**Files**: `unit/tools/test_*.py`

**What's Tested**:
- **Base Tools**: `read_code`, `grep_search`, `find_symbol`, `git_status`
- **Composite Tools**: `locate`, `explore_symbol_usage`, `map_module`, `trace_entry_point`
- **Tool Registry**: Tool registration, lookup, risk level filtering
- **Resilient Operations**: Retry logic, graceful degradation
- **Tool Result Summarizer**: Evidence aggregation, citation preservation

**Example**:
```python
def test_locate_tool_fallback_strategy():
    """Locate tool tries multiple strategies."""
    # Strategy 1: Symbol index (fast)
    # Strategy 2: Grep search (medium)
    # Strategy 3: Semantic search (slow)

    result = await locate_tool.execute({"query": "MyClass"})
    assert result.attempt_history is not None
    assert len(result.attempt_history) <= 3  # Max 3 strategies
```

---

## Test Markers

App layer tests use minimal markers:

- **`@pytest.mark.unit`** - Unit tests with mocked dependencies (default)
- **`@pytest.mark.integration`** - Integration tests (if any)
- **`@pytest.mark.slow`** - Slow-running tests (> 5 seconds)

No heavy markers needed - all tests use mocks!

---

## Design Principles

### 1. Import from Contracts Only

**Constitutional Requirement**: App layer MUST NOT import from core_engine or avionics directly.

```python
# ✅ GOOD: Import from contracts
from mission_system.contracts import (
    CoreEnvelope,
    EnvelopeStage,
    create_envelope,
    LLMProviderProtocol,
)

# ❌ BAD: Import from core_engine directly
from jeeves_core_engine.agents.envelope import CoreEnvelope  # ❌ Violation

# ❌ BAD: Import from avionics directly
from avionics.llm import LLMClient  # ❌ Violation
```

### 2. Dependency Injection (Not Service Locator)

**Constitutional Requirement**: Agents receive dependencies via constructor.

```python
# ✅ GOOD: Dependency injection
class PlannerAgent:
    def __init__(
        self,
        llm: LLMProviderProtocol,
        tool_registry: ToolRegistryProtocol,
        context_bounds: ContextBounds,
    ):
        self.llm = llm  # Injected dependency
        self.tools = tool_registry
        self.bounds = context_bounds

# ❌ BAD: Service locator pattern
class PlannerAgent:
    def __init__(self, runtime: AgentRuntime):
        self.llm = runtime.get_llm()  # ❌ Agent reaches into runtime
```

### 3. Self-Contained Fixtures

**Constitutional Requirement**: App layer creates own fixtures (not import from mission_system tests).

```python
# ✅ GOOD: Import from own fixtures
from tests.fixtures.envelope import envelope_factory

# ❌ BAD: Import from mission_system tests
from mission_system.tests.fixtures.agents import envelope_factory  # ❌ Violation
```

---

## Development Workflow

### 1. Run Tests During Development

```bash
# Watch mode (re-run on file changes)
pytest-watch jeeves-capability-code-analyser/tests

# Single test (fast iteration)
pytest jeeves-capability-code-analyser/tests/unit/agents/test_planner.py::test_basic_plan -v
```

### 2. Add New Agent Test

**Template**:

```python
"""Unit tests for [Agent]Agent."""

import pytest
from mission_system.contracts import Status, EnvelopeStage


class TestAgent:
    """Tests for [Agent]Agent."""

    async def test_basic_case(self, agent_fixture, envelope_with_prev_stage):
        """Test basic agent functionality."""
        # Arrange
        envelope = envelope_with_prev_stage

        # Act
        result = await agent_fixture.run(envelope, mock_run_context)

        # Assert
        assert result.status == Status.SUCCESS
        assert result.output is not None
```

### 3. Add New Tool Test

**Template**:

```python
"""Unit tests for [tool] tool."""

import pytest
from mission_system.contracts import RiskLevel


class TestTool:
    """Tests for [tool] tool."""

    def test_basic_execution(self, mock_tool_executor):
        """Test basic tool execution."""
        # Arrange
        params = {"query": "test"}

        # Act
        result = mock_tool_executor.execute("tool_name", params)

        # Assert
        assert result.status == "success"
        assert result.data is not None
```

---

## Common Issues

### Issue 1: Import from core_engine in Tests

**Error**: `from jeeves_core_engine import ...` in test file

**Solution**: Import from contracts instead:

```python
# ❌ Before
from jeeves_core_engine.agents.envelope import CoreEnvelope

# ✅ After
from mission_system.contracts import CoreEnvelope
```

### Issue 2: ModuleNotFoundError for tools

**Error**: `ModuleNotFoundError: No module named 'tools'`

**Solution**: Set correct PYTHONPATH in conftest.py (already configured):

```python
# In tests/conftest.py
app_root = Path(__file__).parent.parent
sys.path.insert(0, str(app_root))
```

### Issue 3: Fixture Not Found

**Error**: `fixture 'envelope_factory' not found`

**Solution**: Ensure conftest.py imports fixtures:

```python
# In tests/conftest.py
from tests.fixtures.envelope import envelope_factory
```

---

## CI/CD Integration

### Fast CI Pipeline (< 5 seconds)

```yaml
# .github/workflows/test-app.yml
jobs:
  test-app:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - run: |
          pip install pytest pytest-asyncio pydantic structlog
          pytest jeeves-capability-code-analyser/tests -v
```

**Expected**: All tests pass (no external deps needed)

---

## Related Documentation

- **Mission System Contracts**: [../../mission_system/contracts.py](../../mission_system/contracts.py)
- **Mission System Tests**: [../../mission_system/tests/README.md](../../mission_system/tests/README.md)
- **Protocols Tests**: [../../protocols/tests/](../../protocols/tests/)

---

**Last Updated**: 2025-12-06
**Test Files**: 13
**Pass Rate**: 100% (with mocks)
**Avg Runtime**: < 5 seconds
**External Dependencies**: None (all mocked)
