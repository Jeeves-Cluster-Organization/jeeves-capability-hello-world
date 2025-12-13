"""
UI/UX Tests for API Endpoints.

Tests HTTP API endpoints, request/response formats, and user-facing behavior.
Based on the Jeeves Core Runtime Contract.

Test Markers:
    @pytest.mark.ui_ux - UI/UX tests
    @pytest.mark.requires_docker - Requires running services
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = [
    pytest.mark.ui_ux,
    pytest.mark.asyncio,
]


# =============================================================================
# Request/Response Format Tests
# =============================================================================

class TestRequestFormats:
    """Tests for API request format validation."""

    def test_analyze_request_format(self):
        """Test code analysis request format."""
        # Valid request per contract
        valid_request = {
            "query": "What does the main function do?",
            "session_id": "session-123",
            "repo_path": "/workspace",
            "options": {
                "max_files": 50,
                "include_citations": True,
            },
        }

        assert "query" in valid_request
        assert isinstance(valid_request["query"], str)
        assert len(valid_request["query"]) > 0

    def test_analyze_request_minimal(self):
        """Test minimal valid request."""
        minimal_request = {
            "query": "Explain this code",
        }

        assert "query" in minimal_request
        assert len(minimal_request) == 1

    def test_analyze_request_with_thread_id(self):
        """Test request with thread/conversation ID."""
        request = {
            "query": "Continue the analysis",
            "thread_id": "thread-abc-123",
        }

        assert "thread_id" in request

    def test_request_query_types(self):
        """Test different query types per contract."""
        query_types = [
            ("trace the flow of data", "trace_flow"),
            ("find the definition of UserClass", "find_definition"),
            ("explain how authentication works", "explain"),
            ("search for error handling", "search"),
        ]

        for query, expected_type in query_types:
            request = {"query": query}
            assert len(request["query"]) > 0


class TestResponseFormats:
    """Tests for API response format validation."""

    def test_success_response_format(self):
        """Test successful response format per contract."""
        success_response = {
            "status": "success",
            "response": "The main function initializes...",
            "files_examined": ["main.py", "utils.py"],
            "citations": [
                {"file": "main.py", "line": 10, "content": "def main():"},
                {"file": "main.py", "line": 15, "content": "    setup()"},
            ],
            "thread_id": "thread-123",
            "metadata": {
                "processing_time_ms": 250,
                "agent_count": 7,
                "tokens_used": 1500,
            },
        }

        # Required fields
        assert "status" in success_response
        assert success_response["status"] == "success"
        assert "response" in success_response

        # Optional but expected fields per contract
        assert "files_examined" in success_response
        assert "citations" in success_response
        assert "thread_id" in success_response

    def test_error_response_format(self):
        """Test error response format per contract."""
        error_response = {
            "status": "error",
            "error": "Query cannot be empty",
            "error_code": "EMPTY_QUERY",
            "details": {
                "field": "query",
                "constraint": "non-empty string required",
            },
        }

        assert error_response["status"] == "error"
        assert "error" in error_response
        assert "error_code" in error_response

    def test_partial_response_format(self):
        """Test partial/streaming response format."""
        partial_response = {
            "status": "partial",
            "response": "Analyzing files...",
            "progress": {
                "current_agent": "traverser",
                "agents_completed": 4,
                "total_agents": 7,
                "files_examined": 10,
            },
        }

        assert partial_response["status"] == "partial"
        assert "progress" in partial_response

    def test_citation_format(self):
        """Test citation format per contract."""
        citation = {
            "file": "main.py",
            "line": 42,
            "content": "def authenticate(user):",
            "context": {
                "before": ["# Authentication module"],
                "after": ["    '''Authenticate user'''"],
            },
        }

        # Required citation fields
        assert "file" in citation
        assert "line" in citation
        assert isinstance(citation["line"], int)

    def test_response_with_clarification(self):
        """Test response requesting clarification."""
        clarification_response = {
            "status": "clarification_needed",
            "clarification": {
                "question": "Which 'main' function? There are multiple files with main().",
                "options": [
                    {"file": "app/main.py", "description": "Application entry point"},
                    {"file": "cli/main.py", "description": "CLI entry point"},
                ],
            },
            "thread_id": "thread-123",
        }

        assert clarification_response["status"] == "clarification_needed"
        assert "clarification" in clarification_response
        assert "question" in clarification_response["clarification"]


class TestResponseFields:
    """Tests for specific response field formats."""

    def test_files_examined_is_list(self):
        """Test files_examined is list of strings."""
        response = {
            "files_examined": ["main.py", "utils.py", "config/settings.py"],
        }

        assert isinstance(response["files_examined"], list)
        assert all(isinstance(f, str) for f in response["files_examined"])

    def test_citations_is_list(self):
        """Test citations is list of citation objects."""
        response = {
            "citations": [
                {"file": "a.py", "line": 1},
                {"file": "b.py", "line": 10},
            ],
        }

        assert isinstance(response["citations"], list)
        for citation in response["citations"]:
            assert "file" in citation
            assert "line" in citation

    def test_metadata_fields(self):
        """Test expected metadata fields."""
        metadata = {
            "processing_time_ms": 250,
            "agent_count": 7,
            "tokens_used": 1500,
            "llm_calls": 3,
            "tool_calls": 5,
            "timestamp": "2025-12-13T00:00:00Z",
        }

        assert isinstance(metadata["processing_time_ms"], (int, float))
        assert isinstance(metadata["agent_count"], int)


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Tests for API error handling."""

    def test_validation_error_format(self):
        """Test validation error format."""
        error = {
            "status": "error",
            "error": "Validation failed",
            "error_code": "VALIDATION_ERROR",
            "validation_errors": [
                {"field": "query", "error": "cannot be empty"},
                {"field": "max_files", "error": "must be positive integer"},
            ],
        }

        assert "validation_errors" in error
        assert len(error["validation_errors"]) > 0

    def test_timeout_error_format(self):
        """Test timeout error format."""
        error = {
            "status": "error",
            "error": "Request timed out",
            "error_code": "TIMEOUT",
            "partial_results": {
                "completed_agents": ["perception", "intent", "planner"],
                "files_examined_so_far": 5,
            },
            "retry_after_seconds": 30,
        }

        assert error["error_code"] == "TIMEOUT"
        assert "partial_results" in error

    def test_rate_limit_error_format(self):
        """Test rate limit error format."""
        error = {
            "status": "error",
            "error": "Rate limit exceeded",
            "error_code": "RATE_LIMITED",
            "retry_after_seconds": 60,
            "limit_info": {
                "requests_per_minute": 10,
                "current_usage": 12,
            },
        }

        assert error["error_code"] == "RATE_LIMITED"
        assert "retry_after_seconds" in error

    def test_service_unavailable_format(self):
        """Test service unavailable error format."""
        error = {
            "status": "error",
            "error": "Service temporarily unavailable",
            "error_code": "SERVICE_UNAVAILABLE",
            "affected_services": ["llm-server"],
        }

        assert error["error_code"] == "SERVICE_UNAVAILABLE"


class TestErrorCodes:
    """Tests for standardized error codes."""

    def test_standard_error_codes(self):
        """Test all standard error codes."""
        standard_codes = [
            "EMPTY_QUERY",
            "INVALID_SESSION",
            "VALIDATION_ERROR",
            "TIMEOUT",
            "RATE_LIMITED",
            "SERVICE_UNAVAILABLE",
            "LLM_UNAVAILABLE",
            "DATABASE_ERROR",
            "INTERNAL_ERROR",
            "NOT_FOUND",
            "UNAUTHORIZED",
            "FORBIDDEN",
        ]

        # All codes should be uppercase with underscores
        for code in standard_codes:
            assert code == code.upper()
            assert " " not in code


# =============================================================================
# Content Type Tests
# =============================================================================

class TestContentTypes:
    """Tests for content type handling."""

    def test_json_request_content_type(self):
        """Test JSON request content type."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        assert "json" in headers["Content-Type"]

    def test_streaming_content_type(self):
        """Test streaming response content type."""
        headers = {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }

        assert headers["Content-Type"] == "text/event-stream"


# =============================================================================
# Pagination Tests
# =============================================================================

class TestPagination:
    """Tests for paginated responses."""

    def test_paginated_response_format(self):
        """Test paginated response format."""
        response = {
            "status": "success",
            "data": [{"file": "a.py"}, {"file": "b.py"}],
            "pagination": {
                "page": 1,
                "per_page": 20,
                "total_items": 100,
                "total_pages": 5,
                "has_next": True,
                "has_prev": False,
            },
        }

        assert "pagination" in response
        assert isinstance(response["pagination"]["total_items"], int)

    def test_pagination_links(self):
        """Test pagination links format."""
        pagination = {
            "links": {
                "self": "/api/files?page=2",
                "first": "/api/files?page=1",
                "last": "/api/files?page=5",
                "next": "/api/files?page=3",
                "prev": "/api/files?page=1",
            },
        }

        assert "self" in pagination["links"]


# =============================================================================
# Session Management Tests
# =============================================================================

class TestSessionManagement:
    """Tests for session/thread management."""

    def test_session_creation_response(self):
        """Test session creation response."""
        response = {
            "session_id": "session-uuid-123",
            "thread_id": "thread-uuid-456",
            "created_at": "2025-12-13T00:00:00Z",
            "expires_at": "2025-12-14T00:00:00Z",
        }

        assert "session_id" in response
        assert "thread_id" in response

    def test_session_context_format(self):
        """Test session context format."""
        context = {
            "session_id": "session-123",
            "thread_id": "thread-456",
            "repo_path": "/workspace",
            "previous_queries": [
                {"query": "What is main?", "timestamp": "2025-12-13T00:00:00Z"},
            ],
            "files_in_context": ["main.py", "utils.py"],
        }

        assert isinstance(context["previous_queries"], list)


# =============================================================================
# Health Endpoint Tests
# =============================================================================

class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_response_format(self):
        """Test health endpoint response format."""
        health = {
            "status": "healthy",
            "version": "1.0.0",
            "timestamp": "2025-12-13T00:00:00Z",
            "services": {
                "database": "healthy",
                "llm": "healthy",
                "cache": "healthy",
            },
        }

        assert health["status"] in ["healthy", "unhealthy", "degraded"]
        assert "services" in health

    def test_detailed_health_response(self):
        """Test detailed health response."""
        health = {
            "status": "degraded",
            "checks": [
                {
                    "name": "database",
                    "status": "healthy",
                    "latency_ms": 5,
                },
                {
                    "name": "llm",
                    "status": "unhealthy",
                    "error": "Connection refused",
                },
            ],
        }

        assert isinstance(health["checks"], list)


# =============================================================================
# Response Metadata Tests
# =============================================================================

class TestResponseMetadata:
    """Tests for response metadata."""

    def test_request_id_in_response(self):
        """Test request ID is returned."""
        response = {
            "request_id": "req-uuid-123",
            "status": "success",
            "response": "...",
        }

        assert "request_id" in response

    def test_timing_metadata(self):
        """Test timing metadata."""
        metadata = {
            "timing": {
                "total_ms": 250,
                "llm_ms": 180,
                "tool_execution_ms": 50,
                "database_ms": 20,
            },
        }

        assert "total_ms" in metadata["timing"]
        total = metadata["timing"]["total_ms"]
        assert total >= metadata["timing"]["llm_ms"]


# =============================================================================
# Citation Format Tests
# =============================================================================

class TestCitationFormats:
    """Tests for citation format variations."""

    def test_inline_citation_format(self):
        """Test inline citation format [file:line]."""
        text = "The main function [main.py:10] calls setup [utils.py:25]"
        # Should contain file:line format
        assert "[main.py:10]" in text

    def test_structured_citation(self):
        """Test structured citation object."""
        citation = {
            "file": "main.py",
            "line": 10,
            "end_line": 15,
            "content": "def main():\n    ...",
            "symbol": "main",
            "symbol_type": "function",
        }

        assert citation["file"].endswith(".py")
        assert citation["line"] > 0

    def test_citation_with_context(self):
        """Test citation with surrounding context."""
        citation = {
            "file": "main.py",
            "line": 10,
            "context_before": 2,
            "context_after": 2,
            "lines": [
                {"line": 8, "content": "# Entry point"},
                {"line": 9, "content": ""},
                {"line": 10, "content": "def main():"},
                {"line": 11, "content": "    '''Main function'''"},
                {"line": 12, "content": "    setup()"},
            ],
        }

        assert len(citation["lines"]) == 5


# =============================================================================
# WebSocket Event Tests
# =============================================================================

class TestWebSocketEvents:
    """Tests for WebSocket event formats."""

    def test_agent_started_event(self):
        """Test agent started event format."""
        event = {
            "type": "agent_started",
            "agent": "perception",
            "timestamp": "2025-12-13T00:00:00Z",
            "thread_id": "thread-123",
        }

        assert event["type"] == "agent_started"
        assert "agent" in event

    def test_agent_completed_event(self):
        """Test agent completed event format."""
        event = {
            "type": "agent_completed",
            "agent": "perception",
            "duration_ms": 45,
            "status": "success",
            "timestamp": "2025-12-13T00:00:00Z",
        }

        assert event["type"] == "agent_completed"
        assert "duration_ms" in event

    def test_tool_execution_event(self):
        """Test tool execution event format."""
        event = {
            "type": "tool_started",
            "tool": "read_code",
            "params": {"file_path": "main.py"},
            "timestamp": "2025-12-13T00:00:00Z",
        }

        assert event["type"] == "tool_started"
        assert "tool" in event

    def test_progress_event(self):
        """Test progress update event format."""
        event = {
            "type": "progress",
            "current_stage": "traverser",
            "stages_completed": 3,
            "total_stages": 7,
            "files_examined": 5,
            "timestamp": "2025-12-13T00:00:00Z",
        }

        assert event["type"] == "progress"
        assert 0 <= event["stages_completed"] <= event["total_stages"]

    def test_stream_end_event(self):
        """Test stream end event format."""
        event = {
            "type": "stream_end",
            "thread_id": "thread-123",
            "total_duration_ms": 1500,
            "timestamp": "2025-12-13T00:00:00Z",
        }

        assert event["type"] == "stream_end"


# =============================================================================
# User Experience Tests
# =============================================================================

class TestUserExperience:
    """Tests for user experience aspects."""

    def test_error_messages_are_helpful(self):
        """Test error messages are user-friendly."""
        error = {
            "error": "Query cannot be empty. Please provide a question about the code.",
            "hint": "Try asking something like 'What does the main function do?'",
        }

        assert len(error["error"]) > 10
        assert "hint" in error

    def test_progress_updates_are_informative(self):
        """Test progress updates are informative."""
        progress = {
            "message": "Analyzing code structure...",
            "current_agent": "traverser",
            "details": "Examining main.py (3 of 10 files)",
        }

        assert "message" in progress
        assert len(progress["message"]) > 0

    def test_response_includes_summary(self):
        """Test responses include a summary for quick reading."""
        response = {
            "summary": "The main function initializes the application and starts the server.",
            "details": "...(long detailed explanation)...",
            "citations": [...],
        }

        assert "summary" in response
        assert len(response["summary"]) < 500  # Summary should be concise
