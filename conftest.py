"""Root conftest — path setup and shared fixtures."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure project root is in Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Add jeeves-airframe submodule to Python path
jeeves_airframe_path = project_root / "jeeves-airframe"
if jeeves_airframe_path.exists() and str(jeeves_airframe_path) not in sys.path:
    sys.path.insert(0, str(jeeves_airframe_path))

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "regression: mark test as regression test")
    config.addinivalue_line("markers", "snapshot: mark test as snapshot test")


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mock_logger():
    """Mock logger conforming to LoggerProtocol."""
    logger = MagicMock()
    logger.bind.return_value = logger
    return logger
