import json
from pathlib import Path
from typing import Tuple, Dict
from jam.state.state import State
from jam.state.utils import construct_state_key
from jam.models.protocol.core import ValidatorIndex
from jam.models.state.kappa import Kappa
from jam.models.state.lambda_ import Lambda_
from jam.models.work import WorkReports
from jam.block.block import Block
from jam.models.state.pi import (
    AllCoreStats,
    AllServiceStats,
    AllValidatorStats,
    Pi,
)
from jam.models.state.tau import Tau
from jam.state.transitions import Statistics
from jam.state.transitions.statistics import statistics as statistics_module
from jam.models.state.sigma import Sigma
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
    dev_spec = json.load(open(Path(__file__).parents[4] / "dev-spec.json"))
    state = {
        bytes.fromhex(k): bytes.fromhex(v)
        for k, v in dev_spec["genesis_state"].items()
    }
    state[construct_state_key(13)] = Pi(
        vals_current=AllValidatorStats.from_json(vector_state["vals_curr_stats"]),
        vals_last=AllValidatorStats.from_json(vector_state["vals_last_stats"]),
        cores=AllCoreStats.empty(),
        services=AllServiceStats({}),
    ).encode()
    curr_validators = Kappa.from_json(vector_state["curr_validators"])
    state[construct_state_key(8)] = curr_validators.encode()
    state[construct_state_key(9)] = Lambda_.from_json(vector_state["curr_validators"]).encode()
    state[construct_state_key(11)] = Tau.from_json(vector_state["slot"]).encode()
    return {key.hex(): value.hex() for key, value in state.items()}


def subset_to_compare(state: Sigma) -> Tuple:
    """
    Pull out only the fields we actually want to assert on
    (validator‐stats and slot in this example).
    """
    if isinstance(state, State):
        data = {k.hex(): v.hex() for k, v in state.store._DB.get_all().items()}
    else:
        data = state
    return data


def transition(pre_state, state, block, **args):
    original_tau = state.tau
    original_assign_fn = statistics_module.assign_fn

    def _vector_assign_fn(_state):
        per_core = {}
        for guarantee in block.extrinsic.guarantees:
            core_index = guarantee.report.core_index
            if core_index not in per_core:
                per_core[core_index] = set()
            for signature in guarantee.signatures:
                per_core[core_index].add(signature.validator_index)
        return per_core, {}, per_core, {}

    state.tau = block.header.slot
    statistics_module.assign_fn = _vector_assign_fn
    try:
        return Statistics.transition(pre_state, state, block, **args)
    finally:
        statistics_module.assign_fn = original_assign_fn
        state.tau = original_tau
