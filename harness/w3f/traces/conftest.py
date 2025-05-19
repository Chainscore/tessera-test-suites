import os
from pathlib import Path

def get_all_modules():
    transform_dir = Path(__file__).parents[3] / "ext" / "w3f-w-traces" / "traces"
    return [f.stem for f in transform_dir.glob("*.py") if f.name != "__init__.py"]

def pytest_addoption(parser):
    parser.addoption("--module", action="store", default=None,
                     help="STF module(s) to test (e.g. safrole, fallback, reports-IO)")
    parser.addoption("--end", action="store", default="100",
                     help="Till block")

def pytest_generate_tests(metafunc):
    module = metafunc.config.getoption("module")
    if module is None:
        modules = get_all_modules()
    else:
        modules = [module]

    end = metafunc.config.getoption("end")
    print("end", end)

    params = [(m, end) for m in modules]
    metafunc.parametrize("module,end", params)