from typing import Tuple, Dict

from harness.w3f.stf.types import InputAccounts
from jam.accumulation.accumulation import Accumulation
from jam.config.data_stores import main_db
from jam.consensus.safrole.safrole import Safrole
from jam.state.ghost import GhostState
from jam.state.state import setup_state
from jam.types.block import Block
from jam.types.extrinsics import GuaranteesExtrinsic, ReportGuarantee
from jam.types.extrinsics.guarantees import ValidatorSignatures
from jam.types.state.chi import Chi
from jam.types.state.eta import Eta
from jam.types.state.nu import Nu
from jam.types.state.pi import AllServiceStats
from jam.types.state.sigma import Sigma
from jam.types.state.tau import Tau
from jam.types.state.xi import Xi
from jam.types.work.report import WorkReport


def transform_block(vector_input: dict) -> (Block, Dict):
    block = Block.genesis()
    block.header.slot = Tau(vector_input["slot"])
    block.extrinsic.guarantees = GuaranteesExtrinsic(
        [
            ReportGuarantee(
                report=WorkReport.from_json(report),
                slot=block.header.slot,
                signatures=ValidatorSignatures([]),
            )
            for report in vector_input["reports"]
        ]
    )
    return block, {}

def transform_state(vector_state: dict) -> Sigma:
    state = GhostState.genesis()
    state.tau = Tau.from_json(vector_state["slot"])
    state.eta = Eta.from_json(
        [
            vector_state["entropy"],
            "0x" + bytes(32).hex(),
            "0x" + bytes(32).hex(),
            "0x" + bytes(32).hex(),
        ]
    )
    state.chi = Chi.from_json(vector_state["privileges"])
    state.pi.services = AllServiceStats.from_json(vector_state["statistics"])
    state.delta = InputAccounts.from_json(vector_state["accounts"]).to_delta()
    state.nu = Nu.from_json(vector_state["ready_queue"])
    state.xi = Xi.from_json(vector_state["accumulated"])
    setup_state(state, main_db)
    return state


transition = Accumulation.transition
