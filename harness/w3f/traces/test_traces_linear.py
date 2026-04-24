import json
from jam.state.utils import construct_state_key
from jam.types.state.delta import AccountMetadata
import pytest
from pathlib import Path

from jam.types import Beta, Gamma, Pi, Kappa

from tsrkit_types import Bytes

from jam.log_setup import logger, setup_logging
from jam.block.block import Block

TRACE_ROOT = Path(__file__).parents[3] / "ext" / "w3f-davxy"

def fetch_vector(module: str, pattern: str):
    vector_dir = TRACE_ROOT / "traces" / module
    return [
        (f.name, json.load(open(f)))
        for f in vector_dir.glob(pattern.replace('"', '').replace("'", ""))
    ]

setup_logging("dracula", "test-linear-traces")

@pytest.mark.asyncio
async def test_traces(module, pattern, db_path, rpc, jam_node):
    block_n = 1

    from jam.state.state import State

    while True:
        try:
            name, vector = fetch_vector(module, f"{''.join(['0' for _ in range(8 - len(str(block_n)))])}{block_n}.json")[0]
            print(f"\n ⏭️Running test case {name} ...")
        except IndexError as e:
            print("Finished!", f"{''.join(['0' for _ in range(8 - len(str(block_n)))])}{block_n}.json", "not found.")
            break

        if block_n == 1:
            pre_data = {Bytes.from_json(keyval["key"]):Bytes.from_json(keyval["value"]) for keyval in vector["pre_state"]["keyvals"]}
            state = State.from_keyvals(pre_data, jam_node)
            state.store.enable_writes()
            state.store.enable_cache()
            # CRITICAL: Set jam_node.state so that _force_transition() uses our state via self.load()
            jam_node.state = state

        assert state.root.hex() == vector["pre_state"]["state_root"][2:]
        block = Block.from_json(vector["block"])

        pre_gamma = state.gamma

        logger.info("Starting transition...")
        state._force_transition(block)

        from deepdiff import DeepDiff

        actual = {key.hex(): value.hex() for key, value in state.store._DB.get_all().items()}
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