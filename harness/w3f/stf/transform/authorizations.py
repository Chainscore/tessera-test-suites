from typing import Dict, Tuple
from jam.authorization.authorization import Authorization
from jam.state.ghost import GhostState
from jam.types.extrinsics.guarantees import (
    GuaranteesExtrinsic,
    ReportGuarantee,
    ValidatorSignatures,
)
from jam.types.state.phi import Phi
from jam.types.state.alpha import Alpha
from jam.types.protocol.core import CoreIndex


from jam.types.block import Block
from jam.types.state.sigma import Sigma
from jam.types.state.tau import Tau
from jam.types.work.report import WorkReport


def transform_block(vector_input: dict) -> (Block, Dict):
    block = Block.genesis()
    block.header.slot = Tau(vector_input["slot"])
    block.extrinsic.guarantees = GuaranteesExtrinsic(
        [
            ReportGuarantee(
                report=WorkReport.empty(
                    core_index=CoreIndex(report["core"]),
                    authorizer_hash=report["auth_hash"],
                ),
                slot=block.header.slot,
                signatures=ValidatorSignatures([]),
            )
            for report in vector_input["auths"]
        ]
    )
    return block, {}


def transform_state(vector_state: dict) -> Sigma:
    state = GhostState.genesis()
    state.rho = Alpha.from_json(vector_state["auth_pools"])
    state.kappa = Phi.from_json(vector_state["auth_queues"])
    return state


def subset_to_compare(state: Sigma) -> Tuple:
    """
    Pull out only the fields we actually want to assert on
    (validator‐stats and slot in this example).
    """
    return (
        state.alpha,
        state.phi,
    )


transition = Authorization.transition
