import shutil
import tempfile
import pytest
import os
import sys
from pathlib import Path

# Add tsr-py directory to path for imports if running from tessera-test-suites
if 'tessera-test-suites' in os.getcwd():
    tsr_py_path = Path(os.getcwd()).parent / 'tessera'
    if tsr_py_path.exists() and str(tsr_py_path) not in sys.path:
        sys.path.insert(0, str(tsr_py_path))

# Set up logging environment variables if not already set
if "LOG_LEVEL" not in os.environ:
    os.environ["LOG_LEVEL"] = "debug"
    os.environ["LOG_LEVEL_IMPORT"] = "error"
    os.environ["LOG_LEVEL_AUTHOR"] = "error"
    os.environ["LOG_LEVEL_NETWORK"] = "error"
    os.environ["LOG_LEVEL_PVM"] = "error"
    os.environ["LOG_LEVEL_HOST_CALLS"] = "debug"
    os.environ["LOG_LEVEL_IN_CORE"] = "error"

@pytest.fixture
def db_path():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)
