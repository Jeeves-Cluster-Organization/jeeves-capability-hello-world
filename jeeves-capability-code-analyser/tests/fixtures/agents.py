"""Pipeline fixtures for testing the code analysis pipeline.

Centralized Architecture (v4.0):
- No concrete agent fixtures (agents are config-driven)
- Provides PipelineConfig and Runtime fixtures
- Mock services remain for isolation
"""

import pytest

from .mocks.llm import MockLLMProvider
from .mocks.tools import MockToolRegistry, MockToolExecutor
from .mocks.database import MockDatabaseClient
from .mocks.events import MockEventBus
from .mocks.settings import MockSettings


# ============================================================
# Mock Service Fixtures
# ============================================================

@pytest.fixture
def mock_llm_provider() -> MockLLMProvider:
    """Mock LLM provider for pipeline testing."""
    return MockLLMProvider()


@pytest.fixture
def mock_tool_registry() -> MockToolRegistry:
    """Mock tool registry with default code analysis tools."""
    return MockToolRegistry()


@pytest.fixture
def mock_tool_executor() -> MockToolExecutor:
    """Mock tool executor with default responses."""
    return MockToolExecutor()


@pytest.fixture
def mock_db() -> MockDatabaseClient:
    """Mock database client for pipeline testing."""
    return MockDatabaseClient()


@pytest.fixture
def mock_event_bus() -> MockEventBus:
    """Mock event bus for capturing pipeline events."""
    return MockEventBus()


@pytest.fixture
def mock_settings() -> MockSettings:
    """Mock settings for pipeline testing."""
    return MockSettings()


# ============================================================
# Pipeline Configuration Fixtures
# ============================================================

@pytest.fixture
def pipeline_config():
    """Get the code analysis pipeline configuration.

    Use for testing the pipeline configuration and hooks.
    """
    from jeeves_capability_code_analyser.pipeline_config import get_code_analysis_pipeline
    return get_code_analysis_pipeline()


@pytest.fixture
def mock_llm_factory(mock_llm_provider):
    """Factory that returns mock LLM providers."""
    def factory(role: str):
        return mock_llm_provider
    return factory


__all__ = [
    # Mock services
    "mock_llm_provider",
    "mock_tool_registry",
    "mock_tool_executor",
    "mock_db",
    "mock_event_bus",
    "mock_settings",
    # Pipeline configuration
    "pipeline_config",
    "mock_llm_factory",
]
