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
from jam.execution.host_calls.invocations.accumulate import PsiA, StateContext
from tsrkit_types.bytes import Bytes
from tsrkit_types.enum import Uint

# Helper: make the same 32-byte fixed keys the service used
def key32(label: bytes) -> Bytes[32]:
    raw = bytearray(32)
    raw[:min(32, len(label))] = label[:32]
    return Bytes[32](bytes(raw))

def test_lookup_via_accumulate(tmp_path):
    service = "lookup2"   # name your compiled .jam accordingly
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, str(tmp_path))
    state = setup_state(settings.state_db, GhostState.genesis())

    # ---- Install & fund the service and provide its code preimage
    package = create_dummy_package()
    wi_service_code = open(
        Path(__file__).parents[4]
        / "tessera-test-suites"
        / "playground"
        / "builds"
        / f"{service}-service.jam",
        "rb",
    ).read()
    wi_code_hash = Hash.blake2b(wi_service_code)
    wi_service = ServiceId(1)

    state.delta[wi_service].service = AccountMetadata(
        code_hash=wi_code_hash,
        balance=Balance(10**12),  # plenty of balance so set_storage cannot fail
        gas_limit=Gas(50_000),
        min_gas=Gas(1_000),
        num_i=Ai(0),
        num_o=Ao(0),
    )
    # Put the code preimage and mark it available for lookup at this timeslot
    state.delta[wi_service].preimages[wi_code_hash] = Bytes(wi_service_code)
    state.delta[wi_service].lookup[
        LookupTable(hash=wi_code_hash, length=BlobLength(len(wi_service_code)))
    ] = Timestamps([state.tau])

    # ---- Work item: payload is optional here; accumulate falls back to my_info().code_hash
    wi = WorkItem(
        service=wi_service,
        code_hash=wi_code_hash,
        payload=Bytes(b""),                 # we don't rely on items; fallback uses code_hash
        refine_gas_limit=Gas(1_000),
        accumulate_gas_limit=Gas(5_000),
        import_segments=ImportSpecs([]),
        extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),           # keep 1 to stay consistent with your pipeline
    )
    package.items.append(wi)

    # ---- Refine
    r, e, u = PsiR(0, p=package, auth_trace=b"", i_segments=[[]], e_offset=0).execute()
    print(f"Refine status={r} gas_used={u} exports={e}")

    # ---- Accumulate
    partial_state = StateContext(
        service_accounts=state.delta,
        validator_keys=state.iota,
        authorizer_keys=state.phi,
        privileges=state.chi,
    )
    timeslot = TimeSlot(state.tau)
    gas = Gas(10_000)

    lookupTable= LookupTable(hash=wi_code_hash, length=BlobLength(len(wi_service_code)))
    print("lookup bhai",state.delta[wi_service].lookup.get(lookupTable))


    # from jam.types.state.accumulation.types import OperandTuples
    # operands = OperandTuples([])

    # new_state_ctx, deferred_transfers, commit_opt, gas_left, preimages = PsiA(
    #     partial_state, timeslot, wi_service, gas, operands
    # ).execute()

    # # ---- Assert storage updated by accumulate::lookup
    # svc = new_state_ctx.service_accounts[wi_service]

    # # diagnostic count (may be 0 if your pipeline doesn't pass items)
    # n_items = svc.storage[key32(b"acc_items_len")]
    # print("acc_items_len:", int.from_bytes(bytes(n_items or b""), "little") if n_items else None)

    # key_used = svc.storage[key32(b"lookup_key")]
    # found = svc.storage[key32(b"lookup_found")]
    # blob = svc.storage[key32(b"lookup_blob")]

    # print("lookup_key:", key_used)
    # print("lookup_found:", found)
    # print("lookup_blob_len:", len(blob) if blob else None)

    # assert key_used is not None, "service didn't record lookup key"
    # assert found is not None and bytes(found) == b"\x01", "lookup said 'not found'"

    # # The looked-up blob should be exactly the code preimage we provided
    # assert blob is not None and bytes(blob) == wi_service_code
