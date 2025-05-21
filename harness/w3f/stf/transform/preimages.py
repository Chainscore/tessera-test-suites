from typing import Dict
from jam.state.ghost import GhostState
from jam.types.block import Block
from jam.types.state.delta import Delta
from jam.preimages.preimages import Preimages
from jam.types.state.pi import AllServiceStats, Pi
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
    state.pi.services = AllServiceStats.from_json(vector_state["statistics"])
    state.delta = Delta.from_json(vector_state["accounts"])
    return state


def compare_state(state: Sigma) -> dict:
    """
    Pull out only the fields we actually want to assert on
    (validator‐stats and slot in this example).
    """
    return {
        "accounts": state.delta.to_json(),
        "statistics": state.pi.services.to_json(),
    }


transition = Preimages.transition
