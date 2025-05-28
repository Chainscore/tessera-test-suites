from ast import mod
import importlib
from copy import deepcopy
import json
from pathlib import Path
from jam.config.logging import logger
from jam.state.ghost import GhostState
from jam.state.merkle import StateTrie
from jam.state.state import State, setup_state, set_state
from jam.storage.db.kv import KVStore
from jam.types.base import Bytes
from jam.types.block import Block
from jam.types.protocol.core import ServiceId

from jam.assurances.assurances import AssurancesError
from jam.consensus.safrole.errors import SafroleError
from jam.error import JamError
from jam.preimages.errors import PreimageError
from jam.disputes.error import DisputesError

STF_ROOT = Path(__file__).parents[3] / "ext" / "jamduna" / "data" 
print("STF_ROOT", STF_ROOT)

def fetch_vectors(module: str, pattern: str):
    vector_dir = STF_ROOT / module / "state_transitions" 
    
    return [
        (f.name, json.load(open(f)))
        for f in vector_dir.glob(pattern)
    ]

def load_stf_module(module: str):
    mod = importlib.import_module(f"harness.jamduna.stf.transform.{module}")
    # now also pull in compare_state
    return (
        mod.t_kv_pre_state,
        mod.t_kv_post_state,
        mod.transform_state,
        mod.subset_to_compare,
        mod.transition,

    )


def test_traces(module, pattern, spec, db_path):
    db_path = db_path + '/kadjhfo'
    db = KVStore(db_path)
    post_db = KVStore(db_path + "/post")
    t_kv_pre_state, t_kv_post_state, transform_state, subset_to_compare, transition = load_stf_module(module)

    for name, vector in fetch_vectors(module, pattern):
        print(f"\n ⏭️Running test case {name} ...")
        try:
            kv_pre_state = t_kv_pre_state(vector, db)
            pre_state = transform_state(kv_pre_state)
            input_block = Block.from_json(vector["block"])
            post_actual = transition(pre_state, input_block)
            kv_post_state = t_kv_post_state(vector, post_db)
            post_state = transform_state(kv_post_state)
            post_expect = transform_state(post_state)
            post_actual = transition(deepcopy(pre_state), input_block)

            expect_sub = subset_to_compare(post_expect)
            actual_sub = subset_to_compare(post_actual)

            from deepdiff import DeepDiff
            for ours, thiers in zip(expect_sub, actual_sub):
                value_diff = DeepDiff(thiers.to_json(), ours.to_json(), significant_digits=0, verbose_level=2)
                assert value_diff == {}, f"\nValue Diff: {name}\nDiff:\n{value_diff.pretty()}"
        except Exception as e:
            logger.error(f"Error in test case {name}: {e}", exc_info=True)
            print(f"❌ Failed test case {name}: {e}")
            continue

        print("✅Passed")
