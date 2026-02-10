# Envelope State Exchange JSON Schema

**Purpose**: Define the boundary contract for envelope state exchange between Python `jeeves_infra` and Go `coreengine` (or vice versa) via stdin/stdout or HTTP.

---

## Overview

The `GenericEnvelope` can be serialized to JSON via:
- **Python**: `envelope.to_state_dict()` → JSON
- **Go**: `envelope.ToStateDict()` → JSON

And deserialized via:
- **Python**: `GenericEnvelope.from_state_dict(data)`
- **Go**: `FromStateDict(data)`

---

## JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "GenericEnvelope",
  "description": "Envelope state for cross-language exchange between Python and Go",
  "type": "object",
  "required": [
    "envelope_id",
    "request_id",
    "user_id",
    "session_id",
    "raw_input",
    "outputs",
    "current_stage",
    "terminated"
  ],
  "properties": {
    "envelope_id": {
      "type": "string",
      "description": "Unique envelope identifier (format: env_<uuid>)",
      "pattern": "^env_[a-f0-9]{16}$"
    },
    "request_id": {
      "type": "string",
      "description": "Request identifier (format: req_<uuid>)",
      "pattern": "^req_[a-f0-9]{16}$"
    },
    "user_id": {
      "type": "string",
      "description": "User identifier",
      "default": "anonymous"
    },
    "session_id": {
      "type": "string",
      "description": "Session identifier (format: sess_<uuid>)",
      "pattern": "^sess_[a-f0-9]{16}$"
    },
    "raw_input": {
      "type": "string",
      "description": "Original user message"
    },
    "received_at": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp when request was received"
    },
    "outputs": {
      "type": "object",
      "description": "Dynamic agent outputs keyed by output_key",
      "additionalProperties": {
        "type": "object",
        "additionalProperties": true
      }
    },
    "current_stage": {
      "type": "string",
      "description": "Current stage name (agent name or 'start'/'end')"
    },
    "stage_order": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Ordered list of stage names from pipeline config"
    },
    "iteration": {
      "type": "integer",
      "minimum": 0,
      "description": "Current retry iteration"
    },
    "max_iterations": {
      "type": "integer",
      "minimum": 1,
      "default": 3
    },
    "llm_call_count": {
      "type": "integer",
      "minimum": 0,
      "description": "Total LLM calls made"
    },
    "max_llm_calls": {
      "type": "integer",
      "minimum": 1,
      "default": 10
    },
    "agent_hop_count": {
      "type": "integer",
      "minimum": 0,
      "description": "Number of agent transitions"
    },
    "max_agent_hops": {
      "type": "integer",
      "minimum": 1,
      "default": 21
    },
    "terminal_reason": {
      "type": ["string", "null"],
      "enum": [
        null,
        "completed_successfully",
        "clarification_required",
        "confirmation_required",
        "denied_by_policy",
        "tool_failed_recoverably",
        "tool_failed_fatally",
        "max_iterations_exceeded",
        "max_llm_calls_exceeded",
        "max_agent_hops_exceeded",
        "max_critic_fires_exceeded"
      ],
      "description": "Why processing terminated"
    },
    "terminated": {
      "type": "boolean",
      "description": "Whether processing is complete"
    },
    "termination_reason": {
      "type": ["string", "null"],
      "description": "Human-readable termination reason"
    },
    "clarification_pending": {
      "type": "boolean",
      "default": false
    },
    "clarification_question": {
      "type": ["string", "null"]
    },
    "clarification_response": {
      "type": ["string", "null"]
    },
    "confirmation_pending": {
      "type": "boolean",
      "default": false
    },
    "confirmation_id": {
      "type": ["string", "null"]
    },
    "confirmation_message": {
      "type": ["string", "null"]
    },
    "confirmation_response": {
      "type": ["boolean", "null"]
    },
    "completed_stages": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "stage_number": { "type": "integer" },
          "satisfied_goals": {
            "type": "array",
            "items": { "type": "string" }
          },
          "summary": { "type": "object" },
          "plan_id": { "type": ["string", "null"] }
        }
      }
    },
    "current_stage_number": {
      "type": "integer",
      "minimum": 1,
      "default": 1
    },
    "max_stages": {
      "type": "integer",
      "minimum": 1,
      "default": 5
    },
    "all_goals": {
      "type": "array",
      "items": { "type": "string" }
    },
    "remaining_goals": {
      "type": "array",
      "items": { "type": "string" }
    },
    "goal_completion_status": {
      "type": "object",
      "additionalProperties": {
        "type": "string",
        "enum": ["pending", "satisfied", "failed"]
      }
    },
    "prior_plans": {
      "type": "array",
      "items": { "type": "object" }
    },
    "critic_feedback": {
      "type": "array",
      "items": { "type": "string" }
    },
    "errors": {
      "type": "array",
      "items": { "type": "object" }
    },
    "completed_at": {
      "type": ["string", "null"],
      "format": "date-time"
    },
    "metadata": {
      "type": "object",
      "additionalProperties": true
    }
  }
}
```

---

## Communication Patterns

### Pattern 1: stdin/stdout (Process-based)

Python calls Go coreengine via subprocess:

```python
import subprocess
import json

# Python → Go
envelope_json = json.dumps(envelope.to_state_dict())
process = subprocess.Popen(
    ["./go-coreengine", "process"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    text=True
)
result_json, _ = process.communicate(input=envelope_json)
updated_envelope = GenericEnvelope.from_state_dict(json.loads(result_json))
```

Go receives and responds:

```go
import (
    "encoding/json"
    "os"
    "github.com/.../go/coreengine/envelope"
)

func main() {
    var state map[string]any
    json.NewDecoder(os.Stdin).Decode(&state)

    env := envelope.FromStateDict(state)
    // Process envelope...

    result := env.ToStateDict()
    json.NewEncoder(os.Stdout).Encode(result)
}
```

### Pattern 2: HTTP JSON API

**Request** (Python → Go):
```http
POST /api/v1/process HTTP/1.1
Content-Type: application/json

{
  "envelope_id": "env_abc123...",
  "request_id": "req_xyz789...",
  "raw_input": "Analyze the authentication flow",
  "outputs": {},
  "current_stage": "start",
  "terminated": false,
  ...
}
```

**Response** (Go → Python):
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "envelope_id": "env_abc123...",
  "request_id": "req_xyz789...",
  "outputs": {
    "perception": {
      "normalized_input": "...",
      "context": {...}
    },
    "intent": {
      "intent": "trace_flow",
      "goals": ["..."]
    }
  },
  "current_stage": "intent",
  "terminated": false,
  ...
}
```

---

## Agent Output Schema

The `outputs` field contains agent results. Each agent writes to its own key:

### Perception Agent Output

```json
{
  "outputs": {
    "perception": {
      "normalized_input": "string",
      "detected_language": "string",
      "extracted_entities": ["string"],
      "context": {
        "session_history": [...],
        "user_preferences": {...}
      }
    }
  }
}
```

### Intent Agent Output

```json
{
  "outputs": {
    "intent": {
      "intent": "trace_flow | analyze_code | explain | ...",
      "goals": ["Goal 1", "Goal 2"],
      "confidence": 0.95,
      "clarification_needed": false
    }
  }
}
```

### Plan Agent Output

```json
{
  "outputs": {
    "plan": {
      "plan_id": "plan_xxx",
      "steps": [
        {
          "tool": "code_search",
          "params": {"query": "..."},
          "expected_output": "..."
        }
      ],
      "estimated_complexity": "medium"
    }
  }
}
```

### Execution Agent Output

```json
{
  "outputs": {
    "execution": {
      "status": "success | partial | error",
      "results": [
        {
          "step_index": 0,
          "tool": "code_search",
          "result": {...},
          "duration_ms": 150
        }
      ],
      "evidence": [
        {
          "location": "src/auth.py:42",
          "content": "def authenticate()...",
          "relevance": "Entry point for auth flow"
        }
      ]
    }
  }
}
```

### Critic Agent Output

```json
{
  "outputs": {
    "critic": {
      "verdict": "approved | reintent | next_stage",
      "satisfied_goals": ["Goal 1"],
      "unsatisfied_goals": ["Goal 2"],
      "feedback": "Need more evidence for Goal 2",
      "confidence": 0.85
    }
  }
}
```

### Integration Agent Output

```json
{
  "outputs": {
    "integration": {
      "final_response": "The authentication flow starts at...",
      "citations": [
        {
          "text": "authenticate() function",
          "location": "src/auth.py:42"
        }
      ],
      "follow_up_suggestions": ["Would you like to see the token validation?"]
    }
  }
}
```

---

## Processing Record Schema

```json
{
  "processing_history": [
    {
      "agent": "perception",
      "stage_order": 1,
      "started_at": "2025-12-10T10:00:00Z",
      "completed_at": "2025-12-10T10:00:01Z",
      "duration_ms": 1000,
      "status": "success",
      "error": null,
      "llm_calls": 1
    }
  ]
}
```

---

## Error Format

```json
{
  "errors": [
    {
      "agent": "execution",
      "error_type": "ToolError",
      "message": "Code search failed: timeout",
      "timestamp": "2025-12-10T10:00:05Z",
      "recoverable": true,
      "details": {
        "tool": "code_search",
        "timeout_ms": 30000
      }
    }
  ]
}
```

---

## Datetime Format

All datetime fields use **ISO 8601 / RFC 3339** format:

```
"2025-12-10T10:00:00Z"           # UTC
"2025-12-10T10:00:00+00:00"      # With timezone
"2025-12-10T10:00:00.123456Z"    # With microseconds
```

Both Python and Go produce compatible formats:
- Python: `datetime.isoformat()`
- Go: `time.Format(time.RFC3339)`

---

## Compatibility Notes

1. **Null handling**: Both languages represent missing optional fields as `null`
2. **Empty arrays**: Use `[]` not `null` for empty lists
3. **Empty objects**: Use `{}` not `null` for empty dicts/maps
4. **Numbers**: JSON numbers (no int/float distinction in JSON)
5. **Booleans**: JSON `true`/`false`

---

## Validation

### Python (Pydantic)

```python
from jeeves_infra.protocols import GenericEnvelope
import json

data = json.loads(json_string)
envelope = GenericEnvelope.from_state_dict(data)  # Validates during construction
```

---

## Version Compatibility

The schema is versioned implicitly via field presence:
- **v1.0**: Core fields (envelope_id, request_id, outputs, etc.)
- **v1.1**: Added multi-stage execution (completed_stages, goal_completion_status)
- **v1.2**: Added bounds tracking (llm_call_count, agent_hop_count)

Consumers should handle missing fields gracefully by using defaults.
