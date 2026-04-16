import json
from pathlib import Path
from typing import Dict, Tuple
from jam.state.state import State
from jam.state.transitions import Reporting
from jam.state.ghost import GhostState
from jam.block.block import Block
from jam.state.utils import construct_state_key
from jam.types.protocol.crypto import OpaqueHash, Hash
from jam.types.protocol.core import TimeSlot
from jam.types.state.alpha import Alpha
from jam.types.state.beta import Beta
from jam.types.state.delta import Delta
from jam.types.state.eta import Eta
from jam.types.state.gamma import Gamma, GammaP
from jam.types.state.kappa import Kappa
from jam.types.state.lambda_ import Lambda_
from jam.types.state.omega import AllReadyWRs, Omega
from jam.types.state.pi import AllCoreStats, AllServiceStats, AllValidatorStats, Pi
from jam.types.state.psi import Psi, PsiB, PsiG, PsiO, PsiW
from jam.types.state.sigma import Sigma
from jam.types.state.rho import Rho
from jam.types.state.tau import Tau
from jam.block.extrinsics import GuaranteesExtrinsic
from jam.types.state.xi import Xi
from jam.types.work.report import WorkDependencies
from jam.utils.constants import EPOCH_LENGTH


def transform_block(vector_input: dict) -> (Block, Dict):
    block = Block.genesis()
    block.header.slot = Tau(vector_input["slot"])
    block.extrinsic.guarantees = GuaranteesExtrinsic.from_json(
        vector_input["guarantees"]
    )
    root_arr = vector_input.get("known_packages")
    if root_arr is None:
        roots = None
    else:
        roots = [OpaqueHash.from_json(h) for h in root_arr]
    return block, {"known_packages": roots}


def transform_state(vector_state: dict) -> Sigma:
    dev_spec = json.load(open(Path(__file__).parents[4] / "dev-spec.json"))
    state = {bytes.fromhex(k):bytes.fromhex(v) for k, v in dev_spec["genesis_state"].items()}

    if not isinstance(vector_state["recent_blocks"]["mmr"], list):
        vector_state["recent_blocks"]["mmr"] = vector_state["recent_blocks"]["mmr"]["peaks"]
    vector_state["recent_blocks"]["packages"] = []

    state[construct_state_key(10)] = Rho.from_json(vector_state["avail_assignments"]).encode()
    state[construct_state_key(6)] = Eta.from_json(vector_state["entropy"]).encode()
    state[construct_state_key(1)] = Alpha.from_json(vector_state["auth_pools"]).encode()
    state[construct_state_key(3)] = Beta.from_json(vector_state["recent_blocks"]).encode()
    core_stats = AllCoreStats.from_json(vector_state["cores_statistics"])
    services_stats = AllServiceStats.from_json(vector_state["services_statistics"])
    state[construct_state_key(13)] = Pi(
        vals_current=AllValidatorStats.empty(),
        vals_last=AllValidatorStats.empty(),
        cores=core_stats,
        services=services_stats
    ).encode()
    state[construct_state_key(8)] = Kappa.from_json(vector_state["curr_validators"]).encode()
    state[construct_state_key(9)] = Lambda_.from_json(vector_state["prev_validators"]).encode()
    state[construct_state_key(5)] = Psi(
        good=PsiG([]),
        bad=PsiB([]),
        wonky=PsiW([]),
        offenders=PsiO.from_json(vector_state["offenders"])
    ).encode()
    state.update(
        Delta.from_json(vector_state["accounts"]).transform()
    )
    
    # --- Set Gamma P = Kappa --- #
    gamma = Gamma.decode(state[construct_state_key(4)])
    gamma.p = GammaP.from_json(vector_state["curr_validators"])
    state[construct_state_key(4)] = gamma.encode()
    
    return {key.hex(): value.hex() for key, value in state.items()}

def subset_to_compare(state: Sigma) -> Tuple:
    """
    Pull out only the fields we actually want to assert on
    """
    if isinstance(state, State):
        data = {k.hex(): v.hex() for k, v in state.store._DB.get_all().items()}
    else:
        data = state
    data[construct_state_key(11).hex()] = Tau(0).encode().hex()
    return data


def transition(pre_state, state, block, **args):
    state.tau = block.header.slot
    state = Reporting.transition(pre_state, state, block, **args)

    return state