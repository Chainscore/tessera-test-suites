from typing import Dict, Tuple
from jam.state.ghost import GhostState
from jam.block.block import Block
from jam.types.state.delta import Delta
from jam.state.transitions import Preimages
from jam.types.state.pi import AllServiceStats, Pi
from jam.types.state.sigma import Sigma

from jam.block.extrinsics.preimages import PreimagesExtrinsic
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


def subset_to_compare(state: Sigma) -> Tuple:
    """
    Pull out only the fields we actually want to assert on
    (validator‐stats and slot in this example).
    """
    return (
        state.delta,
        state.pi.services,
    )


transition = Preimages.transition

spec="data"
