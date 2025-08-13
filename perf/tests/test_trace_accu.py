import json
import os
from pathlib import Path
import pytest
from jam.settings import setup_setting

from tsrkit_types import Bytes

from jam.logging import logger, setup_logging
from jam.state.ghost import GhostState
# from jam.state.merkle import StateTrie
from jam.state.state import Block, State, setup_state
from rockstore import RockStore
# from jam.types.block import Block

TRACE_ROOT = Path(__file__).parents[2] / "ext" / "w3f"
def get_trace_modules():
    trace_dir = TRACE_ROOT / "traces"

    a= [d.name for d in trace_dir.iterdir() if d.is_dir()]
    return ["reports-l1"]

def fetch_vectors(module: str, pattern: str):
    vector_dir = TRACE_ROOT / "traces" / module
    print("The directories",vector_dir)
    return [
        (f.name, json.load(open(f)))
        for f in vector_dir.glob(pattern)
    ]

os.environ["LOG_LEVEL_HOST_CALLS"] = "debug"

setup_logging(theme="default", environment="testing")


@pytest.mark.parametrize("module", get_trace_modules())
def test_traces(module, tmp_path):
    for name, vector in fetch_vectors(module, "*.json"):
        if(name=="00000003.json"):
            print(f"\n ⏭️Running test case {name} in module {module}...")
            db = None
            post_db = None
            settings = None
            db_path = tmp_path / name
            settings = setup_setting(str(db_path), 1)
            db = RockStore(str(db_path))
            post_db = RockStore(str(db_path / "post"))

            if name == "00000000.json":
                print("Skipping genesis...")
                continue
            block = Block.from_json(vector["block"])
            if len(vector["pre_state"]["keyvals"]) != 0:
                pre_data = {Bytes.from_json(keyval["key"]):Bytes.from_json(keyval["value"]) for keyval in vector["pre_state"]["keyvals"]}
                state = setup_state(db, pre_data)
            else:
                state = setup_state(GhostState.genesis(genesis_path=gen_path), db)
            print(state.root.hex())
            state.transition(block)
            pre_data = {Bytes.from_json(keyval["key"]):Bytes.from_json(keyval["value"]) for keyval in vector["pre_state"]["keyvals"]}

            print("After transition state root",state.root.hex()==vector["post_state"]["state_root"][2:])
