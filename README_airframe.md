# jeeves-airframe (embedded)

This repository now contains a minimal **airframe** package that factors
inference-platform concerns away from capabilities. Airframe owns endpoint
representation, backend adapters, health signals, observability hooks, and a
stable stream-first inference contract. Capabilities keep control of agent
logic, prompts, pipelines, tool execution, and endpoint selection policy.

## Integrating an existing capability

1) Build an `InferenceRequest` with your chat messages (and optional tools/model):
```python
from airframe.types import InferenceRequest, Message
req = InferenceRequest(messages=[Message(role="user", content="Hello")])
```

2) Apply your own endpoint-selection policy using the registry:
```python
from airframe.registry import StaticRegistry
endpoint = StaticRegistry([endpoint_spec]).list_endpoints()[0]
```

3) Invoke streaming inference:
```python
from airframe.client import AirframeClient
client = AirframeClient(StaticRegistry([endpoint]))
async for event in client.stream_infer(endpoint, req):
    ...
```

Airframe never decides which endpoint to use; it only provides watchable
registries and normalized adapters.

## Kubernetes (optional)

`K8sRegistry` is an optional, read-only registry that loads endpoint specs from
a single ConfigMap key. JSON is required; YAML is supported only if PyYAML is installed.
`watch()` requires an active asyncio event loop.
Import via `from airframe.k8s import K8sRegistry`.

Fixed schema:
- ConfigMap `data["endpoints"]` contains a JSON string representing a list of EndpointSpec dicts.

Optional dependency:
- Install with `airframe[k8s]` (when packaged) to pull in the Kubernetes client.
- If Kubernetes deps are absent, `K8sRegistry` raises `ImportError` on init with a clear message.

## Sanity Checks

- `python -m airframe.selftest` — should print "airframe selftest: ok" if httpx is installed and imports succeed.
- `pytest tests/airframe` — unit suite should pass (SSE parsing, error categorization, registry watch).
- `AIRFRAME_ENABLED=true python -m airframe.selftest` — confirms env parsing does not raise; no external network calls made.
- Default: `AIRFRAME_ENABLED` is treated as true unless set to `0/false/no`; fallback to legacy provider is logged with warning if airframe init fails.
- Docker compose: `docker compose -f docker/docker-compose.yml run --rm orchestrator python -m airframe.selftest` — same check inside the container image.
- Local python: `AIRFRAME_ENABLED=true python -m airframe.selftest` — verifies the bridge/env path without containers.
- Integration (opt-in): `AIRFRAME_INTEGRATION=1 pytest tests/airframe/test_integration_llama.py` — exercises real llama-server streaming if available.

## Hardening Checks

- `pytest tests/airframe` — should pass deterministically; includes import, SSE, cancellation, and k8s registry tests.
- `python -m airframe.selftest` — prints versions for httpx and optional k8s deps; no network calls.
- `AIRFRAME_INTEGRATION=1 pytest tests/airframe/test_integration_llama.py` — optional real llama-server streaming check.
- Note: `from airframe.k8s import K8sRegistry` raises ImportError when k8s deps are not installed.
- Note: `watch()` requires an active asyncio loop.
- Optional: `AIRFRAME_STRICT=true` prevents fallback when airframe init fails (useful for CI/staging).
