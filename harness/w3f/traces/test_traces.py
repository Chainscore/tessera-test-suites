import json, importlib
from copy import deepcopy
from pathlib import Path

from jam.consensus.safrole.errors import SafroleError
from jam.state.ghost import GhostState
from jam.state.merkle import StateTrie
from jam.state.state import State, setup_state
from jam.storage.db.kv import KVStore
from jam.types.base import Dictionary, decodable_dictionary, ByteArray32, Bytes
from jam.types.block import Block

TRACE_ROOT = Path(__file__).parents[3] / "ext" / "w3f-w-traces"

def fetch_vectors(module: str, end: str):
    vector_dir = TRACE_ROOT / "traces" / module
    print(vector_dir)
    return [
        (f.name, json.load(open(f)))
        for f in vector_dir.glob("*.json") if int(f.name.split(".")[0]) < int(end)
    ]


def test_traces(module, end, db_path):
    print(f"module {module} | end {end} | db_path {db_path}")
    for name, vector in fetch_vectors(module, end):
        print(f"\n ⏭️Running test case {name} ...")
        db = KVStore(db_path)
        block = Block.from_json(vector["block"])
        keyvals = vector["pre_state"]["keyvals"]
        state = setup_state(GhostState.genesis(), db)
        if len(keyvals) != 0:
            trie = StateTrie()
            trie.merkelize({Bytes(keyval["key"]):Bytes(keyval["value"]) for keyval in keyvals}, db)
            state = State(db, trie)

        state.transition(block)

        # assert state.root == vector["post_state"]["state_root"]
        # print("✅Passed")