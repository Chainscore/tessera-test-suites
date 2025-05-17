from jam.consensus.safrole.safrole import Safrole
from jam.utils.dummy.dummy_block import create_dummy_block


def transform_block(input: dict) -> dict:
    block = create_dummy_block()
    block["extrinsic"]["tickets"] = input["extrinsic"]
    block["header"]["slot"] = input["slot"]
    block["header"]["epoch_mark"]["entropy"] = input["entropy"]
    return block

def transform_state(state: dict) -> dict:
    state["gamma"] = {}
    if "gamma_k" in state:
        state["gamma"]["k"] = state["gamma_k"]
        del state["gamma_k"]
    if "gamma_z" in state:
        state["gamma"]["z"] = state["gamma_z"]
        del state["gamma_z"]
    if "gamma_s" in state:
        state["gamma"]["s"] = state["gamma_s"]
        del state["gamma_s"]
    if "gamma_a" in state:
        state["gamma"]["a"] = state["gamma_a"]
        del state["gamma_a"]

    state["psi"] = {
        "good": [],
        "bad": [],
        "wonky": [],
        "offenders" : state["post_offenders"]
    }
    return state

transition = Safrole.transition