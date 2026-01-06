import os
from pathlib import Path
import shutil
import tempfile
import pytest

def get_all_modules():
    transform_dir = Path(__file__).parents[3] / "ext" / "jam-conformance" / "fuzz-reports" / "0.7.2" / "traces"
    return [d.name for d in transform_dir.iterdir() if d.is_dir()]

def pytest_addoption(parser):
    parser.addoption("--module", action="store", default=None,
                     help="STF module(s) to test (e.g. safrole, fallback, reports-IO)")
    parser.addoption("--pattern", action="store", default="*.json",
                     help="File glob pattern(s) to match (e.g. --pattern='*.json' --pattern='fee_*.json')")


def pytest_generate_tests(metafunc):
    module = metafunc.config.getoption("module")
    if module is None:
        modules = get_all_modules()
    else:
        modules = [module]

    pattern = metafunc.config.getoption("pattern")
    params = [(m,pattern) for m in modules]
    metafunc.parametrize("module,pattern", params)

@pytest.fixture
def db_path():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def rpc(request):
    return request.config.getoption("--no-rpc", default=True)
