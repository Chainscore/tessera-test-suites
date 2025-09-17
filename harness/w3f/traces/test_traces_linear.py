import json
from jam.state.utils import construct_state_key
from jam.types.state.delta import AccountMetadata
import pytest
import os
from pathlib import Path

from jam.types import Beta, Eta, Gamma, Pi

from tsrkit_types import Bytes

from jam.log_setup import logger, setup_logging
from jam.state.state import State, setup_state, set_state
from jam.block.block import Block

TRACE_ROOT = Path(__file__).parents[3] / "ext" / "w3f-davxy"

def fetch_vector(module: str, pattern: str):
    vector_dir = TRACE_ROOT / "traces" / module
    return [
        (f.name, json.load(open(f)))
        for f in vector_dir.glob(pattern.replace('"', '').replace("'", ""))
    ]

setup_logging("default", "test-linear-traces")

@pytest.mark.asyncio
async def test_traces(module, pattern, db_path):
    db_path = db_path
    block_n = 1

    from jam.state.state import state as _state
    state = _state

    from jam.settings import setup_setting
    settings = setup_setting(db_path, 1)

    while True:
        try:
            name, vector = fetch_vector(module, f"{"".join(["0" for _ in range(8 - len(str(block_n)))])}{block_n}.json")[0]
            print(f"\n ⏭️Running test case {name} ...")
        except IndexError as e:
            print("Finished!", f"{"".join(["0" for _ in range(8 - len(str(block_n)))])}{block_n}.json", "not found.")
            break 

        if block_n == 1:
            pre_data = {Bytes.from_json(keyval["key"]):Bytes.from_json(keyval["value"]) for keyval in vector["pre_state"]["keyvals"]}
            state = setup_state(settings.state_db, pre_data)
        
        assert state.root.hex() == vector["pre_state"]["state_root"][2:]
        block = Block.from_json(vector["block"])

        pre_gamma = state.gamma

        logger.info("Starting transition...")
        state.transition(block)

        from deepdiff import DeepDiff

        # post_data = {Bytes.from_json(keyval["key"]): Bytes.from_json(keyval["value"]) for keyval in vector["post_state"]["keyvals"]}
        # post_trie = StateTrie()
        # post_trie.merkelize(post_data, post_db)
        # post_state = State(post_db, post_trie)
        #
        # if post_state.pi != state.pi:
        #     print("MISMATCHED PI")
        #     print("DIFF", DeepDiff(state.pi.to_json(), post_state.pi.to_json(), significant_digits=0, verbose_level=2, view="tree"))
        #     print("PRE PI", PRE_PI)
        # if post_state.rho != state.rho:
        #     print("MISMATCHED RHO")
        #     print("DIFF", DeepDiff(state.rho.to_json(), post_state.rho.to_json(), significant_digits=0, verbose_level=2, view="tree"))
        #     print("PRE RHO", PRE_RHO)
        # if post_state.beta != state.beta:
        #     print("MISMATCHED BETA")
        #     print("DIFF", DeepDiff(state.beta.to_json(), post_state.beta.to_json(), significant_digits=0, verbose_level=2, view="tree"))
        #     print("PRE BETA", PRE_BETA)
        #


        actual = {key.hex(): value.hex() for key, value in settings.state_db.get_all().items()}
        expected = {bytes.fromhex(keyval["key"][2:]).hex(): bytes.fromhex(keyval["value"][2:]).hex() for keyval in vector["post_state"]["keyvals"]}
        value_diff = DeepDiff(actual, expected, significant_digits=0, verbose_level=0)
        assert value_diff == {}, f"\nValue Diff: {name}\nDiff:\n{value_diff.pretty()}"
        for k,v in expected.items():
            if k not in actual:
                print("NEW KEY", k, v)
            elif v != actual[k]:
                cls_ = None

                if k == construct_state_key(3).hex(): cls_ = Beta 
                if k == construct_state_key(4).hex(): cls_ = Gamma 
                if k == construct_state_key(13).hex(): cls_ = Pi
                if k == construct_state_key((255, 0)).hex(): cls_ = AccountMetadata
                if cls_: print(
                    "Expected ---\n", 
                    cls_.decode(bytes.fromhex(v)), 
                    "\nActual ---\n", 
                    cls_.decode(bytes.fromhex(actual[k]))
                )
                else: print("DIFF", k, v, actual[k])
        assert state.root.hex() == vector["post_state"]["state_root"][2:]
        print(f"✅Passed block: {block_n}")
        block_n += 1
