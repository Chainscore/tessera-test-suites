import json
from pathlib import Path

from jam.config.logging import logger
from jam.state.ghost import GhostState
from jam.state.merkle import StateTrie
from jam.state.state import State, setup_state, set_state
from rockstore import RockStore
from jam.types.base import Bytes
from jam.types.block import Block
from jam.types.protocol.core import ServiceId

TRACE_ROOT = Path(__file__).parents[3] / "ext" / "jamduna" / "data"

def fetch_vectors(module: str, pattern: str):
    vector_dir = TRACE_ROOT / module / "state_transitions"

    return [
        (f.name, json.load(open(f)))
        for f in vector_dir.glob(pattern)
    ]


def test_traces(module, pattern, db_path, spec):
    db_path = db_path + '/kadjhfo'
    db = RockStore(db_path)
    post_db = RockStore(db_path + "/post")
    for name, vector in fetch_vectors(module, pattern):
        print(f"\n ⏭️Running test case {name} ...")
        try:
            block = Block.from_json(vector["block"])

            gen_path = Path(__file__).parent / "genesis.json"

            if len(vector["pre_state"]["keyvals"]) != 0:
                trie = StateTrie()
                pre_data = {Bytes(keyval["key"]):Bytes(keyval["value"]) for keyval in vector["pre_state"]["keyvals"]}
                trie.merkelize(pre_data, db)
                state = State(db, trie)
                set_state(state)
            else:
                state = setup_state(GhostState.genesis(genesis_path=gen_path), db)

            state.transition(block)

            from deepdiff import DeepDiff
            actual = {key.hex(): value.hex() for key, value in state.DB.get_all().items()}
            expected = {bytes.fromhex(keyval["key"][2:]).hex(): bytes.fromhex(keyval["value"][2:]).hex() for keyval in vector["post_state"]["keyvals"]}
            value_diff = DeepDiff(actual, expected, significant_digits=0, verbose_level=2, view="tree")
            assert value_diff == {}, f"\nValue Diff: {name}\nDiff:\n{value_diff.pretty()}"
            assert str(state.root) == vector["post_state"]["state_root"]
            print("✅Passed")
        except Exception as e:
            print(f"❌ Failed test case {name}: {e}")
    else:
        assert False, "😿 Failed: No matching test vectors found"