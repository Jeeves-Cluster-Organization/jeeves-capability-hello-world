# jeeves-airframe (embedded)

This repository contains an embedded **airframe** package that factors
inference-platform concerns away from capabilities. Airframe owns endpoint
representation, backend adapters, health signals, observability hooks, and a
stable stream-first inference contract. Capabilities keep control of agent
logic, prompts, pipelines, tool execution, and endpoint selection policy.

## Quick Start

```python
from airframe import (
    AirframeClient,
    StaticRegistry,
    EndpointSpec,
    BackendKind,
    InferenceRequest,
    Message,
    StreamEventType,
)

# 1. Define endpoint(s)
endpoint = EndpointSpec(
    name="local-llama",
    base_url="http://localhost:8080",
    backend_kind=BackendKind.LLAMA_SERVER,
    api_type="native",  # or "openai" for /v1/completions
)

# 2. Create registry and client
registry = StaticRegistry([endpoint])
client = AirframeClient(registry)

# 3. Build request
request = InferenceRequest(
    messages=[Message(role="user", content="Hello, world!")],
    temperature=0.7,
    max_tokens=512,
    stream=True,
)

# 4. Stream inference
async for event in client.stream_infer(endpoint, request):
    if event.type == StreamEventType.TOKEN:
        print(event.content, end="", flush=True)
    elif event.type == StreamEventType.ERROR:
        print(f"Error: {event.error}")
    elif event.type == StreamEventType.DONE:
        break
```

## Supported Backends

| Backend Kind | Adapter | Status | Notes |
|--------------|---------|--------|-------|
| `LLAMA_SERVER` | `LlamaServerAdapter` | Full | llama.cpp server (native or OpenAI-compat mode) |
| `OPENAI_CHAT` | `OpenAIChatAdapter` | Full | OpenAI, Azure OpenAI, vLLM, LocalAI |
| `ANTHROPIC_MESSAGES` | — | Placeholder | Not yet implemented |

### LlamaServerAdapter

Supports llama.cpp server with two API modes:

- **Native mode** (`api_type="native"`): Uses `/completion` endpoint with llama.cpp-specific parameters
- **OpenAI mode** (`api_type="openai"`): Uses `/v1/completions` endpoint

```python
endpoint = EndpointSpec(
    name="llama",
    base_url="http://localhost:8080",
    backend_kind=BackendKind.LLAMA_SERVER,
    api_type="native",  # or "openai"
)
```

### OpenAIChatAdapter

Supports OpenAI Chat Completions API and compatible endpoints:

```python
endpoint = EndpointSpec(
    name="openai",
    base_url="https://api.openai.com",
    backend_kind=BackendKind.OPENAI_CHAT,
    metadata={"api_key": "sk-..."},  # API key in metadata
)

# For Azure OpenAI
endpoint = EndpointSpec(
    name="azure",
    base_url="https://your-resource.openai.azure.com",
    backend_kind=BackendKind.OPENAI_CHAT,
    metadata={"azure_api_key": "..."},  # Azure uses different header
)
```

## Health Checking

Airframe provides HTTP-based health probing for endpoints:

```python
from airframe import StaticRegistry, HttpHealthProbe

# Create registry with health probe
probe = HttpHealthProbe(timeout=5.0)
registry = StaticRegistry([endpoint], health_probe=probe)

# One-time health check
await registry.check_health()

# Get health state
health = registry.get_health("local-llama")
print(health.status)  # "healthy", "degraded", "unhealthy", or "unknown"

# List only healthy endpoints
healthy = registry.list_healthy_endpoints()

# Background health monitoring (every 30 seconds)
handle = registry.start_health_monitor(interval=30.0)
# ... later ...
registry.stop_health_monitor()
```

Health check paths per backend:
- `LLAMA_SERVER`: `GET /health`
- `OPENAI_CHAT`: `GET /v1/models`
- `ANTHROPIC_MESSAGES`: `HEAD /v1/messages`

## Endpoint Registry

### StaticRegistry

For fixed endpoint configurations:

```python
from airframe import StaticRegistry, EndpointSpec, BackendKind

endpoints = [
    EndpointSpec(name="gpu-1", base_url="http://gpu1:8080", backend_kind=BackendKind.LLAMA_SERVER),
    EndpointSpec(name="gpu-2", base_url="http://gpu2:8080", backend_kind=BackendKind.LLAMA_SERVER),
]
registry = StaticRegistry(endpoints)
```

### K8sRegistry (Optional)

For Kubernetes-based dynamic discovery:

```python
from airframe.k8s import K8sRegistry

registry = K8sRegistry(
    configmap_name="llm-endpoints",
    namespace="inference",
    key="endpoints",
    poll_interval=15.0,
)

# Watch for changes
handle = registry.watch(async_callback)
```

ConfigMap schema:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: llm-endpoints
data:
  endpoints: |
    [
      {
        "name": "gpu-node-1",
        "base_url": "http://llm-gpu-1:8080",
        "backend_kind": "llama_server",
        "api_type": "native",
        "capacity": {"max_concurrency": 4, "tier": "A100-80GB"}
      }
    ]
```

## Error Handling

Errors are categorized into a stable taxonomy:

```python
from airframe import ErrorCategory

# Categories:
# - TIMEOUT: Request timed out
# - CONNECTION: Network/connection error
# - BACKEND: HTTP 4xx/5xx from backend
# - PARSE: JSON/SSE parsing error
# - UNKNOWN: Uncategorized error

async for event in client.stream_infer(endpoint, request):
    if event.type == StreamEventType.ERROR:
        if event.error.category == ErrorCategory.TIMEOUT:
            # Retry logic
            pass
        elif event.error.category == ErrorCategory.CONNECTION:
            # Mark endpoint unhealthy
            pass
        # Raw backend response available in event.error.raw_backend
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AIRFRAME_ENABLED` | `true` | Enable airframe layer |
| `AIRFRAME_STRICT` | `false` | Fail if airframe init fails (no fallback) |
| `AIRFRAME_DEBUG` | `false` | Enable debug logging |
| `LLAMASERVER_HOST` | `http://localhost:8080` | Default llama-server URL |
| `LLAMASERVER_API_TYPE` | `native` | API mode (`native` or `openai`) |

### Capability Bridge

The `airframe_bridge.py` module provides integration with the capability:

```python
from airframe_bridge import (
    create_airframe_registry_from_env,
    create_airframe_llm_factory,
)

# Create registry from environment
registry = create_airframe_registry_from_env()

# Create LLM factory for runtime
llm_factory = create_airframe_llm_factory(registry)
runtime.llm_provider_factory = llm_factory
```

## Verification

### Sanity Checks

```bash
# Basic import and selftest
python -m airframe.selftest

# Unit tests
pytest tests/airframe -v

# Integration test (requires llama-server)
AIRFRAME_INTEGRATION=1 pytest tests/airframe/test_integration_llama.py -v
```

### Docker

```bash
# Selftest in container
docker compose -f docker/docker-compose.yml run --rm orchestrator python -m airframe.selftest
```

## Architecture

```
airframe/
├── __init__.py          # Public exports
├── types.py             # InferenceRequest, Message, StreamEvent, etc.
├── endpoints.py         # EndpointSpec, HealthState, BackendKind
├── registry.py          # EndpointRegistry, StaticRegistry
├── client.py            # AirframeClient (adapter dispatch)
├── health.py            # HealthProbe, HttpHealthProbe
├── telemetry.py         # Observability hooks (placeholder)
├── selftest.py          # Import verification
├── adapters/
│   ├── base.py          # BackendAdapter ABC
│   ├── llama_server.py  # llama.cpp server adapter
│   └── openai_chat.py   # OpenAI Chat Completions adapter
└── k8s/
    ├── __init__.py      # K8sRegistry export
    ├── registry.py      # ConfigMap-based registry
    └── types.py         # K8s-specific types
```

## Constitution

See `airframe/CONSTITUTION.md` for the architectural principles:

1. **Ownership**: Airframe owns endpoints, adapters, health; capabilities own routing policy
2. **Stream-first**: All inference exposed as async streams
3. **Error taxonomy**: Stable categories (timeout/connection/backend/parse/unknown)
4. **Backend isolation**: Adapters normalize protocol differences
5. **Optional K8s**: Kubernetes integration never required
