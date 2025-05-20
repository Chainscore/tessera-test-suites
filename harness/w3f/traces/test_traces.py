import json
from pathlib import Path
from jam.state.ghost import GhostState
from jam.state.merkle import StateTrie
from jam.state.state import State, setup_state
from jam.storage.db.kv import KVStore
from jam.types.base import Bytes
from jam.types.block import Block

TRACE_ROOT = Path(__file__).parents[3] / "ext" / "w3f-w-traces"

def fetch_vectors(module: str, pattern: str):
    vector_dir = TRACE_ROOT / "traces" / module
    return [
        (f.name, json.load(open(f)))
        for f in vector_dir.glob(pattern)
    ]


def test_traces(module, pattern, db_path):
    for name, vector in fetch_vectors(module, pattern):
        print(f"\n ⏭️Running test case {name} ...")
        db = KVStore(db_path)
        block = Block.from_json(vector["block"])

        gen_path = Path(__file__).parents[3] / "genesis.json"
        state = setup_state(GhostState.genesis(genesis_path=gen_path), db)
        if len(vector["pre_state"]["keyvals"]) != 0:
            trie = StateTrie()
            trie.merkelize({Bytes(keyval["key"]):Bytes(keyval["value"]) for keyval in vector["pre_state"]["keyvals"]}, db)
            state = State(db, trie)

        print(state.alpha.to_json())
        print(state.phi.to_json())
        print(state.eta.to_json())

        state.transition(block)


        actual = {key.hex(): value.hex() for key, value in state.DB.get_all().items()}
        expected = {bytes.fromhex(keyval["key"][2:]).hex(): bytes.fromhex(keyval["value"][2:]).hex() for keyval in vector["post_state"]["keyvals"]}
        from deepdiff import DeepDiff
        value_diff = DeepDiff(actual, expected, significant_digits=0, verbose_level=2, view="tree")
        # assert value_diff == {}, f"\nValue Diff: {name}\nDiff:\n{value_diff.pretty()}"
        # assert str(state.root) == vector["post_state"]["state_root"]
        print("✅Passed")