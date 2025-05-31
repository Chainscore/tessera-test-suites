import os
from pathlib import Path

def get_all_modules():
    transform_dir = Path(__file__).parent / "transform"
    print("transform_dir", transform_dir)
    return [f.stem for f in transform_dir.glob("*.py") if f.name != "__init__.py"]

def pytest_addoption(parser):
    parser.addoption("--module", action="store", default=None,
                     help="STF module(s) to test (e.g. assurances, accumulate)")
    parser.addoption("--spec", action="store", default="default",
                     help="Spec to run (e.g. default, full)")
    parser.addoption("--pattern", action="store", default="*.json",
                     help="File glob pattern(s) to match (e.g. --pattern='*.json' --pattern='fee_*.json')")

def pytest_generate_tests(metafunc):
    module = metafunc.config.getoption("module")
    print("module", module)
    if module is None:
        modules = get_all_modules()
    else:
        modules = [module]

    spec = metafunc.config.getoption("spec")
    if spec is None:
        specs = ["default"]
    else:
        specs = [spec]

    pattern = metafunc.config.getoption("pattern")

    params = [(m, s, pattern) for m in modules for s in specs]
    metafunc.parametrize("module,spec,pattern", params)