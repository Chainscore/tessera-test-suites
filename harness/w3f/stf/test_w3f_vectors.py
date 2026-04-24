import json
import importlib
from pathlib import Path
import shutil
import pytest
from jam.error import JamError
from jam.types import ServiceId

STF_ROOT = Path(__file__).parents[3] / "ext" / "w3f-davxy" / "stf"

def fetch_vectors(module: str, spec: str, pattern: str):
    vector_dir = STF_ROOT / module / spec
    return [
        (f.name, json.load(open(f)))
        for f in vector_dir.glob(pattern.replace('"', '').replace("'", ""))
    ]

def load_stf_module(module: str):
    mod = importlib.import_module(f"harness.w3f.stf.transform.{module}")
    # now also pull in compare_state
    return (
        mod.transform_block,
        mod.transform_state,
        mod.transition,
        mod.subset_to_compare,
    )

def run_case(name: str, vector: dict, tblock, tstate, transition, subset_to_compare, jam_node):
    from jam.state.state import State

    # build inputs
    input_block, args   = tblock(vector["input"])
    pre_state           = tstate(vector["pre_state"])

    # Create state directly from keyvals using jam_node
    state = State.from_keyvals(pre_state, jam_node)
    state.store.enable_writes()
    state.store.enable_cache()

    try:
        # expected + actual post-states
        post_expect = tstate(vector["post_state"])
        # pass state itself as pre_state since we're building from vector pre_state
        transition(state, state, input_block, **args)

        # Apply changes to State Trie
        state.store.record_cache()
        state.store.settle_cache()

        if vector["output"]:
            assert vector["output"].get("err") is None

        # now just compare the *subset* of fields you actually care about
        expect_sub = subset_to_compare(post_expect)
        actual_sub = subset_to_compare(state)

        from deepdiff import DeepDiff
        diff = DeepDiff(actual_sub, expect_sub, significant_digits=0, verbose_level=1)
        assert diff == {}

    except JamError as e:
        assert vector["output"].get("err") == e.code.value


@pytest.mark.asyncio
async def test_stf_vectors(module, spec, pattern, rpc, jam_node):
    tblock, tstate, transition, compare_state = load_stf_module(module)
    for name, vector in fetch_vectors(module, spec, pattern):
        print(f"\n ⏭️ Running test case {name} ...")
        run_case(name, vector, tblock, tstate, transition, compare_state, jam_node)
        print("✅ Passed")
