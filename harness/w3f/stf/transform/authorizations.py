from pathlib import Path
from typing import Dict, Tuple
from jam.state.state import State
from jam.state.transitions import Authorization

from jam.state.ghost import GhostState
from jam.block.extrinsics.guarantees import (
    GuaranteesExtrinsic,
    ReportGuarantee,
    ValidatorSignatures,
)
from jam.state.utils import construct_state_key
from jam.models.state.phi import Phi
from jam.models.state.alpha import Alpha
from jam.models.protocol.core import CoreIndex
from jam.models.protocol.crypto import OpaqueHash

from jam.block.block import Block
from jam.models.state.sigma import Sigma
from jam.models.state.tau import Tau
from jam.models.work import WorkReport


def transform_block(vector_input: dict) -> (Block, Dict):
    block = Block.genesis()
    block.header.slot = Tau(vector_input["slot"])
    block.extrinsic.guarantees = GuaranteesExtrinsic(
        [
            ReportGuarantee(
                report=WorkReport.empty(
                    core_index=CoreIndex(report["core"]),
                    authorizer_hash=OpaqueHash.from_json(report["auth_hash"]),
                ),
                slot=Tau(block.header.slot),
                signatures=ValidatorSignatures([]),
            )
            for report in vector_input["auths"]
        ]
    )
    return block, {}


def transform_state(vector_state: dict) -> Sigma:
    state = {}
    state[construct_state_key(1)] = Alpha.from_json(vector_state["auth_pools"]).encode()
    state[construct_state_key(2)] = Phi.from_json(vector_state["auth_queues"]).encode()
    return {key.hex(): value.hex() for key, value in state.items()}


def subset_to_compare(state: Sigma) -> Tuple[Alpha,Phi]:
    """
    Pull out only the fields we actually want to assert on
    (validator‐stats and slot in this example).
    """
    if isinstance(state, State):
        data = {k.hex(): v.hex() for k, v in state.store._DB.get_all().items()}
    else:
        data = state
    return data


transition = Authorization.transition
