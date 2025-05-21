from typing import Dict, Tuple

from jam.state.ghost import GhostState
from jam.types.block import Block
from jam.types.state.sigma import Sigma
from jam.types.state.beta import Beta
from jam.types.header import Header
from jam.recent_history.recent_history import OpaqueHash, RecentHistory


def transform_block(vector_input: dict) -> (Block, Dict):
    block = Block.genesis()
    block.header.parent = OpaqueHash(vector_input["header_hash"])
    block.header.parent_state_root = OpaqueHash(vector_input["parent_state_root"])

    return block, {"accumulate_root": OpaqueHash(vector_input["accumulate_root"])}


def transform_state(vector_state: dict) -> Sigma:
    state = GhostState.genesis()
    for beta in vector_state["beta"]:
        beta["mmr"]=beta["mmr"]["peaks"]
    state.beta = Beta.from_json(vector_state["beta"])
    return state


def subset_to_compare(state: Sigma) -> Tuple:
    """
    Pull out only the fields we actually want to assert on
    (validator‐stats and slot in this example).
    """
    print("beta bhai",state.beta)
    return (
        state.beta,
    )


transition = RecentHistory.transition
