# Frontend Migration Guide: Unified Event Schema

**Date:** 2025-12-14
**Status:** Implementation Complete (Backend)
**Action Required:** Frontend Updates

---

## Overview

The Jeeves backend has been updated to use a **constitutional UnifiedEvent schema** that standardizes all event emissions across the system. The WebSocket interface now emits events in a new format.

**What Changed:**
- Event schema is now standardized with consistent timestamps, categories, and metadata
- All pipeline events (agent lifecycle, tool execution, critic decisions, etc.) use the same format
- Events include categorization and severity for better filtering and routing

**What Stayed the Same:**
- WebSocket connection mechanism unchanged
- Event subscription patterns still work (`agent.*`, `planner.*`, etc.)
- Core event types unchanged (agent.started, planner.plan_created, etc.)

---

## New Event Format

### Before (Legacy)

```json
{
  "event": "agent.started",
  "payload": {
    "agent": "planner",
    "session_id": "sess_123",
    "request_id": "req_456"
  }
}
```

### After (UnifiedEvent)

```json
{
  "type": "event",
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "agent.started",
  "category": "agent_lifecycle",
  "timestamp": "2025-12-14T01:58:26.123Z",
  "timestamp_ms": 1734141506123,
  "payload": {
    "agent": "planner"
  },
  "severity": "info",
  "session_id": "sess_123",
  "request_id": "req_456",
  "source": "agent_emitter"
}
```

---

## TypeScript Interface

```typescript
/**
 * Unified Event Schema - Constitutional Standard
 *
 * All events from the Jeeves backend conform to this schema.
 */
interface UnifiedEvent {
  // Message type discriminator
  type: "event";

  // Identity
  event_id: string;                    // UUID v4
  event_type: string;                  // Namespaced: "agent.started", "critic.decision"
  category: EventCategory;             // Broad classification

  // Timing (standardized - both formats provided)
  timestamp: string;                   // ISO 8601 UTC: "2025-12-14T01:58:26.123Z"
  timestamp_ms: number;                // Epoch milliseconds: 1734141506123

  // Context (for correlation and filtering)
  session_id: string;                  // Session correlation ID
  request_id: string;                  // Request correlation ID

  // Payload
  payload: Record<string, any>;        // Event-specific data

  // Metadata
  severity: EventSeverity;             // Event severity
  source: string;                      // Component that emitted ("agent_emitter", "gateway", etc.)
}

/**
 * Event categories for filtering and routing
 */
type EventCategory =
  | "agent_lifecycle"      // Agent start/complete events
  | "tool_execution"       // Tool start/complete events
  | "pipeline_flow"        // Flow start/complete/error
  | "critic_decision"      // Critic verdicts
  | "stage_transition"     // Multi-stage progress
  | "domain_event"         // Business events (task, session, etc.)
  | "session_event"        // Session lifecycle
  | "workflow_event";      // Workflow operations

/**
 * Event severity for filtering and alerting
 */
type EventSeverity =
  | "debug"
  | "info"
  | "warning"
  | "error"
  | "critical";
```

---

## Standard Event Types

All event types follow a namespaced pattern: `{agent}.{action}`

### Agent Lifecycle Events

| Event Type | Category | Description |
|-----------|----------|-------------|
| `agent.started` | agent_lifecycle | Generic agent started |
| `agent.completed` | agent_lifecycle | Generic agent completed |
| `perception.started` | agent_lifecycle | Perception agent started |
| `perception.completed` | agent_lifecycle | Perception agent completed |
| `intent.started` | agent_lifecycle | Intent agent started |
| `intent.completed` | agent_lifecycle | Intent agent completed |
| `planner.started` | agent_lifecycle | Planner agent started |
| `planner.plan_created` | agent_lifecycle | Planner created execution plan |
| `executor.started` | agent_lifecycle | Executor agent started |
| `executor.completed` | agent_lifecycle | Executor agent completed |
| `synthesizer.started` | agent_lifecycle | Synthesizer agent started |
| `synthesizer.completed` | agent_lifecycle | Synthesizer agent completed |
| `critic.started` | agent_lifecycle | Critic agent started |
| `critic.decision` | critic_decision | Critic made a decision |
| `integration.started` | agent_lifecycle | Integration agent started |
| `integration.completed` | agent_lifecycle | Integration agent completed |

### Tool Execution Events

| Event Type | Category | Description |
|-----------|----------|-------------|
| `executor.tool_started` | tool_execution | Tool execution started |
| `executor.tool_completed` | tool_execution | Tool execution completed |
| `executor.tool_failed` | tool_execution | Tool execution failed |

### Pipeline Flow Events

| Event Type | Category | Description |
|-----------|----------|-------------|
| `orchestrator.started` | pipeline_flow | Pipeline started |
| `orchestrator.completed` | pipeline_flow | Pipeline completed |
| `orchestrator.error` | pipeline_flow | Pipeline error occurred |
| `orchestrator.stage_transition` | stage_transition | Multi-stage transition |

### Session Events

| Event Type | Category | Description |
|-----------|----------|-------------|
| `session.created` | session_event | Session created |
| `session.updated` | session_event | Session updated |
| `session.deleted` | session_event | Session deleted |

---

## Frontend Implementation Guide

### Step 1: Update WebSocket Event Handler

```typescript
// OLD: Legacy event handling
function handleWebSocketMessage(message: any) {
  if (message.event === "agent.started") {
    updateAgentStatus(message.payload.agent, "running");
  }
}

// NEW: UnifiedEvent handling
function handleWebSocketMessage(message: any) {
  if (message.type === "event") {
    const event = message as UnifiedEvent;

    // Route by category for efficiency
    switch (event.category) {
      case "agent_lifecycle":
        handleAgentLifecycle(event);
        break;
      case "tool_execution":
        handleToolExecution(event);
        break;
      case "critic_decision":
        handleCriticDecision(event);
        break;
      case "pipeline_flow":
        handlePipelineFlow(event);
        break;
      case "stage_transition":
        handleStageTransition(event);
        break;
    }

    // Always append to event log
    appendToEventLog(event);
  }
}
```

### Step 2: Implement Category Handlers

```typescript
function handleAgentLifecycle(event: UnifiedEvent) {
  // Extract agent name from payload
  const agentName = event.payload.agent || extractAgentFromEventType(event.event_type);

  // Determine status from event_type
  const isStarted = event.event_type.endsWith(".started");
  const isCompleted = event.event_type.endsWith(".completed") ||
                      event.event_type.endsWith(".plan_created") ||
                      event.event_type.endsWith(".decision");

  const status = isStarted ? "running" : isCompleted ? "completed" : "unknown";

  // Update UI state
  agentStatusStore.update(agentName, {
    status,
    timestamp: event.timestamp,
    lastEventId: event.event_id,
    ...event.payload
  });
}

function handleToolExecution(event: UnifiedEvent) {
  const toolName = event.payload.tool_name || event.payload.tool;

  if (event.event_type === "executor.tool_started") {
    toolTimelineStore.addExecution({
      toolName,
      startTime: event.timestamp_ms,
      status: "running",
      eventId: event.event_id,
      params: event.payload.params,
    });
  } else if (event.event_type === "executor.tool_completed") {
    toolTimelineStore.completeExecution(event.event_id, {
      endTime: event.timestamp_ms,
      status: event.payload.status,
      executionTime: event.payload.execution_time_ms,
      error: event.payload.error,
    });
  }
}

function handleCriticDecision(event: UnifiedEvent) {
  criticPanelStore.setDecision({
    action: event.payload.action,
    confidence: event.payload.confidence,
    issue: event.payload.issue,
    feedback: event.payload.feedback,
    timestamp: event.timestamp,
  });
}

function handleStageTransition(event: UnifiedEvent) {
  stageProgressStore.update({
    fromStage: event.payload.from_stage,
    toStage: event.payload.to_stage,
    satisfiedGoals: event.payload.satisfied_goals,
    remainingGoals: event.payload.remaining_goals,
    timestamp: event.timestamp,
  });
}

function handlePipelineFlow(event: UnifiedEvent) {
  if (event.event_type === "orchestrator.started") {
    overallStatusStore.setState("running");
  } else if (event.event_type === "orchestrator.completed") {
    overallStatusStore.setState("completed");
  } else if (event.event_type === "orchestrator.error") {
    overallStatusStore.setState("error", event.payload.error);
  }
}
```

### Step 3: Add Event Log Component

```typescript
interface EventLogEntry {
  event_id: string;
  timestamp: string;
  event_type: string;
  category: string;
  severity: string;
  summary: string;
}

function EventLog() {
  const [events, setEvents] = useState<EventLogEntry[]>([]);
  const [filter, setFilter] = useState<EventCategory | "all">("all");

  function appendToEventLog(event: UnifiedEvent) {
    setEvents(prev => [...prev, {
      event_id: event.event_id,
      timestamp: event.timestamp,
      event_type: event.event_type,
      category: event.category,
      severity: event.severity,
      summary: generateEventSummary(event),
    }].slice(-100)); // Keep last 100 events
  }

  const filteredEvents = filter === "all"
    ? events
    : events.filter(e => e.category === filter);

  return (
    <div className="event-log">
      <FilterBar value={filter} onChange={setFilter} />
      <div className="events">
        {filteredEvents.map(event => (
          <EventLogItem key={event.event_id} event={event} />
        ))}
      </div>
    </div>
  );
}
```

### Step 4: Utility Functions

```typescript
function extractAgentFromEventType(eventType: string): string {
  // "planner.started" → "planner"
  return eventType.split('.')[0];
}

function generateEventSummary(event: UnifiedEvent): string {
  switch (event.event_type) {
    case "agent.started":
    case "perception.started":
    case "intent.started":
    case "planner.started":
    case "executor.started":
    case "synthesizer.started":
    case "critic.started":
    case "integration.started":
      return `${event.payload.agent} agent started`;

    case "planner.plan_created":
      return `Plan created: ${event.payload.intent || "analyzing code"}`;

    case "executor.tool_started":
      return `Tool ${event.payload.tool_name} started`;

    case "executor.tool_completed":
      return `Tool ${event.payload.tool_name} completed (${event.payload.status})`;

    case "critic.decision":
      return `Critic decision: ${event.payload.action} (${(event.payload.confidence * 100).toFixed(0)}% confidence)`;

    default:
      return event.event_type;
  }
}
```

---

## Migration Checklist

- [ ] Update WebSocket message handler to check for `message.type === "event"`
- [ ] Add TypeScript interfaces for UnifiedEvent and related types
- [ ] Implement category-based event routing
- [ ] Update agent status display to use new event structure
- [ ] Update tool timeline to use new event structure
- [ ] Update critic decision panel to use new event structure
- [ ] Update stage progress indicator to use new event structure
- [ ] Update overall status display to use new event structure
- [ ] Add event log component with filtering
- [ ] Update any event listeners/subscriptions to new format
- [ ] Test with live WebSocket connection
- [ ] Remove legacy event handling code

---

## Testing

### Manual Testing

1. Connect to WebSocket endpoint
2. Trigger a code analysis query
3. Verify all events conform to UnifiedEvent schema
4. Verify UI updates correctly for each event category
5. Verify timestamp consistency (both ISO and milliseconds)
6. Verify event filtering by category works
7. Verify event severity is displayed correctly

### Example Test Events

You can simulate events locally for testing:

```typescript
const testEvents: UnifiedEvent[] = [
  {
    type: "event",
    event_id: "test-001",
    event_type: "perception.started",
    category: "agent_lifecycle",
    timestamp: new Date().toISOString(),
    timestamp_ms: Date.now(),
    session_id: "test-session",
    request_id: "test-request",
    payload: { agent: "perception" },
    severity: "info",
    source: "test",
  },
  {
    type: "event",
    event_id: "test-002",
    event_type: "planner.plan_created",
    category: "agent_lifecycle",
    timestamp: new Date().toISOString(),
    timestamp_ms: Date.now(),
    session_id: "test-session",
    request_id: "test-request",
    payload: {
      agent: "planner",
      intent: "Find authentication flow",
      confidence: 0.95,
      tools: ["locate", "read_code", "grep_search"],
      step_count: 3,
    },
    severity: "info",
    source: "test",
  },
  // Add more test events...
];
```

---

## Benefits of UnifiedEvent Schema

1. **Standardized Timestamps**: Both ISO 8601 and epoch milliseconds provided
2. **Category-Based Routing**: Efficient event handling via category discrimination
3. **Severity Filtering**: Show only errors, warnings, or info events
4. **Event Correlation**: `event_id`, `session_id`, `request_id` for tracking
5. **Source Tracking**: Know which component emitted each event
6. **Backward Compatible**: Old subscriptions still work, just different payload structure

---

## Support

For questions or issues:
- Backend: Check [jeeves_protocols/events.py](jeeves-core/jeeves_protocols/events.py) for canonical schema
- Event Bridge: See [event_bridge.py](jeeves-core/jeeves_mission_system/orchestrator/event_bridge.py)
- WebSocket Handler: See [websocket.py](jeeves-core/jeeves_avionics/gateway/websocket.py)

---

**End of Migration Guide**
