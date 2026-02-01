# Jeeves Capability Constitution

## 0) Purpose

A **Jeeves Capability** is a domain-specific vertical that provides specialized functionality through a pipeline of agents. Capabilities own their domain logic, prompts, tools, and LLM configuration policy while delegating infrastructure concerns to shared substrates.

This constitution defines the contract between capabilities and the platform layers they depend on.

## 1) Capability Ownership

### A Capability MUST Own

| Concern | Description |
|---------|-------------|
| **Domain Logic** | Business rules specific to the capability's purpose |
| **Agent Definitions** | Agent roles, responsibilities, and transitions |
| **Prompts** | LLM prompts tailored to the domain |
| **Tools** | Domain-specific tool implementations |
| **LLM Configuration Policy** | Which model/provider to use for which agent/task |
| **Response Formatting** | How to present results to users |
| **Validation Rules** | Domain-specific input/output validation |

### A Capability MUST NOT Own

| Concern | Belongs To |
|---------|------------|
| LLM wire protocol (HTTP, SSE, JSON) | LiteLLM / jeeves_infra LLM Providers |
| Provider-specific API handling | LiteLLM |
| Backend-specific payload formatting | LiteLLM |
| Mission orchestration (checkpointing, recovery) | Mission System |
| Tool execution framework | jeeves_infra |
| Database schemas (sessions, memory) | jeeves_infra |
| gRPC service scaffolding | Mission System |

## 2) Layer Dependencies

```
+-------------------------------------------------------------+
|                      Capability                              |
|  +-----------------------------------------------------+    |
|  |  agents/ prompts/ tools/ config/ orchestration/     |    |
|  +------------------------+----------------------------+    |
|                           |                                  |
|         +-----------------+----------------+                 |
|         |                                  |                 |
|         v                                  v                 |
|  +-------------+    +-------------------------------+        |
|  | LLM Factory |    |       Mission System API      |        |
|  | (adapters)  |    |  (adapters, contracts, api)   |        |
|  +------+------+    +---------------+---------------+        |
+---------+---------------------------+------------------------+
          |                           |
          v                           v
   +-------------+    +-------------------------------+
   |   LiteLLM   |    |       Mission System          |
   | (100+ APIs) |    |      (orchestration)          |
   +-------------+    +---------------+---------------+
                                      |
                                      v
                           +-------------------+
                           |   jeeves_infra    |
                           | (infra/tools/llm) |
                           +---------+---------+
                                     |
                                     v
                           +-------------------+
                           |    jeeves-core    |
                           |   (contracts)     |
                           +-------------------+
```

### Import Rules

```python
# Capability CAN import from:
from mission_system.adapters import (
    create_llm_provider_factory,
    create_tool_executor,
    get_settings,
    create_database_client,
)
from mission_system.contracts import PersistenceProtocol
from mission_system.contracts_core import ContextBounds

# Capability MUST NOT import from:
# - jeeves_infra directly (go through mission_system.adapters)
# - jeeves_core (go through mission_system.contracts)

# Capability MUST NOT be imported by:
# - mission_system (no capability imports)
# - jeeves-core (no capability imports)
# - other capabilities (no cross-capability imports)
```

### Why No Direct jeeves_infra Imports?

Mission System provides **adapters** that wrap jeeves_infra functionality:
- `mission_system.adapters.create_database_client` -> wraps jeeves_infra DB
- `mission_system.adapters.create_tool_executor` -> wraps jeeves_infra tools
- `mission_system.adapters.create_llm_provider_factory` -> wraps jeeves_infra LLM

This ensures:
1. Mission System can swap implementations without breaking capabilities
2. Capabilities don't couple to jeeves_infra internals
3. Testing is easier (mock at mission_system boundary)

> **Note:** `avionics` was the legacy name for `jeeves_infra`.

## 3) LLM Integration Contract

### Capability Responsibilities

```python
# 1. Register capability and agents
from jeeves_capability_hello_world import register_capability
register_capability()  # Must be called BEFORE infrastructure imports

# 2. Get LLM provider factory via adapters
from mission_system.adapters import create_llm_provider_factory, get_settings

settings = get_settings()
llm_factory = create_llm_provider_factory(settings)

# 3. Create provider for specific agent role
provider = llm_factory("understand")  # Returns LLMProvider

# 4. Generate response (blocking or streaming)
response = await provider.generate(
    model="qwen2.5-7b-instruct",
    prompt="Classify user intent...",
    options={"temperature": 0.3, "max_tokens": 2000}
)

# 5. Or stream tokens
async for chunk in provider.generate_stream(model, prompt, options):
    print(chunk.content, end="", flush=True)
```

### LiteLLM Guarantees to Capability

| Guarantee | Description |
|-----------|-------------|
| **Provider Abstraction** | Same API works for 100+ LLM providers |
| **Stream Consistency** | Async iterator yields TokenChunk objects |
| **Error Handling** | Stable error types for routing decisions |
| **Health Visibility** | Provider health check available |
| **No Side Effects** | LLM calls never modify capability state |

## 4) LLM Provider Factory Pattern

Capabilities receive an LLM factory from mission_system adapters:

```python
# Factory pattern (infrastructure-provided, capability-consumed)
from mission_system.adapters import create_llm_provider_factory

def create_service(settings: Settings) -> ChatbotService:
    """Create service with injected LLM factory."""
    llm_factory = create_llm_provider_factory(settings)

    return ChatbotService(
        llm_provider_factory=llm_factory,
        # ... other dependencies
    )
```

### LLM Provider Interface

```python
class LLMProvider(Protocol):
    """Interface that avionics implements, capabilities consume."""

    async def generate(
        self,
        model: str,
        prompt: str,
        options: dict
    ) -> str:
        """Generate completion from LLM."""
        ...

    async def generate_stream(
        self,
        model: str,
        prompt: str,
        options: dict
    ) -> AsyncIterator[TokenChunk]:
        """Stream tokens from LLM."""
        ...

    async def health_check(self) -> bool:
        """Check if provider is healthy."""
        ...
```

## 5) Configuration Ownership

### Capability-Owned Configuration

| Config | Example | Owner |
|--------|---------|-------|
| Agent list | `["understand", "think", "respond"]` | Capability |
| Agent-specific model | `UNDERSTAND_MODEL=qwen2.5-7b` | Capability |
| Agent temperature | `RESPOND_TEMPERATURE=0.7` | Capability |
| Domain timeouts | `ANALYSIS_TIMEOUT=300` | Capability |
| Prompt templates | `chatbot.understand`, `chatbot.respond` | Capability |

### jeeves_infra-Owned Configuration (via LiteLLM)

| Config | Example | Owner |
|--------|---------|-------|
| Provider URL | `LLAMASERVER_HOST` | jeeves_infra (read by capability) |
| Provider type | `llamaserver`, `openai`, `anthropic` | jeeves_infra |
| Retry policy | 3 retries, exponential backoff | LiteLLM |
| API keys | `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` | jeeves_infra/Environment |

### Configuration Flow

```python
# Capability registers agent-specific LLM config
register_capability()  # Registers agents with LLM requirements

# Infrastructure reads config, creates factory
settings = get_settings()  # Reads LLAMASERVER_HOST, LLM_PROVIDER, etc.
llm_factory = create_llm_provider_factory(settings)

# Factory creates provider with merged config
provider = llm_factory("understand")  # Merges agent config with settings
```

## 6) Error Handling Contract

### Capability Error Responsibilities

```python
async def handle_llm_error(error: Exception, context: dict) -> Action:
    """Capability decides what to do with LLM errors."""

    if isinstance(error, TimeoutError):
        # Retry with longer timeout? Switch provider? Fail?
        return Action.RETRY_WITH_FALLBACK

    if isinstance(error, ConnectionError):
        # Mark provider unhealthy? Wait and retry?
        return Action.MARK_UNHEALTHY_AND_RETRY

    if isinstance(error, ValueError):
        # Parse error? Log for debugging?
        logger.error("llm_response_error", raw=str(error))
        return Action.FAIL_WITH_MESSAGE

    return Action.FAIL
```

### LiteLLM Error Guarantees

- Errors are **categorized** by type (timeout, connection, rate limit, etc.)
- Errors **preserve context** when available
- Retry logic is **configurable** per provider
- Rate limiting is **handled automatically** with backoff

## 7) Testing Contract

### Capability Test Responsibilities

```python
# Unit tests: mock LLM provider
def test_agent_with_mock_llm():
    mock_provider = MockProvider(responses={"prompt": "response"})
    agent = Agent(llm_provider=mock_provider)
    result = await agent.process("input")
    assert result == "expected"

# Integration tests: use real provider with local llama-server
def test_pipeline_with_local_llm(llama_server):
    settings = get_test_settings()
    service = create_service(settings=settings)
    result = await service.process("query")
    assert result.status == "complete"
```

### jeeves_infra Test Guarantees

- jeeves_infra tests **never depend** on capability code
- jeeves_infra provides **test utilities** (MockProvider, test settings)
- LiteLLM integration tests cover **all provider types** independently

## 8) Deployment Independence

Capabilities depend on jeeves-core (which includes LiteLLM providers):

```
# As git submodule
.gitmodules:
  [submodule "jeeves-core"]
    path = jeeves-core
    url = https://github.com/org/jeeves-core.git
```

### Version Compatibility

| jeeves_infra Change | Capability Impact |
|-----------------|-------------------|
| New LLM provider | None (opt-in) |
| New error type | Handle in catch-all |
| New streaming feature | Ignore unknown fields |
| Breaking change | Major version bump, migration guide |

## 9) Acceptance Criteria for Capability Changes

A capability change is acceptable only if:

- [ ] No jeeves_infra internals accessed (only mission_system.adapters)
- [ ] LLM configuration policy is capability-owned
- [ ] Error handling is capability-owned
- [ ] No provider-specific payload formatting
- [ ] Tests don't require real LLM endpoints (use mocks or local llama-server)
- [ ] Configuration documented in capability, not jeeves_infra
