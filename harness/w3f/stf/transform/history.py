from typing import Dict, Tuple

from jam.state.ghost import GhostState
from jam.types.block import Block
from jam.types.extrinsics.guarantees import GuaranteesExtrinsic, ReportGuarantee, ValidatorSignatures
from jam.types.protocol.core import SegmentRoot, WorkPackageHash
from jam.types.state.sigma import Sigma
from jam.types.state.beta import Beta
from jam.types.header import Header
from jam.recent_history.recent_history import OpaqueHash, RecentHistory
from jam.types.work.report import SegmentRootLookup, WorkReport
from jam.utils.dummy.dummy_extrinsics import create_dummy_work_report



def transform_block(vector_input: dict) -> (Block, Dict):
    block = Block.genesis()
    block.header.parent_state_root = OpaqueHash(vector_input["parent_state_root"])
    guarantees =[]
    for segment in vector_input["work_packages"]:
        # 1) create your dummy report
        wr = create_dummy_work_report()
        # 2) plug in the segment lookup
        sr=SegmentRootLookup({})
        sr[WorkPackageHash(segment["hash"])]=SegmentRoot(segment["exports_root"])
        wr.segment_root_lookup = sr

        # 3) wrap it in a ReportGuarantee
        guarantee = ReportGuarantee(
            report=wr,
            slot=block.header.slot,
            signatures=ValidatorSignatures([]),
        )

        guarantees.append(guarantee)
    block.extrinsic.guarantees=GuaranteesExtrinsic(guarantees)

    return block, {"accumulate_root": OpaqueHash(vector_input["accumulate_root"]),"header_hash":OpaqueHash(vector_input["header_hash"])}


def transform_state(vector_state: dict) -> Sigma:
    state = GhostState.genesis()
    for beta in vector_state["beta"]:
        beta["mmr"]=beta["mmr"]["peaks"]
        for lookup_item in beta["reported"]:
            lookup_item["work_package_hash"]=lookup_item["hash"]
            del lookup_item["hash"]
            lookup_item["segment_tree_root"]=lookup_item["exports_root"]
            del lookup_item["exports_root"]

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
