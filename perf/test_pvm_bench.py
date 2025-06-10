import json
from pathlib import Path

from jam.accumulation.types import StateContext, OperandTuples
from jam.execution.host_calls.invocations.accumulate import PsiA
from jam.state.ghost import GhostState
from jam.state.state import setup_state
from rockstore import RockStore
from jam.types.protocol.core import ServiceId, Gas

GEN_PATH = Path(__file__).parents[0] / "dummy-state-genesis.json"

def test_compare_pvm(db_path):
	db = RockStore(db_path)
	state = GhostState.genesis(GEN_PATH)
	state = setup_state(state, db)
	context = StateContext(service_accounts=state.delta, validator_keys=state.iota, authorizer_keys=state.phi, privileges=state.chi)

	PsiA(context, state.tau, ServiceId(0), Gas(10000000000), OperandTuples([])).execute()