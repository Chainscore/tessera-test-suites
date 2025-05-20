from typing import Dict
from typing import Optional


from harness.w3f.stf.types import InputAccounts, Service
from jam.report.state import Reporting
from jam.state.ghost import GhostState
from jam.types.block import Block
from jam.types.protocol.crypto import OpaqueHash, Hash
from jam.types.protocol.core import TimeSlot
from jam.types.state.alpha import Alpha
from jam.types.state.beta import Beta
from jam.types.state.eta import Eta
from jam.types.state.kappa import Kappa
from jam.types.state.lambda_ import Lambda_
from jam.types.state.pi import AllCoreStats, AllServiceStats, AllValidatorStats, Pi
from jam.types.state.psi import PsiO
from jam.types.state.sigma import Sigma
from jam.types.state.rho import Rho
from jam.types.state.tau import Tau
from jam.types.extrinsics.guarantees import (
    GuaranteesExtrinsic,
    ReportGuarantee,
    ValidatorSignatures,
)
from jam.types.work.report import WorkReport


def transform_block(vector_input: dict) -> (Block, Dict):
    block = Block.genesis()
    block.header.slot = Tau(vector_input["slot"])
    block.extrinsic.guarantees = GuaranteesExtrinsic.from_json(
        vector_input["guarantees"]
    )
    # root_arr = vector_input.get("known_packages")
    # if root_arr is None:
    #     roots = None
    # else:
    #     roots = [OpaqueHash(h) for h in root_arr]
    return block, {}


def transform_state(vector_state: dict) -> Sigma:
    state = GhostState.genesis()
    for block in vector_state["recent_blocks"]:
        block["mmr"] = block["mmr"]["peaks"]
        block["packages"] = []
    for account in vector_state["accounts"]:
        account["data"]["storage"] = []
        account["data"]["preimages"] = []

    state.rho = Rho.from_json(vector_state["avail_assignments"])
    state.eta = Eta.from_json(vector_state["entropy"])
    state.alpha = Alpha.from_json(vector_state["auth_pools"])
    state.beta = Beta.from_json(vector_state["recent_blocks"])
    state.pi.cores = AllCoreStats.from_json(vector_state["cores_statistics"])
    state.pi.services = AllServiceStats.from_json(vector_state["services_statistics"])
    state.kappa = Kappa.from_json(vector_state["curr_validators"])
    state.lambda_ = Lambda_.from_json(vector_state["prev_validators"])
    state.psi.offenders = PsiO.from_json(vector_state["offenders"])
    state.delta = InputAccounts.from_json(vector_state["accounts"]).to_delta()

    return state


def compare_state(state: Sigma) -> dict:
    """
    Pull out only the fields we actually want to assert on
    (validator‐stats and slot in this example).
    """
    accounts = state.delta.to_json()
    for account in accounts:
        del account["data"]["storage"]
        del account["data"]["preimages"]
    return {
        "avail_assignments": state.rho.to_json(),
        "entropy": state.eta.to_json(),
        "auth_pools": state.alpha.to_json(),
        "recent_blocks": state.beta.to_json(),
        "cores_statistics": state.pi.cores.to_json(),
        "services_statistics": state.pi.services.to_json(),
        "curr_validators": state.pi.vals_current.to_json(),
        "prev_validators": state.pi.vals_last.to_json(),
        "offenders": state.psi.offenders.to_json(),
        "accounts": accounts,
    }


transition = Reporting.transition
