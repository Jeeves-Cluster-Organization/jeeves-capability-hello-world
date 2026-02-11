"""Root conftest — shared fixtures."""
from unittest.mock import MagicMock
import pytest


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
