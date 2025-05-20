import json
import importlib
from copy import deepcopy
from pathlib import Path

from jam.consensus.safrole.errors import SafroleError
from jam.disputes.error import DisputesError, DisputesErrorCode


from deepdiff import DeepDiff

STF_ROOT = Path(__file__).parents[3] / "ext" / "w3f"

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
        mod.compare_state,
    )

def run_case(name: str, vector: dict,
             tblock, tstate, transition, compare_state):
    # build inputs
    input_block, args = tblock(vector["input"])
    pre_state       = tstate(vector["pre_state"])

    try:
        # expected + actual post-states
        post_expect = tstate(vector["post_state"])
        post_actual = transition(deepcopy(pre_state), input_block, **args)

        # now just compare the *subset* of fields you actually care about
        expect_sub = compare_state(post_expect)
        actual_sub = compare_state(post_actual)

        diff = DeepDiff(actual_sub, expect_sub,
                        significant_digits=0,
                        verbose_level=2)
        assert diff == {}, f"\nState Diff: {name}\n{diff.pretty()}"

    except Exception as e:
        # only handle SafroleError or DisputesError here:
        if isinstance(e, (SafroleError, DisputesError)):
            if "err" in vector["output"]:
                # print("Byaah",e.code._value_,vector["output"].get("err"))

                assert vector["output"].get("err") == e.code._value_
            else:
                raise e
        else:
            # re-raise any other unexpected exception
            raise e

def test_stf_vectors(module, spec, pattern):
    tblock, tstate, transition, compare_state = load_stf_module(module)
    for name, vector in fetch_vectors(module, spec, pattern):
        print(f"\n ⏭️ Running test case {name} ...")
        run_case(name, vector, tblock, tstate, transition, compare_state)
        print("✅ Passed")
