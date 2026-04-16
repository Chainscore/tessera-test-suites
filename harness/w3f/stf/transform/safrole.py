from pathlib import Path
from typing import Dict, Tuple
from jam.state.state import State
from jam.state.transitions import Safrole
from jam.state.ghost import GhostState
from jam.block.block import Block
from jam.block.extrinsics.tickets import TicketsExtrinsic
from jam.state.utils import construct_state_key
from jam.types.protocol.crypto import OpaqueHash
from jam.types.state.eta import Eta
from jam.types.state.gamma import Gamma
from jam.types.state.iota import Iota
from jam.types.state.kappa import Kappa
from jam.types.state.lambda_ import Lambda_
from jam.types.state.psi import Psi, PsiB, PsiG, PsiO, PsiW
from jam.types.state.sigma import Sigma
from jam.types.state.tau import Tau


def transform_block(vector_input: dict) -> (Block, Dict):
    block = Block.genesis()
    block.extrinsic.tickets = TicketsExtrinsic.from_json(vector_input["extrinsic"])
    block.header.slot = Tau(vector_input["slot"])
    return block, {"entropy": OpaqueHash.from_json(vector_input["entropy"])}


def transform_state(vector_state: dict) -> Sigma:
    state = {}
    state[construct_state_key(4)] = Gamma.from_json(vector_state).encode()
    state[construct_state_key(5)] = Psi(
        good=PsiG([]),
        bad=PsiB([]),
        wonky=PsiW([]),
        offenders=PsiO.from_json(vector_state["post_offenders"])
    ).encode()
    state[construct_state_key(6)] = Eta.from_json(vector_state["eta"]).encode()
    state[construct_state_key(11)] = Tau.from_json(vector_state["tau"]).encode()
    state[construct_state_key(9)] = Lambda_.from_json(vector_state["lambda"]).encode()
    state[construct_state_key(8)] = Kappa.from_json(vector_state["kappa"]).encode()
    state[construct_state_key(7)] = Iota.from_json(vector_state["iota"]).encode()
    return {key.hex(): value.hex() for key, value in state.items()}

def subset_to_compare(state: Sigma) -> Tuple:
    """
    Pull out only the fields we actually want to assert on
    """
    if isinstance(state, State):
        data = {k.hex(): v.hex() for k, v in state.store._DB.get_all().items()}
    else:
        data = state
    return data


transition = Safrole.transition
