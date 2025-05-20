from typing import Dict

from jam.consensus.safrole.safrole import Safrole
from jam.state.ghost import GhostState
from jam.types.block import Block
from jam.types.extrinsics.tickets import TicketsExtrinsic
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
    return block, {"entropy": OpaqueHash(vector_input["entropy"])}


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


def compare_state(state: Sigma) -> dict:
    """
    Pull out only the fields we actually want to assert on
    (validator‐stats and slot in this example).
    """
    return {
        "tau": int(state.tau),
        "post_offenders": state.psi.offenders.to_json(),
        "eta": state.eta.to_json(),
        "lambda": state.lambda_.to_json(),
        "kappa": state.kappa.to_json(),
        "gamma_k": state.gamma.k.to_json(),
        "gamma_a": state.gamma.a.to_json(),
        "gamma_s": state.gamma.s.to_json(),
        "gamma_z": state.gamma.z.to_json(),
        "iota": state.iota.to_json(),
        "kappa": state.kappa.to_json(),
        "kappa": state.kappa.to_json(),
    }


transition = Safrole.transition
