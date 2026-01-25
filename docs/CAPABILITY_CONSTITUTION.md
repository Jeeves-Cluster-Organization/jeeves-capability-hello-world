# Jeeves Capability Constitution

## 0) Purpose

A **Jeeves Capability** is a domain-specific vertical that provides specialized functionality through a pipeline of agents. Capabilities own their domain logic, prompts, tools, and endpoint selection policy while delegating infrastructure concerns to shared substrates.

This constitution defines the contract between capabilities and the platform layers they depend on.

## 1) Capability Ownership

### A Capability MUST Own

| Concern | Description |
|---------|-------------|
| **Domain Logic** | Business rules specific to the capability's purpose |
| **Agent Definitions** | Agent roles, responsibilities, and transitions |
| **Prompts** | LLM prompts tailored to the domain |
| **Tools** | Domain-specific tool implementations |
| **Endpoint Selection Policy** | Which LLM endpoint to use for which agent/task |
| **Response Formatting** | How to present results to users |
| **Validation Rules** | Domain-specific input/output validation |

### A Capability MUST NOT Own

| Concern | Belongs To |
|---------|------------|
| LLM wire protocol (HTTP, SSE, JSON) | Airframe |
| Endpoint health probing | Airframe |
| Backend-specific payload formatting | Airframe |
| Mission orchestration (checkpointing, recovery) | Mission System |
| Tool execution framework | Avionics |
| Database schemas (sessions, memory) | Avionics |
| gRPC service scaffolding | Mission System |

## 2) Layer Dependencies

```
┌─────────────────────────────────────────────────────────────┐
│                      Capability                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  agents/ prompts/ tools/ config/ orchestration/     │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         │                                    │
│         ┌───────────────┼───────────────┐                   │
│         │               │               │                   │
│         ▼               ▼               ▼                   │
│  ┌─────────────┐ ┌─────────────────────────────────┐        │
│  │  Airframe   │ │       Mission System API        │        │
│  │  Bridge     │ │  (adapters, contracts, api)     │        │
│  └──────┬──────┘ └───────────────┬─────────────────┘        │
└─────────┼────────────────────────┼──────────────────────────┘
          │                        │
          ▼                        ▼
   ┌─────────────┐    ┌───────────────────────────────┐
   │  Airframe   │    │       Mission System          │
   │ (inference) │    │      (orchestration)          │
   └─────────────┘    └───────────────┬───────────────┘
                                      │
                                      ▼
                           ┌───────────────────┐
                           │     Avionics      │
                           │ (infra/tools/llm) │
                           └─────────┬─────────┘
                                     │
                                     ▼
                           ┌───────────────────┐
                           │    jeeves-core    │
                           │   (contracts)     │
                           └───────────────────┘
```

### Import Rules

```python
# ✅ Capability CAN import from:
from airframe import AirframeClient, EndpointSpec, InferenceRequest
from mission_system.api import create_mission_runtime
from mission_system.adapters import get_settings, create_database_client
from mission_system.contracts import PersistenceProtocol
from mission_system.contracts_core import ContextBounds

# ❌ Capability MUST NOT import from:
# - avionics (go through mission_system.adapters)
# - jeeves_core (go through mission_system.contracts)

# ❌ Capability MUST NOT be imported by:
# - airframe (no capability imports)
# - mission_system (no capability imports)
# - jeeves-core (no capability imports)
# - other capabilities (no cross-capability imports)
```

### Why No Direct Avionics Imports?

Mission System provides **adapters** that wrap avionics functionality:
- `mission_system.adapters.create_database_client` → wraps avionics DB
- `mission_system.adapters.create_tool_executor` → wraps avionics tools
- `mission_system.adapters.create_llm_provider_factory` → wraps avionics LLM

This ensures:
1. Mission System can swap implementations without breaking capabilities
2. Capabilities don't couple to avionics internals
3. Testing is easier (mock at mission_system boundary)

## 3) Airframe Integration Contract

### Capability Responsibilities

```python
# 1. Create registry (static or dynamic)
def create_registry() -> EndpointRegistry:
    # Capability decides: env vars, config file, K8s, etc.
    return StaticRegistry([...])

# 2. Implement endpoint selection policy
def select_endpoint(agent_role: str, registry: EndpointRegistry) -> EndpointSpec:
    # Capability decides: round-robin, health-aware, agent-specific, etc.
    endpoints = registry.list_endpoints()
    healthy = [e for e in endpoints if registry.get_health(e.name).status == "healthy"]
    return healthy[0] if healthy else endpoints[0]

# 3. Build inference requests
def build_request(prompt: str, agent_config: dict) -> InferenceRequest:
    return InferenceRequest(
        messages=[Message(role="user", content=prompt)],
        model=agent_config.get("model"),
        temperature=agent_config.get("temperature"),
        max_tokens=agent_config.get("max_tokens"),
        stream=True,
    )

# 4. Handle stream events
async def process_response(stream: AsyncIterator[InferenceStreamEvent]) -> str:
    chunks = []
    async for event in stream:
        if event.type == StreamEventType.TOKEN:
            chunks.append(event.content)
        elif event.type == StreamEventType.ERROR:
            # Capability decides: retry, fallback, raise
            handle_error(event.error)
        elif event.type == StreamEventType.DONE:
            break
    return "".join(chunks)
```

### Airframe Guarantees to Capability

| Guarantee | Description |
|-----------|-------------|
| **Backend Abstraction** | Same `InferenceRequest` works for all backends |
| **Stream Consistency** | Every stream ends with exactly one `DONE` |
| **Error Categorization** | Errors have stable categories for routing decisions |
| **Health Visibility** | Registry provides health state for routing |
| **No Side Effects** | Airframe never modifies capability state |

## 4) LLM Provider Factory Pattern

Capabilities provide an LLM factory to the mission runtime:

```python
# Bridge module pattern (capability-owned)
def create_llm_provider_factory(registry: EndpointRegistry) -> Callable[[str], LLMProvider]:
    """
    Returns a factory that creates LLM providers per agent role.

    Args:
        registry: Endpoint registry (from airframe)

    Returns:
        Factory function: agent_role -> LLMProvider
    """
    client = AirframeClient(registry)

    def factory(agent_role: str) -> LLMProvider:
        return AirframeLLMProvider(
            client=client,
            registry=registry,
            agent_role=agent_role,
            endpoint_selector=capability_specific_selector,  # Capability policy
        )

    return factory
```

### LLM Provider Interface

```python
class LLMProvider(Protocol):
    """Interface that capabilities implement for mission runtime."""

    async def generate(
        self,
        model: str,
        prompt: str,
        options: dict
    ) -> str:
        """Generate completion from LLM."""
        ...
```

## 5) Configuration Ownership

### Capability-Owned Configuration

| Config | Example | Owner |
|--------|---------|-------|
| Agent list | `["perception", "planner", "critic"]` | Capability |
| Agent-specific model | `PLANNER_MODEL=gpt-4` | Capability |
| Agent temperature | `CRITIC_TEMPERATURE=0.2` | Capability |
| Routing rules | "use GPU for synthesis" | Capability |
| Domain timeouts | `ANALYSIS_TIMEOUT=300` | Capability |

### Airframe-Owned Configuration

| Config | Example | Owner |
|--------|---------|-------|
| Endpoint URL | `LLAMASERVER_HOST` | Airframe (read by capability) |
| Backend kind | `llama_server`, `openai_chat` | Airframe |
| Health check interval | 30s | Airframe |
| Retry policy | 3 retries, exponential backoff | Airframe |

### Shared Configuration (Capability Reads, Airframe Uses)

```python
# Capability reads env, passes to airframe
endpoint = EndpointSpec(
    name="primary",
    base_url=os.getenv("LLAMASERVER_HOST", "http://localhost:8080"),
    backend_kind=BackendKind.LLAMA_SERVER,
    api_type=os.getenv("LLAMASERVER_API_TYPE", "native"),
)
```

## 6) Error Handling Contract

### Capability Error Responsibilities

```python
async def handle_inference_error(error: AirframeError, context: dict) -> Action:
    """Capability decides what to do with airframe errors."""

    match error.category:
        case ErrorCategory.TIMEOUT:
            # Retry with longer timeout? Switch endpoint? Fail?
            return Action.RETRY_WITH_FALLBACK

        case ErrorCategory.CONNECTION:
            # Mark endpoint unhealthy? Wait and retry?
            return Action.MARK_UNHEALTHY_AND_RETRY

        case ErrorCategory.BACKEND:
            # Parse error response? Log for debugging?
            log.error("backend_error", raw=error.raw_backend)
            return Action.FAIL_WITH_MESSAGE

        case ErrorCategory.PARSE:
            # Retry? The response was malformed
            return Action.RETRY_ONCE

        case _:
            return Action.FAIL
```

### Airframe Error Guarantees

- Errors are **never raised** across the stream boundary
- Errors **always include** category and message
- Errors **preserve raw backend data** when available
- Errors are **deterministic** (same input → same category)

## 7) Health-Aware Routing

Capabilities MAY implement health-aware endpoint selection:

```python
class HealthAwareSelector:
    def __init__(self, registry: EndpointRegistry):
        self.registry = registry

    def select(self, agent_role: str) -> EndpointSpec:
        endpoints = self.registry.list_endpoints()

        # Filter by health
        healthy = [
            e for e in endpoints
            if self.registry.get_health(e.name).status == "healthy"
        ]

        # Filter by agent requirements (capability policy)
        suitable = [
            e for e in (healthy or endpoints)
            if self._matches_agent_requirements(e, agent_role)
        ]

        if not suitable:
            raise NoSuitableEndpointError(agent_role)

        # Selection strategy (capability policy)
        return self._select_strategy(suitable)

    def _matches_agent_requirements(self, endpoint: EndpointSpec, role: str) -> bool:
        """Capability-specific matching logic."""
        # Example: critic needs high-quality model
        if role == "critic" and endpoint.capacity.tier != "A100-80GB":
            return False
        return True

    def _select_strategy(self, endpoints: List[EndpointSpec]) -> EndpointSpec:
        """Capability-specific selection strategy."""
        # Round-robin, least-loaded, random, etc.
        return random.choice(endpoints)
```

## 8) Testing Contract

### Capability Test Responsibilities

```python
# Unit tests: mock airframe
def test_agent_with_mock_llm():
    mock_provider = MockLLMProvider(responses={"prompt": "response"})
    agent = Agent(llm_provider=mock_provider)
    result = await agent.process("input")
    assert result == "expected"

# Integration tests: use airframe with mock backend
def test_pipeline_with_mock_backend(mock_llama_server):
    registry = StaticRegistry([mock_endpoint])
    service = create_service(registry=registry)
    result = await service.process("query")
    assert result.status == "complete"
```

### Airframe Test Guarantees

- Airframe tests **never depend** on capability code
- Airframe provides **test utilities** (mock adapters, fake registries)
- Airframe tests cover **all backend adapters** independently

## 9) Deployment Independence

Capabilities and airframe deploy independently:

```
# Capability pins airframe version
requirements.txt:
  jeeves-airframe>=1.2.0,<2.0.0

# Or as git submodule
.gitmodules:
  [submodule "jeeves-airframe"]
    path = airframe
    url = https://github.com/org/jeeves-airframe.git
```

### Version Compatibility

| Airframe Change | Capability Impact |
|-----------------|-------------------|
| New adapter | None (opt-in) |
| New error category | Handle in catch-all |
| New stream event type | Ignore unknown events |
| Breaking change | Major version bump, migration guide |

## 10) Acceptance Criteria for Capability Changes

A capability change is acceptable only if:

- [ ] No airframe internals accessed (only public API)
- [ ] Endpoint selection policy is capability-owned
- [ ] Error handling is capability-owned
- [ ] No backend-specific payload formatting
- [ ] Tests don't require real LLM endpoints
- [ ] Configuration documented in capability, not airframe
