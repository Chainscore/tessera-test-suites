from typing import Dict, Tuple
from jam.consensus.safrole.safrole import Safrole
from jam.state.ghost import GhostState
from jam.types.block import Block
from jam.types.block.extrinsics.tickets import TicketsExtrinsic
from jam.types.protocol.crypto import OpaqueHash
from jam.types.state.eta import Eta
from jam.types.state.gamma import Gamma
from jam.types.state.iota import Iota
from jam.types.state.kappa import Kappa
from jam.types.state.lambda_ import Lambda_
from jam.types.state.psi import PsiO
from jam.types.state.sigma import Sigma
from jam.types.state.tau import Tau


def transform_block(vector_input: dict) -> (Block, Dict):
    block = Block.genesis()
    block.extrinsic.tickets = TicketsExtrinsic.from_json(vector_input["extrinsic"])
    block.header.slot = Tau(vector_input["slot"])
    return block, {"entropy": OpaqueHash.from_json(vector_input["entropy"])}


def transform_state(vector_state: dict) -> Sigma:
    state = GhostState.genesis()
    state.gamma = Gamma.from_json(vector_state)
    state.psi.offenders = PsiO.from_json(vector_state["post_offenders"])
    state.eta = Eta.from_json(vector_state["eta"])
    state.tau = Tau.from_json(vector_state["tau"])
    state.lambda_ = Lambda_.from_json(vector_state["lambda"])
    state.kappa = Kappa.from_json(vector_state["kappa"])
    state.iota = Iota.from_json(vector_state["iota"])
    return state


def subset_to_compare(state: Sigma) -> Tuple:
    """
    Pull out only the fields we actually want to assert on
    (validator‐stats and slot in this example).
    """
    return (
        state.tau,
        state.psi.offenders,
        state.eta,
        state.lambda_,
        state.kappa,
        state.gamma,
        state.iota,
    )


transition = Safrole.transition
