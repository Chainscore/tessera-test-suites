from typing import Tuple

from jam.settings import Settings
from jam.types import AuthorizationQueue, OpaqueHash, Phi, Iota, ValidatorData, ValidatorMetadata, BandersnatchPublic, \
    Ed25519Public, BlsPublic
from jam.utils.constants import MAX_AUTH_QUEUE_ITEMS, CORE_COUNT, VALIDATOR_COUNT
from jam.utils.dummy.utils import create_dummy_bytes32, create_dummy_bytes
from ..types import InputAccounts
from jam.state.state import State
from jam.state.transitions import Accumulation
from jam.block.block import Block
from jam.state.utils import construct_state_key
from jam.types.protocol.core import TimeSlot
from jam.types.state.chi import Chi
from jam.types.state.eta import Eta
from jam.types.state.omega import Omega
from jam.types.state.pi import AllCoreStats, AllServiceStats, AllValidatorStats, Pi
from jam.types.state.sigma import Sigma
from jam.types.state.tau import Tau
from jam.types.state.xi import Xi
from jam.types.work import WorkReports


def transform_block(vector_input: dict) -> (Block, dict):
    block = Block.genesis()
    block.header.slot = TimeSlot(vector_input["slot"])
    return block, {"newly_avail_wrs": WorkReports.from_json(vector_input["reports"])}


def transform_state(vector_state: dict) -> dict[bytes, bytes]:
    state = {}
    state[construct_state_key(11)] = Tau.from_json(vector_state["slot"]).encode()

    # Phi - Authorization queue
    queue = AuthorizationQueue(
        [OpaqueHash(create_dummy_bytes32()) for _ in range(MAX_AUTH_QUEUE_ITEMS)]
    )
    state[construct_state_key(2)] = Phi([queue for _ in range(CORE_COUNT)]).encode()

    state[construct_state_key(6)] = Eta.from_json(
        [
            vector_state["entropy"],
            "0x" + bytes(32).hex(),
            "0x" + bytes(32).hex(),
            "0x" + bytes(32).hex(),
        ]
    ).encode()

    # Create dummy validator data
    key_set = [Settings(data_path=None, seed=i) for i in range(VALIDATOR_COUNT)]
    dummy_validator_data = [
        ValidatorData(
            bandersnatch=BandersnatchPublic(key.bandersnatch_public),
            ed25519=Ed25519Public(key.ed25519_public),
            bls=BlsPublic(create_dummy_bytes(144)),
            metadata=ValidatorMetadata.from_json(bytes(128).hex()),
        )
        for key in key_set
    ]

    state[construct_state_key(7)] = Iota(dummy_validator_data).encode()

    state[construct_state_key(12)] = Chi.from_json(vector_state["privileges"]).encode()
    services_stats = AllServiceStats.from_json(vector_state["statistics"])
    state[construct_state_key(13)] = Pi(
        vals_current=AllValidatorStats.empty(),
        vals_last=AllValidatorStats.empty(),
        cores=AllCoreStats.empty(),
        services=services_stats
    ).encode()
    state.update(
        InputAccounts.from_json(vector_state["accounts"]).to_delta().transform()
    )

    state[construct_state_key(14)] = Omega.from_json(vector_state["ready_queue"]).encode()
    state[construct_state_key(15)] = Xi.from_json(vector_state["accumulated"]).encode()
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
    data[construct_state_key(7).hex()] = bytes(32).hex()
    data[construct_state_key(2).hex()] = bytes(32).hex()
    data[construct_state_key(16).hex()] = bytes(32).hex()
    data[construct_state_key(13).hex()] = bytes(32).hex()
    return data


def transition(pre_state, state, block, **args):
    state.tau = block.header.slot
    state, c_map = Accumulation.transition(pre_state, state, block, **args)

    return state
