from pathlib import Path
from typing import Dict, Tuple

from jam.state.ghost import GhostState
from jam.state.state import State
from jam.state.utils import construct_state_key
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
    state = {}
    if not isinstance(vector_state["beta"]["mmr"], list):
        vector_state["beta"]["mmr"] = vector_state["beta"]["mmr"]["peaks"]

    state[construct_state_key(3)] = Beta.from_json(vector_state["beta"]).encode()
    return {key.hex(): value.hex() for key, value in state.items()}


def subset_to_compare(state: Sigma) -> Tuple[Beta]:
    """
    Pull out only the fields we actually want to assert on
    """
    if isinstance(state, State):
        data = {k.hex(): v.hex() for k, v in state.store._DB.get_all().items()}
    else:
        data = state
    return data

transition = RecentHistory.transition
