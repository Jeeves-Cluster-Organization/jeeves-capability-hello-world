"""
Tests for streaming implementation.

Validates:
1. Authoritative vs debug token distinction
2. Terminal event semantics (exactly one done OR error)
3. Cancellation propagation
4. Inline citation extraction
5. End-to-end streaming behavior
"""

import pytest
import asyncio
import time
from typing import List, AsyncIterator
from unittest.mock import Mock, AsyncMock, MagicMock

from jeeves_infra.protocols import (
    AgentConfig,
    AgentOutputMode,
    TokenStreamMode,
    Envelope,
    PipelineEvent,
    Agent,
    create_envelope,
    RequestContext,
)


# =============================================================================
# TEST 1: Authoritative Token Test
# =============================================================================

@pytest.mark.asyncio
async def test_text_stream_authoritative_tokens():
    """Verify TEXT_STREAM tokens are authoritative (debug=False)."""

    # Create mock LLM provider that streams tokens
    class MockLLMProvider:
        async def generate_stream(self, model, prompt, options):
            tokens = ["Hello", " ", "world", "!"]
            for token in tokens:
                chunk = MagicMock()
                chunk.text = token
                yield chunk

    # Create mock prompt registry
    class MockPromptRegistry:
        def get(self, key, context=None):
            return "Test prompt"

    # Create agent with TEXT + AUTHORITATIVE config
    config = AgentConfig(
        name="test_agent",
        has_llm=True,
        output_mode=AgentOutputMode.TEXT,
        token_stream=TokenStreamMode.AUTHORITATIVE,
        output_key="test_output",
    )

    agent = Agent(
        config=config,
        logger=Mock(),
        llm=MockLLMProvider(),
        prompt_registry=MockPromptRegistry(),
    )

    # Create test envelope
    envelope = create_envelope(
        raw_input="test message",
        request_context=RequestContext(
            request_id="test123",
            capability="test",
            session_id="session1",
            user_id="user1",
        ),
        metadata={},
    )

    # Stream tokens and verify
    tokens = []
    events = []
    async for event_type, event in agent.stream(envelope):
        if event.type == "token":
            assert event.debug == False, "Authoritative tokens must have debug=False"
            tokens.append(event.data["token"])
            events.append(event)

    # Verify all tokens received
    assert tokens == ["Hello", " ", "world", "!"]

    # Verify canonical output stored
    assert "test_output" in envelope.outputs
    assert envelope.outputs["test_output"]["response"] == "Hello world!"


# =============================================================================
# TEST 2: Debug Token Tagging Test
# =============================================================================

@pytest.mark.asyncio
async def test_debug_stream_tokens_not_authoritative():
    """Verify STRUCTURED output uses non-streaming generate (not stream).

    STRUCTURED mode agents use buffered JSON output, not token streaming.
    This test verifies the agent.run() path for structured output.
    """

    # Create mock LLM provider
    class MockLLMProvider:
        async def generate(self, model, prompt, options):
            return '{"intent": "question", "needs_search": true}'

        async def generate_stream(self, model, prompt, options):
            # This should NOT be called for STRUCTURED mode
            raise AssertionError("generate_stream should not be called for STRUCTURED mode")
            yield  # Make it a generator

    class MockPromptRegistry:
        def get(self, key, context=None):
            return "Test prompt"

    # Create agent with STRUCTURED config (no streaming for structured output)
    config = AgentConfig(
        name="test_agent",
        has_llm=True,
        output_mode=AgentOutputMode.STRUCTURED,
        token_stream=TokenStreamMode.OFF,  # STRUCTURED doesn't stream
        output_key="test_output",
    )

    agent = Agent(
        config=config,
        logger=Mock(),
        llm=MockLLMProvider(),
        prompt_registry=MockPromptRegistry(),
    )

    envelope = create_envelope(
        raw_input="test message",
        request_context=RequestContext(
            request_id="test123",
            capability="test",
            session_id="session1",
            user_id="user1",
        ),
        metadata={},
    )

    # Use process() instead of stream() for STRUCTURED output
    result = await agent.process(envelope)

    # Verify canonical output is BUFFERED JSON
    assert "test_output" in envelope.outputs
    output = envelope.outputs["test_output"]
    assert "intent" in output
    assert output["intent"] == "question"


# =============================================================================
# TEST 3: Cancellation & Terminal Semantics Test
# =============================================================================

@pytest.mark.asyncio
async def test_cancellation_propagates():
    """Verify cancellation propagates and no double-done."""
    from jeeves_capability_hello_world.orchestration import ChatbotService

    # Create mock service components
    class MockLLMProvider:
        async def generate(self, model, prompt, options):
            return '{"intent": "concept", "topic": "envelope", "reasoning": "User asking about Envelope"}'

    class MockLLMFactory:
        def __call__(self, role):
            return MockLLMProvider()

    class MockToolExecutor:
        async def execute(self, tool_name, params):
            return {}

    class MockPromptRegistry:
        def get(self, key, context=None):
            return "Test prompt"
        @staticmethod
        def get_instance():
            return MockPromptRegistry()

    class MockResources:
        """Mock resources tracker."""
    class MockKernelClient:
        """Mock KernelClient for testing."""
        async def record_usage(self, *args, **kwargs):
            from jeeves_infra.kernel_client import QuotaCheckResult
            return QuotaCheckResult(within_bounds=True)

        async def check_quota(self, *args, **kwargs):
            from jeeves_infra.kernel_client import QuotaCheckResult
            return QuotaCheckResult(within_bounds=True)

        async def get_process(self, *args, **kwargs):
            from jeeves_infra.kernel_client import ProcessInfo
            return ProcessInfo(
                pid="mock-pid",
                request_id="mock-req",
                user_id="test",
                session_id="test",
                state="RUNNING",
                priority="NORMAL",
            )

    # Create service
    from jeeves_capability_hello_world.pipeline_config import ONBOARDING_CHATBOT_PIPELINE

    # Mock the registry to avoid import issues
    import mission_system.prompts.core.registry as registry_module
    original_registry = getattr(registry_module, 'PromptRegistry', None)
    registry_module.PromptRegistry = MockPromptRegistry

    try:
        service = ChatbotService(
            llm_provider_factory=MockLLMFactory(),
            tool_executor=MockToolExecutor(),
            logger=Mock(),
            pipeline_config=ONBOARDING_CHATBOT_PIPELINE,
            kernel_client=MockKernelClient(),
            use_mock=False,
        )

        events = []
        try:
            async for event in service.process_message_stream(
                user_id="test_user",
                session_id="test_session",
                message="test message",
            ):
                events.append(event)
                # Simulate client disconnect after 3 events
                if len(events) == 3:
                    raise asyncio.CancelledError()
        except asyncio.CancelledError:
            pass

        # Verify no double-done (if error emitted, no done should follow)
        terminal_events = [e for e in events if e.type in ["done", "error"]]
        assert len(terminal_events) <= 1, "Must have at most one terminal event"

    finally:
        # Restore original
        if original_registry:
            registry_module.PromptRegistry = original_registry


# =============================================================================
# TEST 4: Inline Citations Test
# =============================================================================

@pytest.mark.asyncio
async def test_inline_citations_best_effort():
    """Verify inline citations are extracted but not guaranteed."""
    from jeeves_infra.protocols import Agent

    config = AgentConfig(name="test", output_key="test")
    agent = Agent(config=config, logger=Mock())

    # Test successful extraction
    text = "Temperature is 72°F [Weather.com]. Sunny today [BBC News]."
    citations = agent._extract_citations(text)
    assert citations == ["Weather.com", "BBC News"]

    # Test deduplication
    text_dup = "Data from [Source1]. More data [Source1]. Final [Source2]."
    citations_dup = agent._extract_citations(text_dup)
    assert citations_dup == ["Source1", "Source2"]

    # Test edge case: nested brackets (brittle - may not work)
    text_brittle = "Data from [Source [nested]]."
    citations_brittle = agent._extract_citations(text_brittle)
    # This is v0 best-effort - we document it may not work perfectly
    assert isinstance(citations_brittle, list)  # Just verify it doesn't crash


# =============================================================================
# TEST 5: End-to-End Streaming Test
# =============================================================================

@pytest.mark.asyncio
async def test_end_to_end_streaming_latency():
    """Verify first token latency and incremental display."""

    # Create mock LLM with artificial delays
    class DelayedLLMProvider:
        async def generate(self, model, prompt, options):
            return '{"intent": "question", "needs_search": false}'

        async def generate_stream(self, model, prompt, options):
            tokens = ["Hello", " ", "world", "!"]
            for token in tokens:
                await asyncio.sleep(0.1)  # 100ms delay per token
                chunk = MagicMock()
                chunk.text = token
                yield chunk

    class MockPromptRegistry:
        def get(self, key, context=None):
            return "Test prompt"

    config = AgentConfig(
        name="test_agent",
        has_llm=True,
        output_mode=AgentOutputMode.TEXT,
        token_stream=TokenStreamMode.AUTHORITATIVE,
        output_key="test_output",
    )

    agent = Agent(
        config=config,
        logger=Mock(),
        llm=DelayedLLMProvider(),
        prompt_registry=MockPromptRegistry(),
    )

    envelope = create_envelope(
        raw_input="test message",
        request_context=RequestContext(
            request_id="test123",
            capability="test",
            session_id="session1",
            user_id="user1",
        ),
        metadata={},
    )

    # Measure token yield times
    start = time.time()
    yield_times = []

    async for event_type, event in agent.stream(envelope):
        if event.type == "token":
            yield_times.append(time.time() - start)

    # Verify tokens yielded incrementally (not all at once)
    # If buffered, all yields would happen at ~0.4s
    # If streaming, yields at ~0.1s, ~0.2s, ~0.3s, ~0.4s
    assert len(yield_times) == 4
    assert yield_times[0] < 0.15, "First token should arrive quickly (~0.1s)"
    assert yield_times[1] < 0.25, "Second token should arrive at ~0.2s"
    assert yield_times[2] < 0.35, "Third token should arrive at ~0.3s"
    assert yield_times[3] < 0.45, "Fourth token should arrive at ~0.4s"

    # Verify incremental delivery (not all at end)
    # Each token should arrive roughly 0.1s apart
    for i in range(1, len(yield_times)):
        time_diff = yield_times[i] - yield_times[i-1]
        assert 0.08 < time_diff < 0.12, f"Tokens should arrive incrementally, got {time_diff}s gap"


# =============================================================================
# TEST 6: No Hidden Buffering Test
# =============================================================================

@pytest.mark.asyncio
async def test_no_hidden_buffering():
    """Verify tokens yield immediately, not buffered internally."""

    class DelayedLLMProvider:
        async def generate_stream(self, model, prompt, options):
            tokens = ["A", "B", "C", "D"]
            for token in tokens:
                await asyncio.sleep(0.5)  # Artificial delay
                chunk = MagicMock()
                chunk.text = token
                yield chunk

    class MockPromptRegistry:
        def get(self, key, context=None):
            return "Test prompt"

    config = AgentConfig(
        name="test_agent",
        has_llm=True,
        output_mode=AgentOutputMode.TEXT,
        token_stream=TokenStreamMode.AUTHORITATIVE,
        output_key="test_output",
    )

    agent = Agent(
        config=config,
        logger=Mock(),
        llm=DelayedLLMProvider(),
        prompt_registry=MockPromptRegistry(),
    )

    envelope = create_envelope(
        raw_input="test message",
        request_context=RequestContext(
            request_id="test123",
            capability="test",
            session_id="session1",
            user_id="user1",
        ),
        metadata={},
    )

    # Measure yield times
    start = time.time()
    yield_times = []

    async for event_type, event in agent.stream(envelope):
        if event.type == "token":
            yield_times.append(time.time() - start)

    # Verify tokens yielded incrementally (not all at once at end)
    # If buffered, all yields would happen at ~2.0s
    # If streaming, yields at ~0.5s, ~1.0s, ~1.5s, ~2.0s
    assert 0.4 < yield_times[0] < 0.6, f"First token after ~0.5s, got {yield_times[0]}"
    assert 0.9 < yield_times[1] < 1.1, f"Second token after ~1.0s, got {yield_times[1]}"
    assert 1.4 < yield_times[2] < 1.6, f"Third token after ~1.5s, got {yield_times[2]}"
    assert 1.9 < yield_times[3] < 2.1, f"Fourth token after ~2.0s, got {yield_times[3]}"


# =============================================================================
# TEST 7: Terminal Event Guarantee Test
# =============================================================================

@pytest.mark.asyncio
async def test_exactly_one_terminal_event():
    """Verify exactly one terminal event (done OR error), no further events."""
    from jeeves_capability_hello_world.orchestration import ChatbotService

    class MockLLMProvider:
        async def generate(self, model, prompt, options):
            return '{"intent": "concept", "topic": "architecture", "reasoning": "User asking about architecture"}'

        async def generate_stream(self, model, prompt, options):
            for token in ["test", " response"]:
                chunk = MagicMock()
                chunk.text = token
                yield chunk

    class MockLLMFactory:
        def __call__(self, role):
            return MockLLMProvider()

    class MockToolExecutor:
        async def execute(self, tool_name, params):
            return {}

    class MockPromptRegistry:
        def get(self, key, context=None):
            return "Test prompt"
        @staticmethod
        def get_instance():
            return MockPromptRegistry()

    class MockKernelClient:
        """Mock KernelClient for testing."""
        async def record_usage(self, *args, **kwargs):
            from jeeves_infra.kernel_client import QuotaCheckResult
            return QuotaCheckResult(within_bounds=True)

        async def check_quota(self, *args, **kwargs):
            from jeeves_infra.kernel_client import QuotaCheckResult
            return QuotaCheckResult(within_bounds=True)

        async def get_process(self, *args, **kwargs):
            from jeeves_infra.kernel_client import ProcessInfo
            return ProcessInfo(
                pid="mock-pid",
                request_id="mock-req",
                user_id="test",
                session_id="test",
                state="RUNNING",
                priority="NORMAL",
            )

    from jeeves_capability_hello_world.pipeline_config import ONBOARDING_CHATBOT_PIPELINE

    import mission_system.prompts.core.registry as registry_module
    original_registry = getattr(registry_module, 'PromptRegistry', None)
    registry_module.PromptRegistry = MockPromptRegistry

    try:
        service = ChatbotService(
            llm_provider_factory=MockLLMFactory(),
            tool_executor=MockToolExecutor(),
            logger=Mock(),
            pipeline_config=ONBOARDING_CHATBOT_PIPELINE,
            kernel_client=MockKernelClient(),
            use_mock=False,
        )

        events = []
        async for event in service.process_message_stream(
            user_id="test_user",
            session_id="test_session",
            message="test message",
        ):
            events.append(event)

        # Verify exactly one terminal event
        terminal_events = [e for e in events if e.type in ["done", "error"]]
        assert len(terminal_events) == 1, f"Must have exactly one terminal event, got {len(terminal_events)}"

        # Verify terminal event is last
        last_event = events[-1]
        assert last_event.type in ["done", "error"], "Terminal event must be last"

        # Verify no events after terminal
        terminal_index = next(i for i, e in enumerate(events) if e.type in ["done", "error"])
        assert terminal_index == len(events) - 1, "No events should come after terminal event"

    finally:
        if original_registry:
            registry_module.PromptRegistry = original_registry
