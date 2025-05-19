import os
from pathlib import Path

def pytest_addoption(parser):
    parser.addoption("--pattern", action="store", default="*.json",
                     help="File glob pattern(s) to match (e.g. --pattern='*.json' --pattern='fee_*.json')")

def pytest_generate_tests(metafunc):
    pattern = metafunc.config.getoption("pattern")
    metafunc.parametrize("pattern", [pattern])