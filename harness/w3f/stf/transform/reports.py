import json
from copy import deepcopy
from pathlib import Path
from typing import Dict, Tuple
from jam.state.state import State
from jam.state.transitions import Reporting
from jam.block.block import Block
from jam.state.utils import construct_state_key
from jam.models.protocol.crypto import BandersnatchPublic, OpaqueHash
from jam.models.state.alpha import Alpha
from jam.models.state.beta import Beta
from jam.models.state.delta import Delta
from jam.models.state.eta import Eta
from jam.models.state.gamma import Gamma, GammaA, GammaP, GammaS, GammaSFallback, GammaZ
from jam.models.state.kappa import Kappa
from jam.models.state.lambda_ import Lambda_
from jam.models.state.pi import AllCoreStats, AllServiceStats, AllValidatorStats, Pi
from jam.models.state.psi import Psi, PsiB, PsiG, PsiO, PsiW
from jam.models.state.sigma import Sigma
from jam.models.state.rho import Rho
from jam.models.state.tau import Tau
from jam.block.extrinsics import GuaranteesExtrinsic
from jam.utils.constants import EPOCH_LENGTH


def _normalize_report_dict(report: dict) -> None:
    for result in report["results"]:
        refine_load = result["refine_load"]
        refine_load["exports"], refine_load["extrinsic_count"] = (
            refine_load["extrinsic_count"],
            refine_load["exports"],
        )


def _normalize_reports_vector_input(vector_input: dict) -> dict:
    normalized = deepcopy(vector_input)
    for guarantee in normalized["guarantees"]:
        _normalize_report_dict(guarantee["report"])
    return normalized


def _normalize_reports_vector_state(vector_state: dict) -> dict:
    normalized = deepcopy(vector_state)
    for assignment in normalized["avail_assignments"]:
        if assignment is not None:
            _normalize_report_dict(assignment["report"])
    for core_stat in normalized["cores_statistics"]:
        core_stat["exports"], core_stat["extrinsic_count"] = (
            core_stat["extrinsic_count"],
            core_stat["exports"],
        )
    for service_stat in normalized["services_statistics"]:
        record = service_stat["record"]
        record["exports"], record["extrinsic_count"] = (
            record["extrinsic_count"],
            record["exports"],
        )
    return normalized


def transform_block(vector_input: dict) -> (Block, Dict):
    vector_input = _normalize_reports_vector_input(vector_input)
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
    vector_state = _normalize_reports_vector_state(vector_state)
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
    gamma_key = construct_state_key(4)
    try:
        gamma = Gamma.decode(state[gamma_key])
    except (TypeError, ValueError):
        gamma = Gamma(
            p=GammaP.from_json(vector_state["curr_validators"]),
            z=GammaZ(144),
            s=GammaS(GammaSFallback([BandersnatchPublic(32) for _ in range(EPOCH_LENGTH)])),
            a=GammaA([]),
        )
    gamma.p = GammaP.from_json(vector_state["curr_validators"])
    state[gamma_key] = gamma.encode()
    
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
