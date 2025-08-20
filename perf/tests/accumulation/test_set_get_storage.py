# perf/tests/accumulation/test_set_get_storage.py

from jam.state.state import setup_state
from jam.settings import setup_setting
from jam.utils.dummy.dummy_package import create_dummy_package

from jam.types.protocol.core import Balance, BlobLength, Gas, ServiceId
from jam.types.protocol.crypto import Hash
from jam.types.state.delta import AccountMetadata, Ai, Ao, LookupTable, Timestamps
from jam.types.work.item import WorkItem, ImportSpecs, ExtrinsicSpecs
from jam.execution.host_calls.invocations.refine import PsiR
from jam.execution.host_calls.invocations.accumulate import PsiA
from jam.types.state.accumulation.types import StateContext, OperandTuples
from tsrkit_types.bytes import Bytes as TBytes
from tsrkit_types.enum import Uint


def _artifact(name: str) -> Path:


def _register_new_account(state, sid: ServiceId, code: bytes) -> bytes:
    ch = Hash.blake2b(code)
    state.delta[sid].service = AccountMetadata(
        code_hash=ch,
        balance=Balance(1_000_000),
        gas_limit=Gas(50_000),
        min_gas=Gas(1_000),
        num_i=Ai(0),
        num_o=Ao(0),
    )
    state.delta[sid].preimages[ch] = TBytes(code)
    state.delta[sid].lookup[LookupTable(hash=ch, length=BlobLength(len(code)))] = Timestamps([state.tau])
    return ch


def _install_code_without_reset(state, sid: ServiceId, code: bytes) -> bytes:
    """Swap the code hash on an existing account without touching storage."""
    ch = Hash.blake2b(code)
    state.delta[sid].preimages[ch] = TBytes(code)
    state.delta[sid].lookup[LookupTable(hash=ch, length=BlobLength(len(code)))] = Timestamps([state.tau])
    # only update the code hash field; do not replace AccountMetadata struct wholesale
    state.delta[sid].service.code_hash = ch
    return ch


def _isegs_for(pkg):
    return [[] for _ in range(len(pkg.items))]


def test_set_then_get_storage(db_path):
    # --- setup ---
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
    state = setup_state(settings.state_db, GhostState.genesis())
    svc = ServiceId(42)

    key = b"mykey"
    val = b"seed-value"

    # ===== 1) SET phase =====
    set_code = _artifact("set_storage").read_bytes()
    ch_set = _register_new_account(state, svc, set_code)

    pkg_set = create_dummy_package()
    payload_set = struct.pack("<Q", len(key)) + key + struct.pack("<Q", len(val)) + val
    wi_set = WorkItem(
        service=svc, code_hash=ch_set, payload=TBytes(payload_set),
        refine_gas_limit=Gas(50_000), accumulate_gas_limit=Gas(50_000),
        import_segments=ImportSpecs([]), extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    pkg_set.items.append(wi_set)

    # refine
    rS, eS, uS = PsiR(0, p=pkg_set, auth_trace=b"", i_segments=_isegs_for(pkg_set), e_offset=0).execute()
    assert rS.get_key() == "ok"

    # accumulate — runs the SetStorage::accumulate code currently installed
    partial = StateContext(
        service_accounts=state.delta,
        validator_keys=state.iota,
        authorizer_keys=state.phi,
        privileges=state.chi,
    )
    updated_state, *_ = PsiA(u=partial, t=state.tau, s=svc, g=Gas(50_000), o=OperandTuples([])).execute()

    # Check echo from set: raw key "/echo_set"
    echo_set_key32 = TBytes[32](bytes(Hash.blake2b(b"/echo_set")))
    got = updated_state.service_accounts[svc].storage[echo_set_key32]
    assert got is not None, "echo_set missing (set_storage did not run?)"
    assert bytes(got) == b"OK"

    # ===== 2) GET phase (switch service code to get_storage WITHOUT resetting storage) =====
    get_code = _artifact("get_storage").read_bytes()
    ch_get = _install_code_without_reset(state, svc, get_code)

    pkg_get = create_dummy_package()
    payload_get = struct.pack("<Q", len(key)) + key  # only key
    wi_get = WorkItem(
        service=svc, code_hash=ch_get, payload=TBytes(payload_get),
        refine_gas_limit=Gas(50_000), accumulate_gas_limit=Gas(50_000),
        import_segments=ImportSpecs([]), extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    pkg_get.items.append(wi_get)

    rG, eG, uG = PsiR(0, p=pkg_get, auth_trace=b"", i_segments=_isegs_for(pkg_get), e_offset=0).execute()
    assert rG.get_key() == "ok"

    # accumulate — runs the GetStorage::accumulate code now installed
    partial2 = StateContext(
        service_accounts=state.delta,
        validator_keys=state.iota,
        authorizer_keys=state.phi,
        privileges=state.chi,
    )
    updated_state2, *_ = PsiA(u=partial2, t=state.tau, s=svc, g=Gas(50_000), o=OperandTuples([])).execute()

    # Check echo from get: raw key "/echo_get" should contain the exact value we set
    echo_get_key32 = TBytes[32](bytes(Hash.blake2b(b"/echo_get")))
    got2 = updated_state2.service_accounts[svc].storage[echo_get_key32]
    assert got2 is not None, "echo_get missing (get_storage did not run?)"
    assert bytes(got2) == val
