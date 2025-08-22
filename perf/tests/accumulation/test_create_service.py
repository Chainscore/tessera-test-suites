# perf/tests/accumulation/test_create_service.py

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


def key32(label: bytes) -> Bytes[32]:
    raw = bytearray(32)
    n = min(32, len(label))
    raw[:n] = label[:n]
    return Bytes[32](bytes(raw))


def encode_params(code_hash: Bytes[32], code_len: int, min_item_gas: int, min_memo_gas: int) -> Bytes:
    return Bytes(
        bytes(code_hash)
        + int(code_len).to_bytes(4, "little", signed=False)
        + int(min_item_gas).to_bytes(8, "little", signed=False)
        + int(min_memo_gas).to_bytes(8, "little", signed=False)
    )


def test_create_service(tmp_path):
    parent_service_name = "create_service"  # builds/{parent_service_name}-service.jam
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, str(tmp_path))
    state = setup_state(settings.state_db, GhostState.genesis())

    # --- Load parent service code (.jam) and register as ServiceId(1)
    parent_code = open(
        Path(__file__).parents[4]
        / "tessera-test-suites"
        / "playground"
        / "builds"
        / f"{parent_service_name}-service.jam",
        "rb",
    ).read()
    parent_hash = Hash.blake2b(parent_code)
    S_PARENT = ServiceId(1)

    state.delta[S_PARENT].service = AccountMetadata(
        code_hash=parent_hash,
        balance=Balance(10**12),
        gas_limit=Gas(50_000),
        min_gas=Gas(1_000),
        num_i=Ai(0),
        num_o=Ao(0),
    )
    # Preimage + availability timestamp for the parent code
    state.delta[S_PARENT].preimages[parent_hash] = Bytes(parent_code)
    state.delta[S_PARENT].lookup[
        LookupTable(hash=parent_hash, length=BlobLength(len(parent_code)))
    ] = Timestamps([state.tau])

    # --- Child code (for the created service): reuse same blob for simplicity
    child_code = parent_code
    child_hash = Hash.blake2b(child_code)
    child_len = len(child_code)

    # Gas params we want the child to have
    MIN_ITEM_GAS = 2_000
    MIN_MEMO_GAS = 3_000

    # --- Work item payload encodes (child_hash, child_len, min_item_gas, min_memo_gas)
    payload = encode_params(child_hash, child_len, MIN_ITEM_GAS, MIN_MEMO_GAS)

    package = create_dummy_package()
    wi = WorkItem(
        service=S_PARENT,
        code_hash=parent_hash,
        payload=Bytes(payload),
        refine_gas_limit=Gas(10_000),
        accumulate_gas_limit=Gas(10_000),
        import_segments=ImportSpecs([]),
        extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),  # ensure the item flows into accumulate
    )
    package.items.append(wi)

    # --- Refine
    r, e, u = PsiR(0, p=package, auth_trace=b"", i_segments=[[]], e_offset=0).execute()
    print(f"Refine status={r} gas_used={u} exports={e}")

    # --- Accumulate (this calls accumulate::create_service)
    partial = StateContext(
        service_accounts=state.delta,
        validator_keys=state.iota,
        authorizer_keys=state.phi,
        privileges=state.chi,
    )
    timeslot = TimeSlot(state.tau)
    gas = Gas(20_000)

    from jam.types.state.accumulation.types import OperandTuples
    operands = OperandTuples([])

    new_state_ctx, deferred, commit_opt, gas_left, preimages = PsiA(
        partial, timeslot, S_PARENT, gas, operands
    ).execute()

    parent_acct = new_state_ctx.service_accounts[S_PARENT]

    # --- Read success flag + child id from parent storage
    ok_flag = parent_acct.storage[key32(b"create_ok")]
    assert ok_flag is not None and bytes(ok_flag) == b"\x01", "create_service failed (flag not set)"

    child_id_le = parent_acct.storage[key32(b"created_service_id")]
    assert child_id_le is not None, "child id not written"
    child_id = int.from_bytes(bytes(child_id_le), "little")
    S_CHILD = ServiceId(child_id)

    # --- Validate the child account metadata
    child_acct = new_state_ctx.service_accounts[S_CHILD]
    assert child_acct.service.code_hash == child_hash, "child code_hash mismatch"
    assert int(child_acct.service.gas_limit) == MIN_ITEM_GAS, "child min_item_gas mismatch"
    assert int(child_acct.service.min_gas) == MIN_MEMO_GAS, "child min_memo_gas mismatch"

    # Child should have at least the basic threshold balance (the transfer is internal to create_service)
    assert int(child_acct.service.balance) >= int(child_acct.t), "child balance below threshold"

    print("✅ create_service ok; new service id:", int(S_CHILD))
