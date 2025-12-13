"""Pytest configuration for jeeves-capability-code-analyser tests.

This file configures pytest for the app layer test suite.
It ensures proper import paths and shared fixtures.

Constitutional Compliance:
- Uses jeeves_mission_system.contracts for all core types
- Does NOT import from jeeves_core_engine or jeeves_avionics directly
- App layer tests are self-contained with own fixtures
- Constitution R7: register_capability() called at test setup
"""

import sys
from pathlib import Path

import pytest

# Add parent directory to path so we can import from the app
app_root = Path(__file__).parent.parent
sys.path.insert(0, str(app_root))

# Add mission system to path for contracts import
project_root = app_root.parent
sys.path.insert(0, str(project_root))

# Add jeeves-core submodule to Python path for core packages
# (jeeves_protocols, jeeves_avionics, jeeves_mission_system, etc.)
jeeves_core_path = project_root / "jeeves-core"
if jeeves_core_path.exists() and str(jeeves_core_path) not in sys.path:
    sys.path.insert(0, str(jeeves_core_path))


# ============================================================
# Capability Registration Fixture (Constitution R7)
# ============================================================

@pytest.fixture(autouse=True, scope="session")
def setup_capability_registration():
    """Register capability resources per Constitution R7.

    This ensures the CapabilityResourceRegistry is populated with:
    - Database schemas
    - Gateway modes
    - Service configurations
    - Orchestrator factory
    - Tools initializer
    - Agent definitions
    """
    from jeeves_protocols import reset_capability_resource_registry

    # Start with clean registry
    reset_capability_resource_registry()

    # Register capability (Constitution R7)
    from jeeves_capability_code_analyser import register_capability
    register_capability()

    yield

    # Clean up for test isolation
    reset_capability_resource_registry()


# ============================================================
# Language Config Registration Fixture
# ============================================================

@pytest.fixture(autouse=True)
def setup_language_config():
    """Register language config in the global registry for tests.

    This is required because tools like code_tools.py use
    get_language_config_from_registry() which expects the config
    to be registered at bootstrap.
    """
    from jeeves_mission_system.contracts import get_config_registry, ConfigKeys
    from jeeves_capability_code_analyser.config import get_language_config

    registry = get_config_registry()
    config = get_language_config()
    registry.register(ConfigKeys.LANGUAGE_CONFIG, config)
    yield
    # Cleanup not strictly needed as registry persists across tests


# ============================================================
# Import Fixtures from tests/fixtures/ package
# ============================================================

# Envelope fixtures
from tests.fixtures.envelope import (
    envelope_factory,
    sample_envelope,
    envelope_with_perception,
    envelope_with_intent,
    envelope_with_plan,
    envelope_with_execution,
    envelope_with_synthesizer,
    envelope_with_critic,
)

# Mock service fixtures (Centralized Architecture v4.0 - agents are config-driven)
from tests.fixtures.agents import (
    mock_llm_provider,
    mock_tool_registry,
    mock_tool_executor,
    mock_db,
    mock_event_bus,
    mock_settings,
    # Pipeline fixtures
    pipeline_config,
    mock_llm_factory,
)


# ============================================================
# Pytest Configuration
# ============================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests with mocked dependencies"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests with real services"
    )
    config.addinivalue_line(
        "markers", "slow: Slow-running tests"
    )


# ============================================================
# Path Reset Fixture
# ============================================================

@pytest.fixture(autouse=True)
def reset_repo_path_cache():
    """Reset repo path cache before each test.

    Ensures each test starts with a fresh validation state,
    allowing monkeypatch to properly change REPO_PATH.
    """
    try:
        from tools.base.path_helpers import reset_repo_path_cache as reset_cache
        reset_cache()
        yield
        reset_cache()
    except ImportError:
        # path_helpers may not exist yet
        yield


# ============================================================
# Async Backend
# ============================================================

@pytest.fixture
def anyio_backend():
    """Use asyncio as the async backend."""
    return "asyncio"


# Re-export all fixtures for pytest discovery
__all__ = [
    # Envelope fixtures
    "envelope_factory",
    "sample_envelope",
    "envelope_with_perception",
    "envelope_with_intent",
    "envelope_with_plan",
    "envelope_with_execution",
    "envelope_with_synthesizer",
    "envelope_with_critic",
    # Mock service fixtures
    "mock_llm_provider",
    "mock_tool_registry",
    "mock_tool_executor",
    "mock_db",
    "mock_event_bus",
    "mock_settings",
    # Pipeline fixtures
    "pipeline_config",
    "mock_llm_factory",
]
