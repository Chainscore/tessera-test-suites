import json
import os
from pathlib import Path

import pytest
from tsrkit_types import Bytes

from jam.log_setup import logger, setup_logging
from jam.state.ghost import GhostState
from jam.state.state import State
from rockstore import RockStore
from jam.block.block import Block

TRACE_ROOT = Path(__file__).parents[3] / "ext" / "w3f-davxy"

def fetch_vectors(module: str, pattern: str):
    vector_dir = TRACE_ROOT / "traces" / module
    return [
        (f.name, json.load(open(f)))
        for f in vector_dir.glob(pattern.replace('"', '').replace("'", ""))
    ]

os.environ["LOG_LEVEL_HOST_CALLS"] = "debug"

setup_logging("gruvbox", "test-traces")

# TODO: Currently Block Viewer would only run in case all traces are passed sequentially, using same db.
@pytest.mark.asyncio
async def test_traces(module, pattern, db_path, rpc, jam_node):
    for name, vector in fetch_vectors(module, pattern):
        print(f"\n ⏭️Running test case {name} ...")

        if name == "00000000.json" or name == "genesis.json":
            print("Skipping genesis...")
            continue

        block = Block.from_json(vector["block"])

        gen_path = Path(__file__).parent / "genesis.json"

        if len(vector["pre_state"]["keyvals"]) != 0:
            pre_data = {Bytes.from_json(keyval["key"]):Bytes.from_json(keyval["value"]) for keyval in vector["pre_state"]["keyvals"]}
            state = State.from_keyvals(pre_data, jam_node)
        else:
            from jam.state.ghost import GhostState
            state = GhostState.genesis(genesis_path=gen_path)

        state.store.enable_writes()
        state.store.enable_cache()

        logger.info("Starting transition...")

        PRE_PI = state.pi
        PRE_BETA = state.beta
        PRE_RHO = state.rho

        state._force_transition(block)
        from deepdiff import DeepDiff

        post_data = {Bytes.from_json(keyval["key"]): Bytes.from_json(keyval["value"]) for keyval in vector["post_state"]["keyvals"]}
        post_state = State.from_keyvals(post_data, jam_node)

        if post_state.pi != state.pi:
            print("MISMATCHED PI")
            print("DIFF\n", DeepDiff(state.pi.to_json(), "\n", post_state.pi.to_json(), significant_digits=0, verbose_level=2, view="tree"))
            print("PRE PI", PRE_PI)
        if post_state.rho != state.rho:
            print("MISMATCHED RHO")
            print("DIFF", DeepDiff(state.rho.to_json(), post_state.rho.to_json(), significant_digits=0, verbose_level=2, view="tree"))
            print("PRE RHO", PRE_RHO)
        if post_state.beta != state.beta:
            print("MISMATCHED BETA")
            print("DIFF", DeepDiff(state.beta.to_json(), post_state.beta.to_json(), significant_digits=0, verbose_level=2, view="tree"))
            print("PRE BETA", PRE_BETA)

        actual = {key.hex(): value.hex() for key, value in state.store._DB.get_all().items()}
        expected = {bytes.fromhex(keyval["key"][2:]).hex(): bytes.fromhex(keyval["value"][2:]).hex() for keyval in vector["post_state"]["keyvals"]}
        value_diff = DeepDiff(actual, expected, significant_digits=0, verbose_level=2, view="tree")
        # assert value_diff == {}, f"\nValue Diff: {name}\nDiff:\n{value_diff.pretty()}"
        for k,v in expected.items():
            if k not in actual:
                print("NEW KEY", k, v)
            elif v != actual[k]:
                print("DIFF: ", k, "\nEXP \t", v, "\nACT \t", actual[k], "\nPRE \t", pre_data[Bytes.fromhex(k)].hex() if Bytes.fromhex(k) in pre_data else None)

        try:
            assert state.root.hex() == vector["post_state"]["state_root"][2:]
            print("✅Passed")
        except Exception as e:
            print("❌Failed", type(e), str(e))

