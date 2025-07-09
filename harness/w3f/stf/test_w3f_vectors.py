import json
import importlib
from copy import deepcopy
from pathlib import Path
import shutil
from jam.error import JamError
from jam.settings import setup_setting
from jam.state.state import setup_state

STF_ROOT = Path(__file__).parents[3] / "ext" / "w3f" / "stf"

def fetch_vectors(module: str, spec: str, pattern: str):
    vector_dir = STF_ROOT / module / spec
    return [
        (f.name, json.load(open(f)))
        for f in vector_dir.glob(pattern)
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

def run_case(name: str, vector: dict, tblock, tstate, transition, subset_to_compare, settings):
    
    # build inputs
    input_block, args   = tblock(vector["input"])
    pre_state           = tstate(vector["pre_state"])
    
    setup_state(settings.state_db, pre_state)
    try:
        # expected + actual post-states
        post_expect = tstate(vector["post_state"])
        post_actual = transition(tstate(vector["pre_state"]), input_block, **args)

        if vector["output"]:
            assert vector["output"].get("err") is None
        # now just compare the *subset* of fields you actually care about
        expect_sub = subset_to_compare(post_expect)
        actual_sub = subset_to_compare(post_actual)

        from deepdiff import DeepDiff
        for ours, thiers in zip(expect_sub,actual_sub):
            value_diff = DeepDiff(thiers.to_json(), ours.to_json(), significant_digits=0, verbose_level=2)
            assert value_diff == {}, f"\nValue Diff: {name}\nDiff:\n{value_diff.pretty()}"
            # types_diff = DeepDiff(thiers, ours, significant_digits=0, verbose_level=2)
            # assert value_diff == {}, f"\nValue Diff: {name}\nDiff:\n{types_diff.pretty()}"

    except JamError as e:
        assert vector["output"].get("err") == e.code.value

def test_stf_vectors(module, spec, pattern):
    print("mod", module, spec, pattern)
    tblock, tstate, transition, compare_state = load_stf_module(module)
    shutil.rmtree("data/tmp")
    for name, vector in fetch_vectors(module, spec, pattern):
        print(f"\n ⏭️ Running test case {name} ...")
        settings = setup_setting(f"data/tmp/{name}/", 1) 
        run_case(name, vector, tblock, tstate, transition, compare_state, settings)
        print("✅ Passed")
