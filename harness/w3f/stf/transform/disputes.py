from typing import List, Tuple, Dict


from jam.consensus.safrole.errors import SafroleError, SafroleErrorCode
from jam.disputes.disputes import Disputes
from jam.state.ghost import GhostState

# from jam.state.state import GhostState, State
# from jam.types import Boolean
from jam.types.state.rho import Rho
from jam.types.block import Block

# from tests.unit.disputes.types import (
#     Input,
#     PreState,
#     Testcase,
#     get_testcases_starting_with,
# )j

from jam.types.state.gamma import GammaK
from jam.types.state.psi import Psi
from jam.types.state.sigma import Sigma
from jam.types.state.tau import Tau
from jam.types.state.lambda_ import Lambda_

from jam.types.extrinsics.disputes import (
    Culprit,
    Culprits,
    DisputesExtrinsic,
    Fault,
    Faults,
    JudgementVotes,
    Judgement,
    Verdict,
    Verdicts,
)


def transform_block(vector_input: dict) -> (Block, Dict):
    block = Block.genesis()
    block.extrinsic.disputes = DisputesExtrinsic.from_json(vector_input["disputes"])
    return block, {}


def transform_state(vector_state: dict) -> Sigma:
    state = GhostState.genesis()
    state.psi = Psi.from_json(vector_state["psi"])
    # state.rho=Rho.from_json(vector_state["rho"])
    state.tau = Tau.from_json(vector_state["tau"])
    state.rho = Rho.from_json(vector_state["rho"])
    state.lambda_ = Lambda_.from_json(vector_state["lambda"])

    return state


def subset_to_compare(state: Sigma) -> Tuple:
    """
    Pull out only the fields we actually want to assert on
    (validator‐stats and slot in this example).
    """
    return (
        state.tau,
        state.pi.vals_current,
        state.pi.vals_last,
        state.kappa,
    )


transition = Disputes.transition
