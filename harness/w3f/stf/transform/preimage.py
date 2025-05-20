from typing import Dict
from jam.state.ghost import GhostState
from jam.types.block import Block
from jam.types.state.sigma import Sigma
from jam.types.extrinsics.preimages import PreimagesExtrinsic
from jam.types.state.tau import Tau


def transform_block(vector_input: dict) -> (Block, Dict):
    block = Block.genesis()
    block.header.slot = Tau(vector_input["slot"])
    block.extrinsic.preimages = PreimagesExtrinsic.from_json(vector_input["preimages"])
    return block, {}


def transform_state(vector_state: dict) -> Sigma:
    state = GhostState.genesis()
    state.psi = Psi.from_json(vector_state["psi"])
    # state.rho=Rho.from_json(vector_state["rho"])
    state.tau = Tau.from_json(vector_state["tau"])
    state.rho = Rho.from_json(vector_state["rho"])
    state.lambda_ = Lambda_.from_json(vector_state["lambda"])

    return state


def compare_state(state: Sigma) -> dict:
    """
    Pull out only the fields we actually want to assert on
    (validator‐stats and slot in this example).
    """
    return {
        "slot": int(state.tau),
        "vals_curr_stats": state.pi.vals_current.to_json(),
        "vals_last_stats": state.pi.vals_last.to_json(),
        "curr_validators": state.kappa.to_json(),
        # if you do want to check core‐ or service‐stats you can
        # add them here:
        # "cores_stats": state.pi.cores.to_json(),
        # "services_stats": state.pi.services.to_json(),
    }


transition = Disputes.transition
