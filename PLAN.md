# Plan: Migrate to Onboarding Chatbot

## Goal
Transform jeeves-capability-hello-world from a generic chatbot into an **onboarding assistant** that explains the Jeeves ecosystem (jeeves-core, jeeves-infra, mission_system).

## Approach
- **Knowledge source**: Embed key docs into system prompts (simple, fast, offline)
- **Scope**: Ecosystem overview (high-level architecture explanations)

---

## Files to Modify

### 1. NEW: Knowledge Base Module
**File**: `jeeves_capability_hello_world/prompts/knowledge_base.py`

```python
"""Embedded knowledge about the Jeeves ecosystem for onboarding."""

ECOSYSTEM_OVERVIEW = """
## The Jeeves Ecosystem

Jeeves is a multi-layered AI agent orchestration system:

### Layer 1: jeeves-core (Go Micro-Kernel)
- Pipeline orchestration engine
- Envelope state management (immutable state transitions)
- Resource quotas (iterations, LLM calls, agent hops)
- Circuit breakers for fault tolerance
- gRPC services for Python layer communication

### Layer 2: jeeves-infra (Python Infrastructure)
- LLM providers (OpenAI, Anthropic, llama.cpp)
- Database clients (PostgreSQL, pgvector)
- Protocols and type definitions
- Gateway (HTTP/WebSocket/gRPC translation)

### Layer 3: mission_system (Python Orchestration Framework)
- Agent profiles and configuration
- Adapters for capabilities (Constitution R7 compliance)
- Prompt registry and management
- Event handling and orchestration

### Layer 4: Capabilities (Python User Space)
- Domain-specific prompts
- Custom tools
- Pipeline configuration
- Service layer (e.g., ChatbotService)
"""

KEY_CONCEPTS = """
## Key Concepts

### Envelope
The state container that flows through the pipeline:
- envelope_id: Unique identifier
- task: The user's request
- current_stage: Which agent is processing
- outputs: Results from each agent

### AgentConfig
Declarative agent definition:
- name: Agent identifier
- has_llm: Whether agent uses LLM
- has_tools: Whether agent can execute tools
- prompt_key: Which prompt to use
- output_key: Where to store results

### Constitution R7 (Import Boundaries)
Capabilities MUST use adapters, not import infrastructure directly:
- CORRECT: from mission_system.adapters import create_llm_provider_factory
- WRONG: from avionics.llm import LLMProvider

### Pipeline Pattern
Understand → Think → Respond
- Understand: LLM classifies intent
- Think: Tool execution (no LLM)
- Respond: LLM generates response
"""

HELLO_WORLD_STRUCTURE = """
## Hello World Structure

jeeves-capability-hello-world/
├── gradio_app.py                    # Entry point - Gradio web UI
├── jeeves_capability_hello_world/   # Main capability package
│   ├── pipeline_config.py           # 3-agent pipeline configuration
│   ├── prompts/chatbot/             # LLM prompts
│   │   ├── understand.py            # Intent classification
│   │   └── respond.py               # Response synthesis
│   ├── tools/                       # Available tools
│   │   └── hello_world_tools.py     # get_time, list_tools
│   └── orchestration/               # Service layer
│       └── chatbot_service.py       # Pipeline execution wrapper
├── jeeves-core/                     # Go micro-kernel (submodule)
└── jeeves-airframe/                 # Python infrastructure (submodule)
"""

def get_onboarding_context() -> str:
    """Get full onboarding context for prompts."""
    return f"{ECOSYSTEM_OVERVIEW}\n\n{KEY_CONCEPTS}\n\n{HELLO_WORLD_STRUCTURE}"
```

### 2. Update Understand Prompt
**File**: `jeeves_capability_hello_world/prompts/chatbot/understand.py`

Changes:
- Remove web search logic (not needed for embedded knowledge)
- Add onboarding-specific intent categories
- Simplify decision making

**New intents**:
- `architecture` - Questions about layers, connections
- `concept` - Questions about Envelope, AgentConfig, etc.
- `getting_started` - Setup, running, customization
- `component` - Questions about jeeves-core, jeeves-infra, etc.
- `general` - Greetings, off-topic

**Key changes** (lines 19-126):
```python
def chatbot_understand() -> str:
    return """You are an onboarding assistant for the Jeeves AI agent ecosystem.

## User Message
{user_message}

## Recent Conversation
{conversation_history}

## Your Role
Help newcomers understand:
- The Jeeves ecosystem architecture (jeeves-core, jeeves-infra, mission_system)
- Key concepts (Envelope, AgentConfig, Constitution R7)
- How to get started with hello-world
- How the 3-agent pipeline works

## Task
Classify the user's question:

## Output Format (JSON only)
{{
  "intent": "<architecture|concept|getting_started|component|general>",
  "topic": "<specific topic if identifiable>",
  "reasoning": "<why you classified this way>"
}}

## Intent Categories

- **architecture**: Questions about layers, how things connect
  Examples: "How do the layers work?", "What's the architecture?"

- **concept**: Questions about specific concepts
  Examples: "What is an Envelope?", "Explain AgentConfig"

- **getting_started**: Setup and usage questions
  Examples: "How do I run this?", "How do I add a tool?"

- **component**: Questions about specific components
  Examples: "What is jeeves-core?", "What does mission_system do?"

- **general**: Greetings, thanks, off-topic
  Examples: "Hello", "Thanks!", "What's the weather?"

Now classify:
"""
```

### 3. Update Respond Prompt
**File**: `jeeves_capability_hello_world/prompts/chatbot/respond.py`

Changes:
- Inject knowledge base context
- Remove search results handling
- Add onboarding-focused guidelines

**Key changes** (lines 20-156):
```python
from jeeves_capability_hello_world.prompts.knowledge_base import get_onboarding_context

def chatbot_respond() -> str:
    knowledge = get_onboarding_context()
    return f"""You are an onboarding assistant for the Jeeves AI agent ecosystem.

## Knowledge Base
{knowledge}

## Recent Conversation
{{conversation_history}}

## Current Question
{{user_message}}

## Intent
{{intent}}

## Task
Answer the user's question about the Jeeves ecosystem using ONLY the knowledge above.

## Output Format (JSON only)
{{{{
  "response": "<your helpful response>",
  "citations": [],
  "confidence": "<high|medium|low>"
}}}}

## Guidelines
1. Answer from the knowledge base above
2. Be concise but complete (2-4 sentences)
3. Use code examples when helpful
4. Admit if something isn't covered in the knowledge base
5. For off-topic questions, gently redirect to Jeeves topics

## Example Responses

Question: "What is jeeves-core?"
Response: "jeeves-core is the Go micro-kernel at the foundation of Jeeves. It handles pipeline orchestration, envelope state management, resource quotas, and provides gRPC services for the Python layer."

Question: "How do I add a tool?"
Response: "To add a tool: 1) Implement your function in tools/hello_world_tools.py, 2) Register it in capability/wiring.py with catalog.register(). Tools can be sync or async and should return a dict with status and results."

Now respond:
"""
```

### 4. Update Streaming Respond Prompt
**File**: `jeeves_capability_hello_world/prompts/chatbot/respond_streaming.py`

Same changes as respond.py but for streaming format (plain text output).

### 5. Update Pipeline Config
**File**: `jeeves_capability_hello_world/pipeline_config.py`

Changes:
- Rename pipeline: `general_chatbot` → `onboarding_chatbot`
- Update system identity in hooks
- Optional: Remove tool execution since we don't need web search

**Line 56-61** (understand_pre_process):
```python
context = {
    "user_message": user_message,
    "conversation_history": formatted_history,
    "system_identity": "Jeeves Onboarding Assistant",
    "capabilities": "ecosystem explanation, concept clarification, getting started help",
}
```

**Line 227** (pipeline name):
```python
ONBOARDING_CHATBOT_PIPELINE = PipelineConfig(
    name="onboarding_chatbot",
    ...
)
```

**Line 303-306** (mode registry):
```python
PIPELINE_MODES = {
    "onboarding_chatbot": ONBOARDING_CHATBOT_PIPELINE,
    "hello_world": ONBOARDING_CHATBOT_PIPELINE,  # Alias
}
```

### 6. Update/Remove Tools
**File**: `jeeves_capability_hello_world/tools/hello_world_tools.py`

Options:
- **Option A**: Remove web_search, keep get_time and list_tools as examples
- **Option B**: Keep all tools but update list_tools to describe onboarding capabilities

Recommend **Option A** - cleaner for onboarding focus.

**Changes**:
- Remove `web_search` function (lines 19-82)
- Update `list_tools` to reflect onboarding focus (lines 134-168)
- Update `__all__` (lines 184-189)

### 7. Update Tool Registration
**File**: `jeeves_capability_hello_world/capability/wiring.py`

Remove web_search registration if removed from tools.

---

## Test Changes

### 8. Update Streaming Tests
**File**: `jeeves_capability_hello_world/tests/test_streaming.py`

Changes needed:
- Update mock LLM responses to return onboarding-style JSON
- Test 3 (line 159): Update mock to not reference web search
- Test 7 (line 420): Update mock to return onboarding intents

**Example change** (test_cancellation_propagates, line 165):
```python
async def generate(self, model, prompt, options):
    return '{"intent": "concept", "topic": "envelope", "reasoning": "User asking about Envelope"}'
```

### 9. Update Integration Tests
**File**: `tests/integration/test_agent_pipeline.py`

Changes:
- Update intent test cases (line 70-75) for onboarding intents
- Update query examples to be onboarding-focused

**Example change** (line 70-75):
```python
test_cases = [
    ("What is the architecture?", "architecture"),
    ("Explain the Envelope concept", "concept"),
    ("How do I run this?", "getting_started"),
    ("What does jeeves-core do?", "component"),
]
```

### 10. Add New Tests
**File**: `jeeves_capability_hello_world/tests/test_onboarding.py` (NEW)

```python
"""Tests for onboarding chatbot functionality."""

import pytest
from jeeves_capability_hello_world.prompts.knowledge_base import (
    ECOSYSTEM_OVERVIEW,
    KEY_CONCEPTS,
    get_onboarding_context,
)

class TestKnowledgeBase:
    """Tests for embedded knowledge base."""

    def test_ecosystem_overview_contains_layers(self):
        """Verify all layers are documented."""
        assert "jeeves-core" in ECOSYSTEM_OVERVIEW
        assert "jeeves-infra" in ECOSYSTEM_OVERVIEW
        assert "mission_system" in ECOSYSTEM_OVERVIEW
        assert "Capabilities" in ECOSYSTEM_OVERVIEW

    def test_key_concepts_contains_required(self):
        """Verify key concepts are documented."""
        assert "Envelope" in KEY_CONCEPTS
        assert "AgentConfig" in KEY_CONCEPTS
        assert "Constitution R7" in KEY_CONCEPTS

    def test_get_onboarding_context_combines_all(self):
        """Verify context includes all sections."""
        context = get_onboarding_context()
        assert "Jeeves Ecosystem" in context
        assert "Key Concepts" in context
        assert "Hello World Structure" in context

class TestOnboardingIntents:
    """Tests for intent classification."""

    @pytest.mark.parametrize("query,expected_intent", [
        ("What is the architecture?", "architecture"),
        ("What is an Envelope?", "concept"),
        ("How do I run this?", "getting_started"),
        ("What is jeeves-core?", "component"),
        ("Hello!", "general"),
    ])
    def test_intent_categories_exist(self, query, expected_intent):
        """Verify intent categories are valid."""
        valid_intents = ["architecture", "concept", "getting_started", "component", "general"]
        assert expected_intent in valid_intents
```

---

## Verification Steps

### Manual Testing
1. Run: `python gradio_app.py`
2. Test questions:
   - "What is jeeves-core?" → Should explain Go micro-kernel
   - "How do the layers connect?" → Should describe architecture
   - "What is an Envelope?" → Should explain state container
   - "How do I add a new tool?" → Should give step-by-step
   - "What is Constitution R7?" → Should explain import boundaries
   - "Hello" → Should greet and offer help

### Automated Testing
```bash
# Run all tests
pytest

# Run onboarding-specific tests
pytest jeeves_capability_hello_world/tests/test_onboarding.py -v

# Run streaming tests
pytest jeeves_capability_hello_world/tests/test_streaming.py -v

# Run integration tests
pytest tests/integration/ -v
```

---

## Implementation Order

1. Create `prompts/knowledge_base.py` (new file)
2. Update `prompts/chatbot/understand.py`
3. Update `prompts/chatbot/respond.py`
4. Update `prompts/chatbot/respond_streaming.py`
5. Update `pipeline_config.py`
6. Update `tools/hello_world_tools.py` (remove web_search)
7. Update `capability/wiring.py` (remove web_search registration)
8. Create `tests/test_onboarding.py` (new file)
9. Update `tests/test_streaming.py`
10. Update `tests/integration/test_agent_pipeline.py`
11. Run tests and verify
12. Manual testing via Gradio UI

---

## Out of Scope
- RAG with embeddings (user chose embedded context)
- Code navigation (user chose overview scope)
- External documentation fetching
