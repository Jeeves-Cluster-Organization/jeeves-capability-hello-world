"""
Root conftest to ensure proper import paths.

This file exists at the project root to ensure that the project directory
is in Python's sys.path before pytest starts collecting tests. This is
especially important on Windows where pytest's import mechanism may not
properly handle the pythonpath setting in pytest.ini.
"""

import sys
import warnings
from pathlib import Path
from unittest.mock import MagicMock

# Try to import numpy, or create a mock if not available
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    # Create a minimal numpy mock for testing without actual numpy
    class MockNumpyModule:
        """Minimal numpy mock for testing environments without numpy."""
        float32 = 'float32'

        @staticmethod
        def random_rand(*shape):
            """Return a list-based mock for random values."""
            import random
            if len(shape) == 1:
                return [random.random() for _ in range(shape[0])]
            elif len(shape) == 2:
                return [[random.random() for _ in range(shape[1])] for _ in range(shape[0])]
            return [random.random()]

        @staticmethod
        def array(data):
            """Return data as-is (mock)."""
            return data

        class random:
            @staticmethod
            def rand(*shape):
                import random as rand_mod
                if len(shape) == 1:
                    return [rand_mod.random() for _ in range(shape[0])]
                elif len(shape) == 2:
                    return [[rand_mod.random() for _ in range(shape[1])] for _ in range(shape[0])]
                return [rand_mod.random()]

    np = MockNumpyModule()
    # Also mock numpy in sys.modules
    sys.modules["numpy"] = MagicMock()
    sys.modules["numpy"].random = MagicMock()
    sys.modules["numpy"].random.rand = np.random.rand
    sys.modules["numpy"].array = np.array
    sys.modules["numpy"].float32 = np.float32

# ============================================================================
# Mock Heavy ML Dependencies (sentence_transformers, transformers)
# These are too heavy to install in lightweight testing environments
# ============================================================================

def _create_mock_sentence_transformer():
    """Create a mock SentenceTransformer class."""
    class MockSentenceTransformer:
        def __init__(self, model_name: str = "all-MiniLM-L6-v2", *args, **kwargs):
            self.model_name = model_name
            self._embedding_dim = 384  # Standard dimension for MiniLM

        def encode(self, texts, convert_to_numpy=True, *args, **kwargs):
            """Return mock embeddings."""
            if isinstance(texts, str):
                # Single text
                if NUMPY_AVAILABLE:
                    return np.random.rand(self._embedding_dim).astype(np.float32)
                else:
                    return np.random.rand(self._embedding_dim)
            else:
                # Batch of texts
                if NUMPY_AVAILABLE:
                    return np.random.rand(len(texts), self._embedding_dim).astype(np.float32)
                else:
                    return np.random.rand(len(texts), self._embedding_dim)

        def get_sentence_embedding_dimension(self):
            return self._embedding_dim

    return MockSentenceTransformer

def _create_mock_cross_encoder():
    """Create a mock CrossEncoder class."""
    class MockCrossEncoder:
        def __init__(self, model_name: str = "cross-encoder/nli-deberta-v3-base", *args, **kwargs):
            self.model_name = model_name

        def predict(self, sentence_pairs, *args, **kwargs):
            """Return mock NLI predictions."""
            if isinstance(sentence_pairs, list) and len(sentence_pairs) > 0:
                if isinstance(sentence_pairs[0], (list, tuple)):
                    # Multiple pairs: return array of scores
                    return [[0.1, 0.1, 0.8]] * len(sentence_pairs)  # Mock: entailment
                else:
                    # Single pair
                    return [0.1, 0.1, 0.8]  # Mock: entailment
            return [0.1, 0.1, 0.8]

        def rank(self, query, documents, *args, **kwargs):
            """Return mock rankings."""
            return [{"corpus_id": i, "score": 1.0 - (i * 0.1)} for i in range(len(documents))]

    return MockCrossEncoder

# Only mock if not already installed
if "sentence_transformers" not in sys.modules:
    mock_st = MagicMock()
    mock_st.SentenceTransformer = _create_mock_sentence_transformer()
    mock_st.CrossEncoder = _create_mock_cross_encoder()
    sys.modules["sentence_transformers"] = mock_st

# Mock transformers if not installed (for NLI models)
if "transformers" not in sys.modules:
    mock_transformers = MagicMock()
    mock_transformers.AutoTokenizer = MagicMock()
    mock_transformers.AutoModelForSequenceClassification = MagicMock()
    mock_transformers.pipeline = MagicMock(return_value=lambda x: [{"label": "entailment", "score": 0.9}])
    sys.modules["transformers"] = mock_transformers

# Mock torch if not installed
if "torch" not in sys.modules:
    mock_torch = MagicMock()
    mock_torch.cuda = MagicMock()
    mock_torch.cuda.is_available = MagicMock(return_value=False)
    mock_torch.device = MagicMock(return_value="cpu")
    mock_torch.no_grad = MagicMock(return_value=MagicMock(__enter__=MagicMock(), __exit__=MagicMock()))
    mock_torch.Tensor = MagicMock
    mock_torch.float32 = "float32"
    sys.modules["torch"] = mock_torch

import pytest

# Ensure httpx compat patch is applied before any TestClient usage.
# This is optional - only needed for mission_system tests
try:
    from jeeves_mission_system.common import httpx_compat  # noqa: F401
except ImportError:
    # httpx not installed - skip for lightweight testing
    pass

try:
    # Constitutional compliance: Use adapters instead of direct avionics imports
    from jeeves_mission_system.adapters import get_settings
    test_settings = get_settings()
    # Tests expect confirmation prompts to be opt-in per scenario.
    test_settings.enable_confirmations = False
except ImportError:
    # mission_system not fully installed - skip for core-only testing
    pass

@pytest.fixture(scope="session", autouse=True)
def _disable_confirmations_session_override():
    """Ensure confirmations stay disabled unless a test explicitly enables them."""
    try:
        # Constitutional compliance: Use adapters instead of direct avionics imports
        from jeeves_mission_system.adapters import get_settings
        test_settings = get_settings()
        original = test_settings.enable_confirmations
        test_settings.enable_confirmations = False
        yield
        test_settings.enable_confirmations = original
    except (ImportError, NameError):
        # mission_system not installed - skip for lightweight testing
        yield

# Ensure project root is in Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Add jeeves-core submodule to Python path for core packages
# (jeeves_protocols, jeeves_avionics, jeeves_mission_system, etc.)
jeeves_core_path = project_root / "jeeves-core"
if jeeves_core_path.exists() and str(jeeves_core_path) not in sys.path:
    sys.path.insert(0, str(jeeves_core_path))


def pytest_addoption(parser):
    """Add custom command-line options for snapshot testing."""
    parser.addoption(
        "--snapshot-update",
        action="store_true",
        default=False,
        help="Update baseline snapshots instead of comparing"
    )
    parser.addoption(
        "--snapshot-show-diff",
        action="store_true",
        default=False,
        help="Show detailed diff for snapshot mismatches"
    )


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "regression: mark test as regression test"
    )
    config.addinivalue_line(
        "markers", "snapshot: mark test as snapshot test"
    )


# ============================================================================
# Shared Test Fixtures (centralized from child conftest.py files)
# ============================================================================

@pytest.fixture
def anyio_backend():
    """Use asyncio as the async backend.

    This fixture is shared across all test modules to ensure consistent
    async behavior. Centralized here to avoid duplication.
    """
    return "asyncio"


@pytest.fixture
def mock_logger():
    """Create a mock logger conforming to LoggerProtocol.

    The logger supports:
    - bind(**kwargs) -> logger (returns itself with context)
    - debug/info/warning/error/critical methods

    Centralized here as it's used across multiple test modules.
    """
    logger = MagicMock()
    logger.bind.return_value = logger
    return logger


# ============================================================================
# UUID Utilities
# ============================================================================

try:
    # uuid_str is a utility function from shared utilities
    from jeeves_shared.uuid_utils import uuid_str  # noqa: F401
except ImportError:
    uuid_str = None  # type: ignore
