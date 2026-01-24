"""Envelope fixtures for testing code analysis pipeline.

Centralized Architecture (v4.0):
- Uses GenericEnvelope with dynamic outputs dict
- Pre-populated states for each pipeline stage
- Imports from jeeves_protocols
"""

import pytest
from typing import Optional, Dict, Any
from uuid import uuid4

from jeeves_protocols import (
    GenericEnvelope,
    create_generic_envelope,
    RequestContext,
)
from registration import CAPABILITY_ID


# Test constants
TEST_USER_ID = "test-user-001"
TEST_SESSION_ID = "test-session-001"


@pytest.fixture
def envelope_factory():
    """Factory for creating GenericEnvelope instances.

    Usage:
        envelope = envelope_factory(
            user_message="What is the Agent class?",
            user_id="test-user"
        )
    """
    def _create(
        user_message: str = "Test message",
        user_id: str = TEST_USER_ID,
        session_id: str = TEST_SESSION_ID,
        request_id: Optional[str] = None,
    ) -> GenericEnvelope:
        request_context = RequestContext(
            request_id=request_id or f"req_{uuid4().hex[:16]}",
            capability=CAPABILITY_ID,
            session_id=session_id,
            user_id=user_id,
        )
        return create_generic_envelope(
            raw_input=user_message,
            request_context=request_context,
        )

    return _create


@pytest.fixture
def sample_envelope(envelope_factory) -> GenericEnvelope:
    """Pre-configured sample envelope for basic tests."""
    return envelope_factory(
        user_message="What agents exist in this codebase?",
    )


@pytest.fixture
def envelope_with_perception(envelope_factory) -> GenericEnvelope:
    """Envelope with perception output populated.

    Use for testing intent stage onwards.
    """
    envelope = envelope_factory(user_message="What agents exist in this codebase?")
    envelope.set_output("perception", {
        "normalized_input": "What agents exist in this codebase?",
        "context_summary": "Code analysis query about agent architecture",
        "session_scope": TEST_SESSION_ID,
        "detected_languages": ["python"],
    })
    envelope.current_stage = "intent"
    return envelope


@pytest.fixture
def envelope_with_intent(envelope_with_perception) -> GenericEnvelope:
    """Envelope with intent output populated.

    Use for testing planner stage onwards.
    """
    envelope = envelope_with_perception
    envelope.set_output("intent", {
        "intent": "understand_architecture",
        "goals": ["Find and list all agents in the codebase"],
        "constraints": [],
        "confidence": 0.9,
        "clarification_needed": False,
        "clarification_question": None,
    })
    envelope.current_stage = "planner"
    # Initialize goal tracking
    envelope.initialize_goals(["Find and list all agents in the codebase"])
    return envelope


@pytest.fixture
def envelope_with_plan(envelope_with_intent) -> GenericEnvelope:
    """Envelope with plan output populated.

    Use for testing executor stage onwards.
    """
    envelope = envelope_with_intent
    envelope.set_output("plan", {
        "plan_id": "plan-test-001",
        "steps": [
            {
                "step_id": "step-1",
                "tool": "glob_files",
                "parameters": {"pattern": "agents/**/*.py"},
            },
            {
                "step_id": "step-2",
                "tool": "read_file",
                "parameters": {"path": "agents/__init__.py"},
            },
        ],
        "rationale": "Search for agent files and read their contents",
        "feasibility_score": 0.95,
    })
    envelope.current_stage = "executor"
    return envelope


@pytest.fixture
def envelope_with_execution(envelope_with_plan) -> GenericEnvelope:
    """Envelope with execution output populated.

    Use for testing synthesizer stage onwards.
    """
    envelope = envelope_with_plan
    envelope.set_output("execution", {
        "results": [
            {
                "step_id": "step-1",
                "tool": "glob_files",
                "parameters": {"pattern": "agents/**/*.py"},
                "status": "success",
                "data": {"files": ["agents/base.py", "agents/perception.py"], "count": 2},
            },
            {
                "step_id": "step-2",
                "tool": "read_file",
                "parameters": {"path": "agents/__init__.py"},
                "status": "success",
                "data": {
                    "content": "from .base import Agent\nfrom .perception import PerceptionAgent",
                    "path": "agents/__init__.py",
                    "total_lines": 2,
                },
            },
        ],
        "all_succeeded": True,
        "summary": "All steps executed successfully",
    })
    envelope.current_stage = "synthesizer"
    return envelope


@pytest.fixture
def envelope_with_synthesizer(envelope_with_execution) -> GenericEnvelope:
    """Envelope with synthesizer output populated.

    Use for testing critic stage onwards.
    """
    envelope = envelope_with_execution
    envelope.set_output("synthesizer", {
        "entities": [
            {
                "name": "Agent",
                "type": "class",
                "location": "agents/base.py:1",
            },
            {
                "name": "PerceptionAgent",
                "type": "class",
                "location": "agents/perception.py:1",
            },
        ],
        "key_flows": [],
        "patterns": [],
        "summary": "Found 2 agent classes in the codebase.",
        "evidence_summary": "Explored agents directory",
    })
    envelope.current_stage = "critic"
    return envelope


@pytest.fixture
def envelope_with_critic(envelope_with_synthesizer) -> GenericEnvelope:
    """Envelope with critic output populated.

    Use for testing integration stage.
    """
    envelope = envelope_with_synthesizer
    envelope.set_output("critic", {
        "verdict": "approved",
        "confidence": 0.95,
        "intent_alignment_score": 0.95,
        "issues": [],
        "recommendations": [],
        "goal_updates": {
            "satisfied": ["Find and list all agents in the codebase"],
            "pending": [],
            "added": [],
        },
    })
    # Update goal tracking
    envelope.goal_completion_status["Find and list all agents in the codebase"] = "satisfied"
    envelope.remaining_goals = []
    envelope.current_stage = "integration"
    return envelope


__all__ = [
    "envelope_factory",
    "sample_envelope",
    "envelope_with_perception",
    "envelope_with_intent",
    "envelope_with_plan",
    "envelope_with_execution",
    "envelope_with_synthesizer",
    "envelope_with_critic",
]
