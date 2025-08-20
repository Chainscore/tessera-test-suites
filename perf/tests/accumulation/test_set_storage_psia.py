
from jam.state.state import setup_state
from jam.settings import setup_setting
from jam.utils.dummy.dummy_package import create_dummy_package

from jam.types.protocol.core import Balance, BlobLength, Gas, ServiceId
from jam.types.protocol.crypto import Hash
from jam.types.state.delta import AccountMetadata, Ai, Ao, LookupTable, Timestamps
from jam.types.work.item import WorkItem, ImportSpecs, ExtrinsicSpecs
from tsrkit_types.bytes import Bytes
from tsrkit_types.enum import Uint

from jam.execution.host_calls.invocations.refine import PsiR
from jam.execution.host_calls.invocations.accumulate import PsiA
from jam.types.state.accumulation.types import StateContext, OperandTuples


def _artifact(name: str) -> Path:
    p = (
        Path(__file__).parents[4]
        / "tessera-test-suites"
        / "playground"
        / "builds"
        / f"{name}-service.jam"


def _register(state, sid: ServiceId, code: bytes):
    ch = Hash.blake2b(code)
    state.delta[sid].service = AccountMetadata(
        code_hash=ch,
        balance=Balance(1_000_000),
        gas_limit=Gas(50_000),
        min_gas=Gas(1_000),
        num_i=Ai(0),
        num_o=Ao(0),
    )
    state.delta[sid].preimages[ch] = Bytes(code)
    state.delta[sid].lookup[
        LookupTable(hash=ch, length=BlobLength(len(code)))
    ] = Timestamps([state.tau])
    return ch


def _isegs_for(pkg):
    # one empty import-segment list per item
    return [[] for _ in range(len(pkg.items))]


def test_kvset_changes_storage_via_psia(db_path):
    # --- bootstrap state ---
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
    state = setup_state(settings.state_db, GhostState.genesis())
    package = create_dummy_package()

    # --- load/register kvset bytecode ---
    code = _artifact("set_storage").read_bytes()
    svc = ServiceId(1)
    ch = _register(state, svc, code)

    # Build payload: key32 (already blake2b) + value
    key32 = bytes(Hash.blake2b(b"kvset-psia-test-key"))
    value = b"stored-by-accumulate"
    payload = key32 + value
    print("bro1",state.delta[svc].storage[Bytes(key32)])
    # Put a work-item so refine can run (and emit the same payload)
    wi = WorkItem(
        service=svc,
        code_hash=ch,
        payload=Bytes(payload),
        refine_gas_limit=Gas(20_000),
        accumulate_gas_limit=Gas(20_000),
        import_segments=ImportSpecs([]),
        extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    package.items.append(wi)

    # --- 1) refine (PsiR) — no storage change expected ---
    rR, eR, uR = PsiR(
        0, p=package, auth_trace=b"", i_segments=_isegs_for(package), e_offset=0
    ).execute()
    print("bro2",state.delta[svc].storage[Bytes(key32)])

    assert rR.get_key() == "ok"
    assert rR.unwrap() == payload
    assert len(eR) == 0
    assert int(uR) >= 0
    # Ensure refine didn’t mutate persistent storage:
    # assert key32 not in state.delta[svc].storage
    print("bro3",state.delta[svc].storage[Bytes(key32)])
    # --- 2) accumulate (PsiA) — actually perform set_storage ---
    partial = StateContext(
        service_accounts=state.delta,
        validator_keys=state.iota,
        authorizer_keys=state.phi,
        privileges=state.chi,
    )
    updated_state, deferred, commit, gas_used, preimages = PsiA(
        u=partial, s=svc, t=state.tau, g=Gas(20_000), o=OperandTuples([])
    ).execute()
    # print("psiA outcomes",updated_state,deferred,commit,gas_used,preimages)

    print("bro4",updated_state.service_accounts[svc].storage[key32])
    print("bro5",updated_state.service_accounts[svc].storage[Bytes(key32)])

    # Verify the returned StateContext reflects the committed write:
    # assert key32 in updated_state.service_accounts[svc].storage
    # assert bytes(updated_state.service_accounts[svc].storage[key32]) == value

    # (Optional) If your framework expects the global state to adopt the update:
    # state.delta = updated_state.service_accounts
