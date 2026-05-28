import os
from pathlib import Path
import shutil
import tempfile
import pytest

TRACE_ROOT = Path(__file__).parents[3] / "ext" / "jam-conformance" / "fuzz-reports" / "0.7.2" / "traces"
DEFAULT_TRACE_ROOT = TRACE_ROOT


def get_all_modules(trace_root: Path):
    if not trace_root.exists():
        return []
    return [d.name for d in trace_root.iterdir() if d.is_dir()]

def pytest_addoption(parser):
    parser.addoption("--module", action="store", default=None,
                     help="STF module(s) to test (e.g. safrole, fallback, reports-IO)")
    parser.addoption("--pattern", action="store", default="*.json",
                     help="File glob pattern(s) to match (e.g. --pattern='*.json' --pattern='fee_*.json')")
    parser.addoption("--trace-root", action="store", default=str(DEFAULT_TRACE_ROOT),
                     help="Root directory containing trace vector files or module subdirectories")


def pytest_generate_tests(metafunc):
    if "module" not in metafunc.fixturenames or "pattern" not in metafunc.fixturenames:
        return

    trace_root = Path(metafunc.config.getoption("trace_root")).expanduser()
    module = metafunc.config.getoption("module")
    if module is None:
        modules = get_all_modules(trace_root)
        if not modules:
            modules = ["*"]
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
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

@pytest.fixture
def rpc(request):
    return request.config.getoption("--no-rpc", default=True)


@pytest.fixture
def trace_root(request):
    return Path(request.config.getoption("trace_root")).expanduser()
