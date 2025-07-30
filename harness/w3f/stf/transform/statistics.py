from typing import Tuple, Dict
from jam.state.ghost import GhostState
from jam.types.protocol.core import ValidatorIndex
from jam.types.state.kappa import Kappa
from jam.types.work import WorkReports
from jam.block.block import Block
from jam.types.state.pi import (
    AllCoreStats,
    AllServiceStats,
    AllValidatorStats,
    Pi,
)
from jam.types.state.tau import Tau
from jam.state.transitions import Statistics
from jam.types.state.sigma import Sigma
from jam.block.extrinsics.preimages import PreimagesExtrinsic
from jam.block.extrinsics.assurances import AssurancesExtrinsic
from jam.block.extrinsics.tickets import (
    TicketsExtrinsic,
)
from jam.block.extrinsics.disputes import (
    DisputesExtrinsic,
)
from jam.block.extrinsics.guarantees import (
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
        # "accumulation_stats": Stats(), TODO: When we add deffered and accumulations (on testCase/func) to the funcions we add this
        # "deferred_transfer_stats": Stats(),
    }


def transform_state(vector_state: dict) -> Sigma:
    state = GhostState.genesis()
    state.pi = Pi(
        vals_current=AllValidatorStats.from_json(vector_state["vals_curr_stats"]),
        vals_last=AllValidatorStats.from_json(vector_state["vals_last_stats"]),
        cores=AllCoreStats.empty(),
        services=AllServiceStats({}),
    )
    state.kappa = Kappa.from_json(vector_state["curr_validators"])
    return state


def subset_to_compare(state: Sigma) -> Tuple:
    """
    Pull out only the fields we actually want to assert on
    (validator‐stats and slot in this example).
    """
    return (
        state.psi,
        state.rho,
        state.tau,
        state.kappa,
        state.lambda_,
    )


transition = Statistics.transition
