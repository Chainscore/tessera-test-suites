import os
from pathlib import Path

def get_all_modules():
    transform_dir = Path(__file__).parents[3] / "ext" / "w3f-w-traces" / "traces"
    return [f.stem for f in transform_dir.glob("*.py") if f.name != "__init__.py"]

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
