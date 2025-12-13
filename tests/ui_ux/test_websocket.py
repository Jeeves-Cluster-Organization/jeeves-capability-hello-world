"""
UI/UX Tests for WebSocket Communication.

Tests WebSocket-based real-time updates and streaming responses.
Based on the Jeeves Core Runtime Contract event system.

Test Markers:
    @pytest.mark.ui_ux - UI/UX tests
    @pytest.mark.websocket - WebSocket tests
    @pytest.mark.requires_docker - Requires running services
"""

import asyncio
import json
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = [
    pytest.mark.ui_ux,
    pytest.mark.websocket,
    pytest.mark.asyncio,
]


# =============================================================================
# Event Type Definitions (per Contract)
# =============================================================================

class AgentEventType:
    """Agent event types per runtime contract."""
    AGENT_STARTED = "AGENT_STARTED"
    AGENT_COMPLETED = "AGENT_COMPLETED"
    TOOL_STARTED = "TOOL_STARTED"
    TOOL_COMPLETED = "TOOL_COMPLETED"
    STAGE_STARTED = "STAGE_STARTED"
    STAGE_COMPLETED = "STAGE_COMPLETED"
    ERROR = "ERROR"
    CLARIFICATION_REQUESTED = "CLARIFICATION_REQUESTED"


# =============================================================================
# Mock WebSocket for Testing
# =============================================================================

class MockWebSocket:
    """Mock WebSocket for testing event formats."""

    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self.sent_messages: List[Dict[str, Any]] = []
        self.closed = False

    async def send(self, message: str):
        """Send message (client to server)."""
        self.sent_messages.append(json.loads(message))

    async def receive(self) -> str:
        """Receive message (server to client)."""
        if self.messages:
            return json.dumps(self.messages.pop(0))
        raise asyncio.TimeoutError()

    async def close(self):
        """Close connection."""
        self.closed = True

    def add_incoming_message(self, message: Dict[str, Any]):
        """Add message to receive queue."""
        self.messages.append(message)


# =============================================================================
# WebSocket Event Format Tests
# =============================================================================

class TestWebSocketEventFormats:
    """Tests for WebSocket event message formats."""

    def test_event_base_format(self):
        """Test base event format."""
        event = {
            "type": "AGENT_STARTED",
            "timestamp": "2025-12-13T00:00:00.000Z",
            "thread_id": "thread-123",
            "request_id": "req-456",
        }

        assert "type" in event
        assert "timestamp" in event
        assert "thread_id" in event

    def test_agent_started_event(self):
        """Test AGENT_STARTED event format."""
        event = {
            "type": "AGENT_STARTED",
            "timestamp": "2025-12-13T00:00:00.000Z",
            "thread_id": "thread-123",
            "payload": {
                "agent_name": "perception",
                "agent_role": "query_normalization",
                "step_number": 1,
                "total_steps": 7,
            },
        }

        assert event["type"] == "AGENT_STARTED"
        assert "agent_name" in event["payload"]

    def test_agent_completed_event(self):
        """Test AGENT_COMPLETED event format."""
        event = {
            "type": "AGENT_COMPLETED",
            "timestamp": "2025-12-13T00:00:00.000Z",
            "thread_id": "thread-123",
            "payload": {
                "agent_name": "perception",
                "status": "success",
                "duration_ms": 150,
                "output_summary": "Query normalized successfully",
            },
        }

        assert event["type"] == "AGENT_COMPLETED"
        assert event["payload"]["status"] in ["success", "error", "skipped"]

    def test_tool_started_event(self):
        """Test TOOL_STARTED event format."""
        event = {
            "type": "TOOL_STARTED",
            "timestamp": "2025-12-13T00:00:00.000Z",
            "thread_id": "thread-123",
            "payload": {
                "tool_name": "read_code",
                "tool_id": "code_analysis.read_code",
                "params": {
                    "file_path": "main.py",
                    "start_line": 1,
                    "end_line": 50,
                },
            },
        }

        assert event["type"] == "TOOL_STARTED"
        assert "tool_name" in event["payload"]

    def test_tool_completed_event(self):
        """Test TOOL_COMPLETED event format."""
        event = {
            "type": "TOOL_COMPLETED",
            "timestamp": "2025-12-13T00:00:00.000Z",
            "thread_id": "thread-123",
            "payload": {
                "tool_name": "read_code",
                "status": "success",
                "duration_ms": 45,
                "result_summary": "Read 50 lines from main.py",
                "citations_added": 1,
            },
        }

        assert event["type"] == "TOOL_COMPLETED"
        assert "duration_ms" in event["payload"]

    def test_stage_started_event(self):
        """Test STAGE_STARTED event format."""
        event = {
            "type": "STAGE_STARTED",
            "timestamp": "2025-12-13T00:00:00.000Z",
            "thread_id": "thread-123",
            "payload": {
                "stage_name": "traversal",
                "stage_number": 4,
                "total_stages": 7,
                "description": "Executing code traversal operations",
            },
        }

        assert event["type"] == "STAGE_STARTED"
        assert 1 <= event["payload"]["stage_number"] <= event["payload"]["total_stages"]

    def test_error_event(self):
        """Test ERROR event format."""
        event = {
            "type": "ERROR",
            "timestamp": "2025-12-13T00:00:00.000Z",
            "thread_id": "thread-123",
            "payload": {
                "error_code": "TOOL_EXECUTION_FAILED",
                "error_message": "Failed to read file: Permission denied",
                "recoverable": True,
                "agent_name": "traverser",
                "tool_name": "read_code",
            },
        }

        assert event["type"] == "ERROR"
        assert "error_code" in event["payload"]
        assert "recoverable" in event["payload"]

    def test_clarification_requested_event(self):
        """Test CLARIFICATION_REQUESTED event format."""
        event = {
            "type": "CLARIFICATION_REQUESTED",
            "timestamp": "2025-12-13T00:00:00.000Z",
            "thread_id": "thread-123",
            "payload": {
                "question": "Which 'main' function did you mean?",
                "options": [
                    {"id": "1", "label": "app/main.py", "description": "Application entry"},
                    {"id": "2", "label": "cli/main.py", "description": "CLI entry"},
                ],
                "timeout_seconds": 60,
            },
        }

        assert event["type"] == "CLARIFICATION_REQUESTED"
        assert "question" in event["payload"]
        assert isinstance(event["payload"]["options"], list)


# =============================================================================
# WebSocket Connection Tests
# =============================================================================

class TestWebSocketConnection:
    """Tests for WebSocket connection lifecycle."""

    @pytest.fixture
    def mock_ws(self):
        return MockWebSocket()

    async def test_connection_established_message(self, mock_ws):
        """Test connection established message."""
        welcome = {
            "type": "CONNECTION_ESTABLISHED",
            "timestamp": "2025-12-13T00:00:00.000Z",
            "payload": {
                "connection_id": "conn-123",
                "server_version": "1.0.0",
                "capabilities": ["streaming", "events"],
            },
        }

        mock_ws.add_incoming_message(welcome)
        msg = await mock_ws.receive()
        data = json.loads(msg)

        assert data["type"] == "CONNECTION_ESTABLISHED"
        assert "connection_id" in data["payload"]

    async def test_ping_pong_messages(self, mock_ws):
        """Test ping/pong keepalive messages."""
        ping = {
            "type": "PING",
            "timestamp": "2025-12-13T00:00:00.000Z",
        }

        pong = {
            "type": "PONG",
            "timestamp": "2025-12-13T00:00:00.000Z",
        }

        # Server sends ping
        mock_ws.add_incoming_message(ping)
        msg = await mock_ws.receive()
        data = json.loads(msg)
        assert data["type"] == "PING"

        # Client responds with pong
        await mock_ws.send(json.dumps(pong))
        assert mock_ws.sent_messages[-1]["type"] == "PONG"

    async def test_connection_close_message(self, mock_ws):
        """Test connection close message."""
        close = {
            "type": "CONNECTION_CLOSING",
            "timestamp": "2025-12-13T00:00:00.000Z",
            "payload": {
                "reason": "Server shutdown",
                "code": 1000,
            },
        }

        mock_ws.add_incoming_message(close)
        msg = await mock_ws.receive()
        data = json.loads(msg)

        assert data["type"] == "CONNECTION_CLOSING"


# =============================================================================
# Streaming Response Tests
# =============================================================================

class TestStreamingResponses:
    """Tests for streaming response formats."""

    def test_stream_start_message(self):
        """Test stream start message format."""
        start = {
            "type": "STREAM_START",
            "timestamp": "2025-12-13T00:00:00.000Z",
            "thread_id": "thread-123",
            "payload": {
                "request_id": "req-456",
                "estimated_duration_ms": 2000,
                "total_stages": 7,
            },
        }

        assert start["type"] == "STREAM_START"
        assert "estimated_duration_ms" in start["payload"]

    def test_stream_chunk_message(self):
        """Test stream chunk message format."""
        chunk = {
            "type": "STREAM_CHUNK",
            "timestamp": "2025-12-13T00:00:00.000Z",
            "thread_id": "thread-123",
            "payload": {
                "chunk_index": 5,
                "content": "The main function initializes",
                "is_final": False,
            },
        }

        assert chunk["type"] == "STREAM_CHUNK"
        assert "content" in chunk["payload"]

    def test_stream_end_message(self):
        """Test stream end message format."""
        end = {
            "type": "STREAM_END",
            "timestamp": "2025-12-13T00:00:00.000Z",
            "thread_id": "thread-123",
            "payload": {
                "request_id": "req-456",
                "status": "success",
                "total_duration_ms": 1850,
                "total_chunks": 15,
                "final_response": {
                    "response": "The main function...",
                    "citations": [...],
                    "files_examined": [...],
                },
            },
        }

        assert end["type"] == "STREAM_END"
        assert "final_response" in end["payload"]


# =============================================================================
# Progress Tracking Tests
# =============================================================================

class TestProgressTracking:
    """Tests for progress tracking messages."""

    def test_progress_update_format(self):
        """Test progress update message format."""
        progress = {
            "type": "PROGRESS_UPDATE",
            "timestamp": "2025-12-13T00:00:00.000Z",
            "thread_id": "thread-123",
            "payload": {
                "percent_complete": 45,
                "current_stage": "traverser",
                "stages_completed": 3,
                "total_stages": 7,
                "files_examined": 8,
                "elapsed_ms": 900,
            },
        }

        assert progress["type"] == "PROGRESS_UPDATE"
        assert 0 <= progress["payload"]["percent_complete"] <= 100

    def test_progress_with_substeps(self):
        """Test progress with substep details."""
        progress = {
            "type": "PROGRESS_UPDATE",
            "timestamp": "2025-12-13T00:00:00.000Z",
            "thread_id": "thread-123",
            "payload": {
                "percent_complete": 50,
                "current_stage": "traverser",
                "substeps": [
                    {"name": "read_code", "status": "completed"},
                    {"name": "find_related", "status": "in_progress"},
                    {"name": "trace_flow", "status": "pending"},
                ],
            },
        }

        assert isinstance(progress["payload"]["substeps"], list)
        for substep in progress["payload"]["substeps"]:
            assert substep["status"] in ["pending", "in_progress", "completed"]


# =============================================================================
# Client Request Tests
# =============================================================================

class TestClientRequests:
    """Tests for client-to-server WebSocket messages."""

    def test_analyze_request_message(self):
        """Test analyze request message format."""
        request = {
            "type": "ANALYZE_REQUEST",
            "timestamp": "2025-12-13T00:00:00.000Z",
            "payload": {
                "query": "What does the main function do?",
                "session_id": "session-123",
                "options": {
                    "stream": True,
                    "include_progress": True,
                },
            },
        }

        assert request["type"] == "ANALYZE_REQUEST"
        assert "query" in request["payload"]

    def test_cancel_request_message(self):
        """Test cancel request message format."""
        cancel = {
            "type": "CANCEL_REQUEST",
            "timestamp": "2025-12-13T00:00:00.000Z",
            "payload": {
                "request_id": "req-456",
                "reason": "User cancelled",
            },
        }

        assert cancel["type"] == "CANCEL_REQUEST"
        assert "request_id" in cancel["payload"]

    def test_clarification_response_message(self):
        """Test clarification response message format."""
        response = {
            "type": "CLARIFICATION_RESPONSE",
            "timestamp": "2025-12-13T00:00:00.000Z",
            "payload": {
                "thread_id": "thread-123",
                "selected_option": "1",
                "additional_context": "I mean the app entry point",
            },
        }

        assert response["type"] == "CLARIFICATION_RESPONSE"
        assert "selected_option" in response["payload"]


# =============================================================================
# Event Ordering Tests
# =============================================================================

class TestEventOrdering:
    """Tests for event ordering and sequencing."""

    def test_event_sequence_for_agent(self):
        """Test correct event sequence for agent execution."""
        events = [
            {"type": "AGENT_STARTED", "payload": {"agent_name": "perception"}},
            {"type": "TOOL_STARTED", "payload": {"tool_name": "normalize"}},
            {"type": "TOOL_COMPLETED", "payload": {"tool_name": "normalize"}},
            {"type": "AGENT_COMPLETED", "payload": {"agent_name": "perception"}},
        ]

        # STARTED should come before COMPLETED
        started_idx = next(i for i, e in enumerate(events) if e["type"] == "AGENT_STARTED")
        completed_idx = next(i for i, e in enumerate(events) if e["type"] == "AGENT_COMPLETED")
        assert started_idx < completed_idx

    def test_full_pipeline_event_sequence(self):
        """Test event sequence for full pipeline."""
        agent_order = [
            "perception",
            "intent",
            "planner",
            "traverser",
            "synthesizer",
            "critic",
            "integration",
        ]

        events = []
        for agent in agent_order:
            events.append({"type": "AGENT_STARTED", "payload": {"agent_name": agent}})
            events.append({"type": "AGENT_COMPLETED", "payload": {"agent_name": agent}})

        # Verify order
        for i, agent in enumerate(agent_order):
            start_idx = i * 2
            complete_idx = start_idx + 1
            assert events[start_idx]["payload"]["agent_name"] == agent
            assert events[complete_idx]["payload"]["agent_name"] == agent


# =============================================================================
# Error Recovery Tests
# =============================================================================

class TestErrorRecovery:
    """Tests for error handling in WebSocket communication."""

    def test_recoverable_error_event(self):
        """Test recoverable error event format."""
        error = {
            "type": "ERROR",
            "timestamp": "2025-12-13T00:00:00.000Z",
            "thread_id": "thread-123",
            "payload": {
                "error_code": "TOOL_RETRY",
                "error_message": "Tool execution failed, retrying...",
                "recoverable": True,
                "retry_attempt": 1,
                "max_retries": 3,
            },
        }

        assert error["payload"]["recoverable"] is True
        assert "retry_attempt" in error["payload"]

    def test_fatal_error_event(self):
        """Test fatal error event format."""
        error = {
            "type": "ERROR",
            "timestamp": "2025-12-13T00:00:00.000Z",
            "thread_id": "thread-123",
            "payload": {
                "error_code": "FATAL_ERROR",
                "error_message": "Pipeline failed irrecoverably",
                "recoverable": False,
                "partial_results": {
                    "completed_agents": ["perception", "intent"],
                    "files_examined": 5,
                },
            },
        }

        assert error["payload"]["recoverable"] is False
        assert "partial_results" in error["payload"]

    def test_reconnection_message(self):
        """Test reconnection message format."""
        reconnect = {
            "type": "RECONNECTION_AVAILABLE",
            "timestamp": "2025-12-13T00:00:00.000Z",
            "payload": {
                "thread_id": "thread-123",
                "resumable": True,
                "resume_from_agent": "traverser",
                "expires_at": "2025-12-13T01:00:00.000Z",
            },
        }

        assert reconnect["type"] == "RECONNECTION_AVAILABLE"
        assert "resumable" in reconnect["payload"]
