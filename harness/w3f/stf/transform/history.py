from typing import Dict, Tuple

from jam.state.ghost import GhostState
from jam.types import OpaqueHash
from jam.block.block import Block
from jam.block.extrinsics.guarantees import GuaranteesExtrinsic, ReportGuarantee, ValidatorSignatures
from jam.types.state.sigma import Sigma
from jam.types.state.beta import Beta
from jam.state.transitions import RecentHistory
from jam.utils.dummy.dummy_extrinsics import create_dummy_work_report
from sympy.core.assumptions_generated import beta_rules


def transform_block(vector_input: dict) -> (Block, Dict):
    block = Block.genesis()
    block.header.parent_state_root = OpaqueHash.from_json(vector_input["parent_state_root"])
    guarantees =[]
    for wp in vector_input["work_packages"]:
        wr = create_dummy_work_report()
        wr.package_spec.hash = OpaqueHash.from_json(wp["hash"])
        wr.package_spec.exports_root = OpaqueHash.from_json(wp["exports_root"])
        guarantee = ReportGuarantee(
            report=wr,
            slot=block.header.slot,
            signatures=ValidatorSignatures([]),
        )

        guarantees.append(guarantee)
    block.extrinsic.guarantees=GuaranteesExtrinsic(guarantees)

    return block, {"acc_root": OpaqueHash.from_json(vector_input["accumulate_root"]), "header_hash": OpaqueHash.from_json(vector_input["header_hash"])}


def transform_state(vector_state: dict) -> Sigma:
    state = GhostState.genesis()
    if not isinstance(vector_state["beta"]["mmr"], list):
        vector_state["beta"]["mmr"]=vector_state["beta"]["mmr"]["peaks"]

    state.beta = Beta.from_json(vector_state["beta"])
    return state


def subset_to_compare(state: Sigma) -> Tuple[Beta]:
    """
    Pull out only the fields we actually want to assert on
    (validator‐stats and slot in this example).
    """
    return (
        state.beta,
    )


transition = RecentHistory.transition
