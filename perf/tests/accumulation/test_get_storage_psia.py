
from jam.state.state import setup_state
from jam.settings import setup_setting
from jam.utils.dummy.dummy_package import create_dummy_package

from jam.types.protocol.core import Balance, BlobLength, Gas, ServiceId
from jam.types.protocol.crypto import Hash
from jam.types.state.delta import AccountMetadata, Ai, Ao, LookupTable, Timestamps
from jam.types.work.item import WorkItem, ImportSpecs, ExtrinsicSpecs
from jam.types.state.accumulation.types import StateContext, OperandTuples
from tsrkit_types.bytes import Bytes
from tsrkit_types.enum import Uint

from jam.execution.host_calls.invocations.refine import PsiR
from jam.execution.host_calls.invocations.accumulate import PsiA

def _artifact(name: str) -> Path:

def _register(state, sid: ServiceId, code: bytes):
    ch = Hash.blake2b(code)
    state.delta[sid].service = AccountMetadata(
        code_hash=ch, balance=Balance(1_000_000),
        gas_limit=Gas(50_000), min_gas=Gas(1_000), num_i=Ai(0), num_o=Ao(0),
    )
    state.delta[sid].preimages[ch] = Bytes(code)
    state.delta[sid].lookup[LookupTable(hash=ch, length=BlobLength(len(code)))] = Timestamps([state.tau])
    return ch

def _isegs_for(pkg):
    return [[] for _ in range(len(pkg.items))]

def test_kvget_via_psia(db_path):
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
    state = setup_state(settings.state_db, GhostState.genesis())
    package = create_dummy_package()

    # 1) Register kvset and kvget
    kvset_code = _artifact("set_storage").read_bytes()
    kvget_code = _artifact("get_storage").read_bytes()
    svc_set, svc_get = ServiceId(1), ServiceId(2)
    ch_set = _register(state, svc_set, kvset_code)
    ch_get = _register(state, svc_get, kvget_code)

    # 2) Prepare key/value
    logical_key = b"kvset-psia-test-key"
    key_t = Hash.blake2b(logical_key)          # TYPED 32B KEY (not raw bytes)
    key32_bytes = bytes(key_t)                 # If you need raw bytes, this is fine
    value = b"stored-by-accumulate"

    # 3) Put a work item for kvset (payload = key32||value)
    wi_set = WorkItem(
        service=svc_set, code_hash=ch_set, payload=Bytes(key32_bytes + value),
        refine_gas_limit=Gas(20_000), accumulate_gas_limit=Gas(20_000),
        import_segments=ImportSpecs([]), extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    package.items.append(wi_set)

    # 3a) refine (no mutation)
    rR, _, _ = PsiR(0, p=package, auth_trace=b"", i_segments=_isegs_for(package), e_offset=0).execute()
    assert rR.get_key() == "ok"

    # 3b) accumulate (perform set_storage)
    partial = StateContext(
        service_accounts=state.delta, validator_keys=state.iota,
        authorizer_keys=state.phi, privileges=state.chi,
    )
    u_after_set, _, _, _, _ = PsiA(
        u=partial, s=svc_set, t=state.tau, g=Gas(20_000), o=OperandTuples([])
    ).execute()

    # 4) Now query via kvget (payload = key32)
    wi_get = WorkItem(
        service=svc_get, code_hash=ch_get, payload=Bytes(key32_bytes),
        refine_gas_limit=Gas(20_000), accumulate_gas_limit=Gas(20_000),
        import_segments=ImportSpecs([]), extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    package.items.append(wi_get)

    rR2, _, _ = PsiR(1, p=package, auth_trace=b"", i_segments=_isegs_for(package), e_offset=0).execute()
    assert rR2.get_key() == "ok"

    partial2 = StateContext(
        service_accounts=u_after_set.service_accounts,  # carry forward previous state
        validator_keys=state.iota, authorizer_keys=state.phi, privileges=state.chi,
    )
    u_after_get, _, _, _, _ = PsiA(
        u=partial2, s=svc_get, t=state.tau, g=Gas(20_000), o=OperandTuples([])
    ).execute()

    # 5) kvget writes results under "/last_get_status" and "/last_get_value" in ITS OWN storage
    status_key = Hash.blake2b(b"/last_get_status")  # TYPED KEY!
    value_key  = Hash.blake2b(b"/last_get_value")

    storage_get = u_after_get.service_accounts[svc_get].storage

    assert status_key in storage_get
    assert bytes(storage_get[status_key]) == b"SOME"
    assert value_key in storage_get
    assert bytes(storage_get[value_key]) == value
