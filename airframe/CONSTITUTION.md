# Jeeves-Airframe Constitution (Minimum)

## 0) Purpose
jeeves-airframe is a reusable platform substrate for inference and platform integration.
It standardizes how capabilities interact with heterogeneous inference backends and runtime substrates,
while keeping capability logic and orchestration policy outside airframe.

## 1) Ownership Boundaries
Airframe MUST own:
- Endpoint representation and metadata (including backend kind, tags, capacity hints).
- Endpoint discovery mechanisms (registries), including watchability.
- Backend adapters that normalize request/response and streaming semantics.
- Health signal representation (state + detail), and optional probing mechanisms.
- Observability hooks (request-level spans/metrics/log fields).

Airframe MUST NOT own:
- Agent logic, prompts, pipeline semantics, or tool execution.
- Endpoint selection policy (routing decisions) for a capability.
- Workflow/task orchestration semantics (queues, checkpoints, mission logic).
- Cluster mutation/deployment logic (Helm charts, Deployments, autoscaling) as a required component.

## 2) Canonical Inference Contract
Airframe MUST expose a stable, backend-agnostic inference contract:

- Canonical request shape: chat messages.
- Request-selectable model: model MAY be provided; endpoints MAY ignore/default it.
- Tool calling fields MUST exist in the request contract (even if unused by some backends).
- Stream-first: inference is exposed as a stream of events.
  - Non-streaming backends MUST still emit a stream (single final event + done).

Airframe MUST NOT require capabilities to format backend-specific payloads.

## 3) Streaming Semantics
Airframe MUST define a small, stable set of stream event types with consistent meaning.
Adapters MUST translate backend streaming formats into these event types.

Adapters MUST terminate the stream deterministically:
- emit a single terminal event (done) exactly once
- close network resources promptly on completion or cancellation

## 4) Error Semantics
Airframe MUST standardize errors into a small stable taxonomy (timeout/connection/backend/parse/unknown).
Airframe errors MUST preserve raw backend payloads or raw diagnostic data when available.

Adapters MUST NOT raise backend-specific exception types across the public airframe API.
Errors MUST be representable as stream events (so streaming callers can handle failures).

## 5) Endpoint Registry and Watchability
Airframe MUST provide an EndpointRegistry interface with:
- snapshot listing (list_endpoints)
- health state retrieval (get_health; may be unknown initially)
- watchability (watch(callback) that emits snapshots)

Registries MUST be usable without Kubernetes.
Kubernetes-backed registries MUST be optional and must not be required to import or run airframe.

## 6) Kubernetes Integration (Airframe Scope)
Airframe Kubernetes integration MUST be read-only discovery/configuration at minimum:
- read endpoint specs from a ConfigMap/CRD/Service annotations
- provide watch updates (polling acceptable initially)
- no cluster mutation operations are required or assumed

Airframe MUST NOT require cluster-admin privileges.

## 7) Observability
Airframe MUST provide request-level observability hooks:
- span boundaries and stable attributes (capability/app may add higher-level labels)
- metrics/log fields including at least: endpoint_name, backend_kind, status, latency

Token-level telemetry MUST be opt-in (off by default).

## 8) Dependency Direction
Airframe MUST be reusable across capabilities and environments:
- Airframe MUST NOT import capability code.
- Airframe MUST NOT depend on jeeves-core internals.
- Capabilities MAY depend on both jeeves-core and airframe and compose them.

## 9) Backward Compatibility
Airframe MUST support a minimal single-endpoint setup with zero external dependencies beyond its adapters.
Adding new adapters or registries MUST NOT break existing callers.

## 10) Acceptance Criteria (Minimum)
A change to airframe is acceptable only if it preserves:
- stable request/stream/error semantics
- no routing policy embedded in airframe
- watchable registry interface
- adapter isolation of backend specifics
- optional Kubernetes integration that does not affect non-K8s usage
