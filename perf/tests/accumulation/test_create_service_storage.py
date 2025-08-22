from pathlib import Path
import struct
import pytest

from jam.execution.host_calls.invocations.refine import PsiR
from jam.execution.host_calls.invocations.accumulate import PsiA

from jam.settings import setup_setting
from jam.state.ghost import GhostState
from jam.state.state import setup_state

from jam.types.protocol.core import (
    Balance, Gas, ServiceId, WorkPackageHash, BlobLength, ExportsRoot,
)
from jam.types.protocol.crypto import Hash, OpaqueHash
from jam.types.state.delta import AccountMetadata, Ai, Ao, LookupTable, Timestamps
from jam.types.work.item import WorkItem, ImportSpecs, ExtrinsicSpecs
from jam.types.state.accumulation.types import StateContext, OperandTuple, OperandTuples

from tsrkit_types.enum import Uint
from tsrkit_types.bytes import Bytes as TBytes
from tsrkit_types import Bytes as RawBytes


# ---------- helpers ----------

def _artifact(name: str) -> Path:
    p = (
        Path(__file__).parents[4]
        / "tessera-test-suites"
        / "playground"
        / "builds"
        / f"{name}-service.jam"
    )
    if not p.exists():
        pytest.skip(f"Missing artifact: {p}")
    return p


def _register(state, sid: ServiceId, code: bytes):
    ch = Hash.blake2b(code)

    # install metadata
    state.delta[sid].service = AccountMetadata(
        code_hash=ch,
        balance=Balance(10_000_000),  # plenty for storage growth
        gas_limit=Gas(80_000),
        min_gas=Gas(1_000),
        num_i=Ai(0),
        num_o=Ao(0),
    )

    # make code-loadable
    state.delta[sid].preimages[ch] = TBytes(code)
    state.delta[sid].lookup[LookupTable(hash=ch, length=BlobLength(len(code)))] = Timestamps([state.tau])

    return ch


def _isegs_for(pkg):
    # one empty list per item
    return [[] for _ in range(len(pkg.items))]


def _pkg_hash(pkg) -> WorkPackageHash:
    return WorkPackageHash(Hash.blake2b(pkg.encode()))


def _ops(pkg_hash: WorkPackageHash, r1, item_gas: int = 10) -> OperandTuples:
    """
    Build a single-item OperandTuples with non-zero per-item gas,
    so the VM keeps and processes the item.
    """
    zero32 = bytes(32)
    return OperandTuples([
        OperandTuple(
            h=pkg_hash,
            e=ExportsRoot(zero32),
            a=OpaqueHash(zero32),
            y=OpaqueHash(zero32),
            g=Uint(item_gas),   # non-zero
            d=r1,               # refine result
            o=RawBytes(b""),    # no extra operand bytes
        )
    ])


def _read_storage_by_raw_key(u_state: StateContext, sid: ServiceId, raw_key: bytes) -> bytes | None:
    """
    Access storage through the hashed key that JAM uses externally:
    hashed_key = blake2b(raw_key), typed as Bytes[32].
    """
    acc = u_state.service_accounts[sid]
    typed_key32 = TBytes[32](bytes(Hash.blake2b(raw_key)))
    try:
        v = acc.storage[typed_key32]
    except KeyError:
        return None
    return v.to_bytes() if hasattr(v, "to_bytes") else bytes(v)


# ---------- tests ----------

def test_storage_set_then_get(tmp_path):
    # state + register
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, str(tmp_path))
    state = setup_state(settings.state_db, GhostState.genesis())

    sid = ServiceId(4242)
    code = _artifact("create_service_storage").read_bytes()
    ch = _register(state, sid, code)

    from jam.utils.dummy.dummy_package import create_dummy_package

    # ----- SET -----
    pkg1 = create_dummy_package()
    key = b"mykey"
    val = b"seed-value"
    payload1 = bytes([0x01, len(key)]) + key + val  # [op=0x01][klen][key][val]
    pkg1.items.append(WorkItem(
        service=sid, code_hash=ch, payload=TBytes(payload1),
        refine_gas_limit=Gas(50_000), accumulate_gas_limit=Gas(50_000),
        import_segments=ImportSpecs([]), extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    ))

    r1, _e1, _u1 = PsiR(0, p=pkg1, auth_trace=b"", i_segments=_isegs_for(pkg1), e_offset=0).execute()
    assert r1.get_key() == "ok"
    ops1 = _ops(_pkg_hash(pkg1), r1, item_gas=1000)

    partial1 = StateContext(
        service_accounts=state.delta,
        validator_keys=state.iota,
        authorizer_keys=state.phi,
        privileges=state.chi,
    )
    print("psiA started")
    u_after_set, *_ = PsiA(partial1, state.tau, sid, Gas(50_000), o=ops1).execute()

    # verify by reading hashed keys from returned StateContext
    assert _read_storage_by_raw_key(u_after_set, sid, b"/last_error").startswith(b"OK:Set")
    assert _read_storage_by_raw_key(u_after_set, sid, key) == val

    # ----- GET -----
    pkg2 = create_dummy_package()
    payload2 = bytes([0x02, len(key)]) + key          # [op=0x02][klen][key]
    pkg2.items.append(WorkItem(
        service=sid, code_hash=ch, payload=TBytes(payload2),
        refine_gas_limit=Gas(50_000), accumulate_gas_limit=Gas(50_000),
        import_segments=ImportSpecs([]), extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    ))

    r2, *_ = PsiR(0, p=pkg2, auth_trace=b"", i_segments=_isegs_for(pkg2), e_offset=0).execute()
    assert r2.get_key() == "ok"
    ops2 = _ops(_pkg_hash(pkg2), r2, item_gas=10)

    # IMPORTANT: thread the updated service_accounts forward
    partial2 = StateContext(
        service_accounts=u_after_set.service_accounts,
        validator_keys=state.iota,
        authorizer_keys=state.phi,
        privileges=state.chi,
    )
    u_after_get, *_ = PsiA(partial2, state.tau, sid, Gas(50_000), o=ops2).execute()

    assert _read_storage_by_raw_key(u_after_get, sid, b"/last_error").startswith(b"OK:Get")
    assert _read_storage_by_raw_key(u_after_get, sid, b"/last_retrieved") == val


def test_create_service_then_status(tmp_path):
    # state + register
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, str(tmp_path))
    state = setup_state(settings.state_db, GhostState.genesis())

    sid = ServiceId(4242)
    code = _artifact("create_service_storage").read_bytes()
    ch = _register(state, sid, code)

    # preload a code blob the service can reference via create_service()
    hello_code = _artifact("hello").read_bytes()
    hello_hash = Hash.blake2b(hello_code)
    state.delta[sid].preimages[hello_hash] = TBytes(hello_code)
    state.delta[sid].lookup[LookupTable(hash=hello_hash, length=BlobLength(len(hello_code)))] = Timestamps([state.tau])

    from jam.utils.dummy.dummy_package import create_dummy_package

    # ----- CREATE SERVICE -----
    pkg1 = create_dummy_package()
    payload1 = bytes([0x10]) + bytes(hello_hash) + struct.pack("<QQQ", len(hello_code), 15_000, 2_000)
    pkg1.items.append(WorkItem(
        service=sid, code_hash=ch, payload=TBytes(payload1),
        refine_gas_limit=Gas(50_000), accumulate_gas_limit=Gas(50_000),
        import_segments=ImportSpecs([]), extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    ))

    r1, *_ = PsiR(0, p=pkg1, auth_trace=b"", i_segments=_isegs_for(pkg1), e_offset=0).execute()
    assert r1.get_key() == "ok"
    ops1 = _ops(_pkg_hash(pkg1), r1, item_gas=1000)

    partial1 = StateContext(
        service_accounts=state.delta,
        validator_keys=state.iota,
        authorizer_keys=state.phi,
        privileges=state.chi,
    )
    u_after_create, *_ = PsiA(partial1, state.tau, sid, Gas(50_000), o=ops1).execute()

    assert _read_storage_by_raw_key(u_after_create, sid, b"/last_error") == b"OK:ServiceCreated"
    assert _read_storage_by_raw_key(u_after_create, sid, b"/last_created_service") is not None

    # ----- STATUS / GAS PROBE -----
    pkg2 = create_dummy_package()
    payload2 = bytes([0xFF])
    pkg2.items.append(WorkItem(
        service=sid, code_hash=ch, payload=TBytes(payload2),
        refine_gas_limit=Gas(50_000), accumulate_gas_limit=Gas(50_000),
        import_segments=ImportSpecs([]), extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    ))

    r2, *_ = PsiR(0, p=pkg2, auth_trace=b"", i_segments=_isegs_for(pkg2), e_offset=0).execute()
    assert r2.get_key() == "ok"
    ops2 = _ops(_pkg_hash(pkg2), r2, item_gas=10)

    partial2 = StateContext(
        service_accounts=u_after_create.service_accounts,
        validator_keys=state.iota,
        authorizer_keys=state.phi,
        privileges=state.chi,
    )
    u_after_status, *_ = PsiA(partial2, state.tau, sid, Gas(50_000), o=ops2).execute()

    # `/status_ops` (4 bytes) and `/status_gas_probe` (16 bytes) should now be set
    assert _read_storage_by_raw_key(u_after_status, sid, b"/last_error") == b"OK:Status"
    assert _read_storage_by_raw_key(u_after_status, sid, b"/status_ops") is not None
    gas_probe = _read_storage_by_raw_key(u_after_status, sid, b"/status_gas_probe")
    assert gas_probe is not None and len(gas_probe) == 16
