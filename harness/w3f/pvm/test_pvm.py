import json, importlib
from copy import deepcopy
from pathlib import Path

from jam.consensus.safrole.errors import SafroleError

STF_ROOT = Path(__file__).parents[3] / "ext" / "w3f"

def fetch_vectors(module: str, spec: str, pattern: str):
    vector_dir = STF_ROOT / module / spec
    return [
        (f.name, json.load(open(f)))
        for f in vector_dir.glob(pattern)
    ]

def load_stf_module(module: str):
    mod = importlib.import_module(f"harness.w3f.stf.transform.{module}")
    return mod.transform_block, mod.transform_state, mod.transition

def run_case(name: str, vector: dict, tblock, tstate, transition):
    input_block, args = tblock(vector["input"])
    pre_state   = tstate(vector["pre_state"])
    try:
        post_expect = tstate(vector["post_state"])
        post_actual = transition(deepcopy(pre_state), input_block, **args)
        from deepdiff import DeepDiff
        value_diff = DeepDiff(post_actual.to_json(), post_expect.to_json(), significant_digits=0, verbose_level=2)
        assert value_diff == {}, f"\nValue Diff: {name}\nDiff:\n{value_diff.pretty()}"
        types_diff = DeepDiff(post_actual, post_expect, significant_digits=0, verbose_level=2)
        assert value_diff == {}, f"\nValue Diff: {name}\nDiff:\n{types_diff.pretty()}"
    except SafroleError as e:
        if "err" in vector["output"]:
            assert vector["output"].get("err") == e.code._value_
        else:
            raise e

def test_stf_vectors(module, spec, pattern):
    tblock, tstate, transition = load_stf_module(module)
    for name, vector in fetch_vectors(module, spec, pattern):
        print(f"\n ⏭️Running test case {name} ...")
        run_case(name, vector, tblock, tstate, transition)
        print("✅Passed")