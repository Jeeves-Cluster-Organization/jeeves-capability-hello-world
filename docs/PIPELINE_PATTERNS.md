# Pipeline Patterns

Advanced pipeline topologies beyond linear sequential flows.

---

## Linear Sequential

The simplest pattern (used in hello-world):

```
understand → think → respond
```

```python
AgentConfig(name="understand", default_next="think"),
AgentConfig(name="think", default_next="respond"),
AgentConfig(name="respond", default_next="end"),
```

---

## Conditional Branching

Route based on agent output using `RoutingRule`:

```python
AgentConfig(
    name="classifier",
    routing_rules=[
        RoutingRule(condition="intent", value="search", target="search_agent"),
        RoutingRule(condition="intent", value="create", target="create_agent"),
    ],
    default_next="general_handler",
    error_next="error_recovery",
)
```

The kernel evaluates `routing_rules` in order; first match wins. Falls back to `default_next`.

---

## Fan-Out (1→N)

Parallel execution with multiple agents depending on the same predecessor:

```python
AgentConfig(name="planner", default_next="end"),
AgentConfig(name="research_a", requires=["planner"]),
AgentConfig(name="research_b", requires=["planner"]),
```

Both `research_a` and `research_b` become ready after `planner` completes.

---

## Fan-In (N→1)

Wait for multiple predecessors before proceeding:

```python
AgentConfig(
    name="synthesizer",
    requires=["research_a", "research_b"],
    join_strategy=JoinStrategy.ALL,  # Wait for all
)
```

Use `JoinStrategy.ANY` to proceed when any predecessor completes.

---

## Error Recovery

Route to a handler on agent failure:

```python
AgentConfig(
    name="risky_operation",
    default_next="success_path",
    error_next="error_handler",
)
```

---

## Envelope Extension

Store routing hints or custom data in envelope metadata:

```python
def post_process(envelope: Envelope, result: dict) -> Envelope:
    envelope.metadata["routing_hint"] = result.get("category")
    envelope.metadata["confidence"] = result.get("score", 0.0)
    return envelope
```

Routing rules can reference metadata values via the `condition` field.

---

## Key Types

```python
from protocols import (
    AgentConfig,
    RoutingRule,
    JoinStrategy,  # ALL or ANY
    PipelineConfig,
)
```

---

*See [CAPABILITY_INTEGRATION_GUIDE.md](CAPABILITY_INTEGRATION_GUIDE.md) for full API reference.*
