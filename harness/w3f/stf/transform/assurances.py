from typing import Dict
from jam.state.ghost import GhostState
from jam.types.block import Block
from jam.types.extrinsics.assurances import AssurancesExtrinsic
from jam.assurances.assurances import Assurances
from jam.types.protocol.crypto import HeaderHash
from jam.types.state.kappa import Kappa
from jam.types.state.rho import Rho
from jam.types.state.sigma import Sigma
from jam.types.state.tau import Tau


def transform_block(vector_input: dict) -> (Block, Dict):
    block = Block.genesis()
    block.header.slot = Tau(vector_input["slot"])
    block.header.parent = HeaderHash(vector_input["parent"])
    block.extrinsic.assurances = AssurancesExtrinsic.from_json(
        vector_input["assurances"]
    )
    return block, {}


def transform_state(vector_state: dict) -> Sigma:
    state = GhostState.genesis()
    state.rho = Rho.from_json(vector_state["avail_assignments"])
    state.kappa = Kappa.from_json(vector_state["curr_validators"])
    return state


def compare_state(state: Sigma) -> dict:
    """
    Pull out only the fields we actually want to assert on
    (validator‐stats and slot in this example).
    """
    return {
        "avail_assignments": state.rho.to_json(),
        "curr_validators": state.kappa.to_json(),
    }


transition = Assurances.transition
