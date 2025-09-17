import shutil
import tempfile
import pytest
import os
import sys
from pathlib import Path

from jam.logging import setup_logging

# Add tsr-py directory to path for imports if running from tessera-test-suites
if 'tessera-test-suites' in os.getcwd():
    tsr_py_path = Path(os.getcwd()).parent / 'tessera'
    if tsr_py_path.exists() and str(tsr_py_path) not in sys.path:
        sys.path.insert(0, str(tsr_py_path))

# Set up logging environment variables if not already set
if "JAM_LOG_LEVEL" not in os.environ:
    os.environ["JAM_LOG_LEVEL"] = "error"
if "JAM_LOG_LEVEL_BLOCK" not in os.environ:
    os.environ["JAM_LOG_LEVEL_BLOCK"] = "error"
if "JAM_LOG_LEVEL_NODE" not in os.environ:
    os.environ["JAM_LOG_LEVEL_NODE"] = "error"
if "JAM_LOG_LEVEL_NETWORK" not in os.environ:
    os.environ["JAM_LOG_LEVEL_NETWORK"] = "error"
if "JAM_LOG_LEVEL_PVM" not in os.environ:
    os.environ["JAM_LOG_LEVEL_PVM"] = "error"

setup_logging("default", "test")

@pytest.fixture
def db_path():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)
