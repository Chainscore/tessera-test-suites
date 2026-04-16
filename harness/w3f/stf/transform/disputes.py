from pathlib import Path
from typing import List, Tuple, Dict


from jam.state.state import State
from jam.state.transitions import Disputes
from jam.state.ghost import GhostState

# from jam.state.state import GhostState, State
# from jam.types import Boolean
from jam.state.utils import construct_state_key
from jam.types.state.rho import Rho
from jam.block.block import Block

# from tests.unit.disputes.types import (
#     Input,
#     PreState,
#     Testcase,
#     get_testcases_starting_with,
# )j

from jam.types.state.psi import Psi
from jam.types.state.sigma import Sigma
from jam.types.state.tau import Tau
from jam.types.state.lambda_ import Lambda_

from jam.block.extrinsics.disputes import DisputesExtrinsic


def transform_block(vector_input: dict) -> (Block, Dict):
    block = Block.genesis()
    block.extrinsic.disputes = DisputesExtrinsic.from_json(vector_input["disputes"])
    return block, {}


def transform_state(vector_state: dict) -> Sigma:
    state = {}
    state[construct_state_key(5)] = Psi.from_json(vector_state["psi"]).encode()
    state[construct_state_key(11)] = Tau.from_json(vector_state["tau"]).encode()
    state[construct_state_key(10)] = Rho.from_json(vector_state["rho"]).encode()
    state[construct_state_key(9)] = Lambda_.from_json(vector_state["lambda"]).encode()
    state[construct_state_key(8)] = Lambda_.from_json(vector_state["kappa"]).encode()
    return {key.hex(): value.hex() for key, value in state.items()}


def subset_to_compare(state: Sigma) -> Tuple:
    """
    Pull out only the fields we actually want to assert on
    (validator‐stats and slot in this example).
    """
    if isinstance(state, State):
        data = {k.hex(): v.hex() for k, v in state.store._DB.get_all().items()}
    else:
        data = state
    return data


transition = Disputes.transition
