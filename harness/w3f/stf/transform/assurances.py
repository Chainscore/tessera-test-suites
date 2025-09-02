from pathlib import Path
from typing import Dict, Tuple
from jam.state.ghost import GhostState
from jam.block.block import Block
from jam.block.extrinsics.assurances import AssurancesExtrinsic
from jam.state.state import State
from jam.state.transitions import Assurances
from jam.state.utils import construct_state_key
from jam.types.protocol.crypto import HeaderHash
from jam.types.state.kappa import Kappa
from jam.types.state.rho import Rho
from jam.types.state.sigma import Sigma
from jam.types.state.tau import Tau


def transform_block(vector_input: dict) -> (Block, Dict):
    block = Block.genesis()
    block.header.slot = Tau(vector_input["slot"])
    block.header.parent = HeaderHash.from_json(vector_input["parent"])
    block.extrinsic.assurances = AssurancesExtrinsic.from_json(vector_input["assurances"])
    return block, {}


def transform_state(vector_state: dict) -> Sigma:
    state = {}
    state[construct_state_key(10)] = Rho.from_json(vector_state["avail_assignments"]).encode()
    state[construct_state_key(8)] = Kappa.from_json(vector_state["curr_validators"]).encode()
    return {key.hex(): value.hex() for key, value in state.items()}

def subset_to_compare(state) -> Tuple:
    """
    Pull out only the fields we actually want to assert on
    """
    if isinstance(state, State):
        data = {k.hex(): v.hex() for k, v in state.store._DB.get_all().items()}
    else:
        data = state
    data[construct_state_key(13).hex()] = bytes(32).hex()
    return data


def transition(pre_state, state, block):
    _, new_wrs = Assurances.transition(pre_state, state, block)
    return state
