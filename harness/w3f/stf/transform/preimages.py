from pathlib import Path
from typing import Dict, Tuple
from jam.state.ghost import GhostState
from jam.block.block import Block
from jam.state.state import State
from jam.state.utils import construct_state_key
from jam.types.state.delta import Delta
from jam.state.transitions import Preimages
from jam.types.state.pi import AllCoreStats, AllServiceStats, AllValidatorStats, Pi
from jam.types.state.sigma import Sigma
from harness.w3f.stf.types import InputAccounts
from jam.block.extrinsics.preimages import PreimagesExtrinsic
from jam.types.state.tau import Tau


def transform_block(vector_input: dict) -> (Block, Dict):
    block = Block.genesis()
    block.header.slot = Tau(vector_input["slot"])
    block.extrinsic.preimages = PreimagesExtrinsic.from_json(vector_input["preimages"])
    return block, {}


def transform_state(vector_state: dict) -> Sigma:
    state = {}
    services_stats = AllServiceStats.from_json(vector_state["statistics"])
    state[construct_state_key(13)] = Pi(
        vals_current=AllValidatorStats.empty(),
        vals_last=AllValidatorStats.empty(),
        cores=AllCoreStats.empty(),
        services=services_stats
    ).encode()    
    state.update(
        Delta.from_json(vector_state["accounts"]).transform()
    )
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

transition = Preimages.transition

spec="data"
