import struct, time
from pathlib import Path

import pytest

from jam.execution.host_calls.invocations.refine import PsiR
from jam.execution.host_calls.invocations.accumulate import PsiA  # <-- STOCK PsiA

from jam.settings import setup_setting
from jam.state.ghost import GhostState
from jam.state.state import setup_state

from jam.types.protocol.core import Balance, Gas, ServiceId, WorkPackageHash, BlobLength, ExportsRoot
from jam.types.protocol.crypto import Hash, OpaqueHash
from jam.types.state.delta import AccountMetadata, Ai, Ao, LookupTable, Timestamps
from jam.types.work.item import WorkItem, ImportSpecs, ExtrinsicSpecs
from jam.types.state.accumulation.types import StateContext, OperandTuple, OperandTuples

from tsrkit_types import U16
from tsrkit_types.bytes import Bytes as TBytes
from tsrkit_types.enum import Uint


def _artifact(name: str) -> Path:
    p = Path(__file__).parents[4] / "tessera-test-suites" / "playground" / "builds" / f"{name}-service.jam"
    if not p.exists():
        pytest.skip(f"Missing artifact: {p}")
    return p

def _register(state, sid: ServiceId, code: bytes):
    ch = Hash.blake2b(code)
    state.delta[sid].service = AccountMetadata(
        code_hash=ch,
        balance=Balance(1_000_000),
        gas_limit=Gas(80_000),
        min_gas=Gas(1_000),
        num_i=Ai(0),
        num_o=Ao(0),
    )
    state.delta[sid].preimages[ch] = TBytes(code)
    state.delta[sid].lookup[LookupTable(hash=ch, length=BlobLength(1))] = Timestamps([state.tau])
    state.delta[sid].lookup[LookupTable(hash=ch, length=BlobLength(len(code)))] = Timestamps([state.tau])
    return ch

def _isegs_for(pkg): return [[] for _ in range(len(pkg.items))]
def _pkg_hash(pkg): return WorkPackageHash(Hash.blake2b(pkg.encode()))

def _ops(pkg_hash, r1, item_gas=10):
    zero32 = bytes(32)
    return OperandTuples([OperandTuple(
        h=pkg_hash, e=ExportsRoot(zero32), a=OpaqueHash(zero32), y=OpaqueHash(zero32),
        g=Gas(int(max(1, item_gas))), d=r1, o=TBytes(b""),
    )])

def _set_payload(k: bytes, v: bytes) -> bytes:
    return b"\x01" + struct.pack("<QQ", len(k), len(v)) + k + v

def _get_payload(k: bytes) -> bytes:
    return b"\x02" + struct.pack("<Q", len(k)) + k

def _metric_payload(elapsed_us: int) -> bytes:
    return b"\x03" + struct.pack("<Q", elapsed_us)

def _read_hashed(state_like: StateContext, sid: ServiceId, raw_key: bytes) -> bytes | None:
    acc = state_like.service_accounts[sid]
    key32 = TBytes[32].decode_from(Hash.blake2b(raw_key).encode())[0]
    try:
        entry = acc.storage.get(key32)
    except TypeError:
        try:
            entry = acc.storage[key32]
        except KeyError:
            entry = None
    if entry is None:
        return None
    return entry.to_bytes() if hasattr(entry, "to_bytes") else (bytes(entry) if isinstance(entry, (bytes, bytearray)) else bytes(entry))

def test_kv_probe(tmp_path):
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, str(tmp_path))
    state = setup_state(settings.state_db, GhostState.genesis())

    sid = ServiceId(7777)
    code = _artifact("update_storage").read_bytes()
    ch = _register(state, sid, code)

    # ---------- SET ----------
    from jam.utils.dummy.dummy_package import create_dummy_package
    pkg = create_dummy_package()
    key, val = b"mykey", b"seed-value"
    wi = WorkItem(
        service=sid, code_hash=ch, payload=TBytes(_set_payload(key, val)),
        refine_gas_limit=Gas(50_000), accumulate_gas_limit=Gas(50_000),
        import_segments=ImportSpecs([]), extrinsic=ExtrinsicSpecs([]),
        export_count=U16(0),
    )
    pkg.items.append(wi)

    r1, _, _ = PsiR(0, p=pkg, auth_trace=b"", i_segments=_isegs_for(pkg), e_offset=0).execute()
    assert r1.get_key() == "ok"
    ops = _ops(_pkg_hash(pkg), r1, item_gas=10)

    t0 = time.perf_counter()
    partial = StateContext(service_accounts=state.delta, validator_keys=state.iota, authorizer_keys=state.phi, privileges=state.chi)
    u_after_set, *_ = PsiA(partial, state.tau, sid, Gas(50_000), o=ops).execute()
    elapsed_us = int((time.perf_counter() - t0) * 1_000_000)

    assert _read_hashed(u_after_set, sid, b"/probe/echo_set") == b"OK"
    assert _read_hashed(u_after_set, sid, b"/probe/roundtrip") == val
    assert _read_hashed(u_after_set, sid, key) == val

    # ---------- record elapsed_us ----------
    pkg2 = create_dummy_package()
    wi2 = WorkItem(
        service=sid, code_hash=ch, payload=TBytes(_metric_payload(elapsed_us)),
        refine_gas_limit=Gas(50_000), accumulate_gas_limit=Gas(50_000),
        import_segments=ImportSpecs([]), extrinsic=ExtrinsicSpecs([]),
        export_count=U16(0),
    )
    pkg2.items.append(wi2)
    r2, _, _ = PsiR(0, p=pkg2, auth_trace=b"", i_segments=_isegs_for(pkg2), e_offset=0).execute()
    ops2 = _ops(_pkg_hash(pkg2), r2, item_gas=10)
    u_after_metric, *_ = PsiA(
        StateContext(
            service_accounts=u_after_set.service_accounts,
            validator_keys=u_after_set.validator_keys,
            authorizer_keys=u_after_set.authorizer_keys,
            privileges=u_after_set.privileges,
        ),
        state.tau, sid, Gas(50_000), o=ops2
    ).execute()

    assert _read_hashed(u_after_metric, sid, b"/metrics/echo") == b"TIMED"
    got_us_le = _read_hashed(u_after_metric, sid, b"/metrics/elapsed_us")
    assert got_us_le is not None and len(got_us_le) == 8
    got_us = int.from_bytes(got_us_le, "little")
    print(f"[kv_probe] accumulate elapsed ~{got_us} us (measured outside, recorded by service)")
    # sanity
    assert got_us > 0
