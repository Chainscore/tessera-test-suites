from typing import Tuple, Dict
from harness.w3f.stf.types import Stats
from jam.state.ghost import GhostState
from jam.types.protocol.core import ValidatorIndex
from jam.types.base.integers.fixed import U32
from jam.types.header import Header
from jam.types.state.iota import Iota
from jam.types.state.kappa import Kappa
from jam.types.work.report import WorkReports
from jam.utils.constants import CORE_COUNT
from jam.types.block import Block

# from jam.types.extrinsics import PreimagesExtrinsic, TicketsExtrinsic
from jam.types.state.pi import (
    AllCoreStats,
    AllServiceStats,
    AllValidatorStats,
    CoreStat,
    Pi,
)
from jam.types.state.tau import Tau
from jam.statistics.statistics import Statistics

from jam.types.state.sigma import Sigma

from jam.types.extrinsics.preimages import PreimagesExtrinsic

from jam.types.extrinsics.assurances import AssurancesExtrinsic

from jam.types.extrinsics.tickets import (
    TicketEnvelope,
    TicketBody,
    TicketsAccumulator,
    KeysAccumulator,
    TicketsExtrinsic,
)

from jam.types.extrinsics.disputes import (
    Verdict,
    Culprit,
    Judgement,
    DisputesExtrinsic,
    Fault,
    DisputesRecords,
)

from jam.types.extrinsics.guarantees import (
    ValidatorSignature,
    ReportGuarantee,
    GuaranteesExtrinsic,
)


def transform_block(vector_input: dict) -> (Block, Dict):
    block = Block.genesis()
    block.header.slot = Tau(vector_input["slot"])
    block.header.author_index = ValidatorIndex(vector_input["author_index"])
    block.extrinsic.tickets = TicketsExtrinsic.from_json(
        vector_input["extrinsic"]["tickets"]
    )
    block.extrinsic.preimages = PreimagesExtrinsic.from_json(
        vector_input["extrinsic"]["preimages"]
    )
    block.extrinsic.guarantees = GuaranteesExtrinsic.from_json(
        vector_input["extrinsic"]["guarantees"]
    )
    block.extrinsic.assurances = AssurancesExtrinsic.from_json(
        vector_input["extrinsic"]["assurances"]
    )
    block.extrinsic.disputes = DisputesExtrinsic.from_json(
        vector_input["extrinsic"]["disputes"]
    )

    return block, {
        "available_wrs": WorkReports([]),
        "accumulation_stats": Stats(),
        "deferred_transfer_stats": Stats(),
    }


def transform_state(vector_state: dict) -> Sigma:
    state = GhostState.genesis()
    state.pi = Pi(
        vals_current=AllValidatorStats.from_json(vector_state["vals_curr_stats"]),
        vals_last=AllValidatorStats.from_json(vector_state["vals_last_stats"]),
        cores=AllCoreStats(
            [
                CoreStat(
                    gas_used=U32(0),
                    imports=U32(0),
                    extrinsic_count=U32(0),
                    extrinsic_size=U32(0),
                    exports=U32(0),
                    bundle_size=U32(0),
                    da_load=U32(0),
                    popularity=U32(0),
                )
                for _ in range(CORE_COUNT)
            ]
        ),
        services=AllServiceStats({}),
    )
    # print(state.pi)
    state.kappa = Kappa.from_json(vector_state["curr_validators"])
    state.tau = Tau(vector_state["slot"])
    return state


def compare_state(state: Sigma) -> dict:
    """
    Pull out only the fields we actually want to assert on
    (validator‐stats and slot in this example).
    """
    return {
        "slot": int(state.tau),
        "psi": state.psi.to_json(),
        "rho": state.rho.to_json(),
        "tau": state.tau.to_json(),
        "kappa": state.kappa.to_json(),
        "lambda": state.lambda_.to_json(),
    }


transition = Statistics.transition
