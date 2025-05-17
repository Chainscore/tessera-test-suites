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
    post_expect = tstate(vector["post_state"])
    try:
        post_actual = transition(deepcopy(pre_state), input_block, **args)
        assert post_actual.alpha == post_expect.alpha
        assert post_actual.beta == post_expect.beta
        assert post_actual.gamma == post_expect.gamma
        assert post_actual.eta == post_expect.eta
        assert post_actual.delta == post_expect.delta
        assert post_actual.iota == post_expect.iota
        assert post_actual.kappa == post_expect.kappa
        assert post_actual.lambda_ == post_expect.lambda_
        assert post_actual.rho == post_expect.rho
        assert post_actual.phi == post_expect.phi
        assert post_actual.chi == post_expect.chi
        assert post_actual.psi == post_expect.psi
        assert post_actual.tau == post_expect.tau
        assert post_actual.pi == post_expect.pi
        assert post_actual.nu == post_expect.nu
        assert post_actual.xi == post_expect.xi
    except SafroleError as e:
        if "err" in vector["output"]:
            assert vector["output"].get("err") == e.code._value_
        else:
            raise e

def test_stf_vectors(module, spec, pattern):
    tblock, tstate, transition = load_stf_module(module)
    for name, vector in fetch_vectors(module, spec, pattern):
        print(f"Running test case {name}")
        run_case(name, vector, tblock, tstate, transition)