from pathlib import Path

from jam.state.ghost import GhostState
from jam.state.state import setup_state, state as global_state
from jam.types.protocol.core import Balance, BlobLength, Gas, ServiceId, TimeSlot
from jam.types.protocol.crypto import Hash
from jam.types.state.delta import AccountMetadata, Ai, Ao, LookupTable, Timestamps
from jam.types.work.item import ExtrinsicSpecs, ImportSpecs, WorkItem
from jam.settings import setup_setting
from jam.utils.dummy.dummy_package import create_dummy_package
from jam.execution.host_calls.invocations.refine import PsiR
from jam.execution.host_calls.invocations.accumulate import PsiA, StateContext  # your PsiA
from tsrkit_types.bytes import Bytes
from tsrkit_types.enum import Uint

# Helpers to read storage for ASSERTs:
from jam.state.utils import construct_state_key
from jam.state.storage import StateStorage
from tsrkit_types.integers import U32

def test_accumulate(tmp_path):
    service = "hello"
    payload = b"Prasad"
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, str(tmp_path))
    state = setup_state(settings.state_db, GhostState.genesis())

    # Make a dummy package + a dummy work item to the hello service
    package = create_dummy_package()
    wi_service_code = open(Path(__file__).parents[4] / "tessera-test-suites" / "playground" / "builds" / f"{service}-service.jam", "rb").read()
    wi_code_hash = Hash.blake2b(wi_service_code)
    wi_service = ServiceId(1)

    # Fund and register the service + preimage
    state.delta[wi_service].service = AccountMetadata(
        code_hash=wi_code_hash,
        balance=Balance(10**12),  # <- big balance so storage writes succeed
        gas_limit=Gas(10_000),    # generous for demo
        min_gas=Gas(1_000),
        num_i=Ai(0),
        num_o=Ao(0),
    )
    state.delta[wi_service].preimages[wi_code_hash] = Bytes(wi_service_code)
    state.delta[wi_service].lookup[LookupTable(hash=wi_code_hash, length=BlobLength(len(wi_service_code)))] = Timestamps([state.tau])

    # Work item
    wi = WorkItem(
        service=wi_service,
        code_hash=wi_code_hash,
        payload=Bytes(payload),
        refine_gas_limit=Gas(5_000),
        accumulate_gas_limit=Gas(5_000),
        import_segments=ImportSpecs([]),
        extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    package.items.append(wi)

    # ---- Refine
    r, e, u = PsiR(0, p=package, auth_trace=b"", i_segments=[[]], e_offset=0).execute()
    print(f"Refine status={r} gas_used={u} exports={e}")

    # ---- Accumulate
    #
    # PsiA executes the service's accumulate code for the service id.
    # We pass the current state's partial context, current timeslot, and gas.
    # Operand tuples are service-defined; for our hello-service accumulate,
    # we don't need any (it just writes each item's result to storage).
    partial_state = StateContext(
        service_accounts=state.delta, validator_keys=state.iota,
        authorizer_keys=state.phi, privileges=state.chi,
    )
    timeslot = TimeSlot(state.tau)
    gas = Gas(5_000)

    # No explicit operands needed for this service:
    from jam.types.state.accumulation.types import OperandTuples
    operands = OperandTuples([])
    new_state_ctx, deferred_transfers, commit_opt, gas_left, preimages = PsiA(
        partial_state, timeslot, wi_service, gas, operands
    ).execute()
    key = Hash.blake2b(package.encode())

    KEY_ITEMS_LEN = Bytes(b"acc_items_len___________________")  # 32 bytes
    n_items_bytes = new_state_ctx.service_accounts[wi_service].storage[KEY_ITEMS_LEN]
    print("accumulation done",n_items_bytes)
    # print("Accumulate done:", new_state_ctx.service_accounts[wi_service].storage[Hash.blake2b(key)])
