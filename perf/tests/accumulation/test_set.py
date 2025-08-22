import struct
from pathlib import Path

import pytest

from jam.execution.host_calls.invocations.refine import PsiR
from jam.execution.host_calls.invocations.accumulate import PsiA

from jam.settings import setup_setting
from jam.state.ghost import GhostState
from jam.state.state import setup_state

from jam.types.protocol.core import (
    Balance,
    Gas,
    ServiceId,
    WorkPackageHash,
    BlobLength,
    ExportsRoot,
    OpaqueHash,
)
from jam.types.protocol.crypto import Hash

from jam.types.state.delta import AccountMetadata, Ai, Ao, LookupTable, Timestamps

from jam.types.work.item import WorkItem, ImportSpecs, ExtrinsicSpecs

from jam.types.state.accumulation.types import (
    StateContext,
    OperandTuple,
    OperandTuples,
)

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

    # Install metadata
    state.delta[sid].service = AccountMetadata(
        code_hash=ch,
        balance=Balance(1_000_000),
        gas_limit=Gas(80_000),
        min_gas=Gas(1_000),
        num_i=Ai(0),
        num_o=Ao(0),
    )

    # Preimage so the runner can load code
    state.delta[sid].preimages[ch] = TBytes(code)

    # Seed lookup so AccountData.historical_lookup() can validate the preimage.
    # The implementation uses: LookupTable(hash=ch, length=BlobLength(len(self.lookup[ch])))
    # We store exactly one timestamp → length=1.
    state.delta[sid].lookup[LookupTable(hash=ch, length=BlobLength(1))] = Timestamps([state.tau])

    # Optional “real-length” entry (harmless, matches other suites)
    state.delta[sid].lookup[LookupTable(hash=ch, length=BlobLength(len(code)))] = Timestamps([state.tau])

    return ch


def _isegs_for(pkg):
    return [[] for _ in range(len(pkg.items))]


def _decode_bytes_result(work_output_bytes: bytes) -> bytes:
    # Some runners wrap results as [u16_be_len][payload]
    if len(work_output_bytes) >= 2:
        n = int.from_bytes(work_output_bytes[:2], "big")
        if n == len(work_output_bytes) - 2:
            return work_output_bytes[2:]
    return work_output_bytes


def _kv_payload(k: bytes, v: bytes) -> bytes:
    return struct.pack("<QQ", len(k), len(v)) + k + v


def _pkg_hash_from_pkg(pkg) -> WorkPackageHash:
    # PsiR computes Hash.blake2b(pkg.encode())
    h = Hash.blake2b(pkg.encode())
    return WorkPackageHash(h)


def _op_tuples_for(pkg_hash: WorkPackageHash, r1) -> OperandTuples:
    zero32 = bytes(32)
    return OperandTuples([
        OperandTuple(
            h=pkg_hash,
            e=ExportsRoot(zero32),
            a=OpaqueHash(zero32),
            y=OpaqueHash(zero32),
            g=Uint(0),
            d=r1,                 # the WorkExecResult from refine
            o=RawBytes(b""),      # no extra operand bytes
        )
    ])


def _typed_pkg_key(pkg_hash: WorkPackageHash) -> RawBytes[32]:
    # AccountStorage is keyed by Bytes[32] (tsrkit_types generic)
    return RawBytes[32].decode_from(pkg_hash.encode())[0]


def _get_storage_value(state_like:StateContext, sid: ServiceId, key: RawBytes[32]) -> bytes | None:
    """
    Read service storage value by typed key (Bytes[32]).
    Returns raw bytes or None.
    """
    # access Delta → AccountData → storage
    if hasattr(state_like, "service_accounts"):
        acc = state_like.service_accounts[sid]
    else:
        return None

    # StorageView.get accepts only (key) — do NOT pass a default.
    try:
        entry = acc.storage.get(key)
    except AttributeError:
        # Some views only implement __getitem__/__contains__
        try:
            entry = acc.storage[key]
        except KeyError:
            return None

    if entry is None:
        return None
    # unwrap TBytes if necessary
    return entry.to_bytes() if hasattr(entry, "to_bytes") else entry


# ---------- tests ----------

def test_set_happy_path(tmp_path):
    # --- state & service ---
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, str(tmp_path))
    state = setup_state(settings.state_db, GhostState.genesis())

    code = _artifact("set").read_bytes()
    sid = ServiceId(101)
    ch = _register(state, sid, code)

    # Build a one-item work package for refine → payload is echoed by refine()
    from jam.utils.dummy.dummy_package import create_dummy_package

    pkg = create_dummy_package()
    key, val = b"user:1:name", b"Alice"
    payload = _kv_payload(key, val)

    wi = WorkItem(
        service=sid,
        code_hash=ch,
        payload=TBytes(payload),
        refine_gas_limit=Gas(40_000),
        accumulate_gas_limit=Gas(40_000),
        import_segments=ImportSpecs([]),
        extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    pkg.items.append(wi)

    # --- run refine to get WorkExecResult r1 ---
    r1, _e1, _u1 = PsiR(0, p=pkg, auth_trace=b"", i_segments=_isegs_for(pkg), e_offset=0).execute()
    assert r1.get_key() == "ok"
    pkg_hash = _pkg_hash_from_pkg(pkg)

    # --- build partial StateContext for PsiA and run accumulate ---
    partial = StateContext(
        service_accounts=state.delta,
        validator_keys=state.iota,
        authorizer_keys=state.phi,
        privileges=state.chi,
    )
    ops = _op_tuples_for(pkg_hash, r1)

    u2, transfers, opt_hash, gas_left, preimages = PsiA(
        partial, state.tau, sid, Gas(80_000), o=ops
    ).execute()  # PsiA.execute() takes no args

    # The service writes an ACK under the package hash with the stored value.
    ack_key = _typed_pkg_key(pkg_hash)
    got = _get_storage_value(u2, sid, ack_key)
    assert got == val, f"expected ack value {val!r}, got {got!r}"


def test_set_payload_too_small(tmp_path):
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, str(tmp_path))
    state = setup_state(settings.state_db, GhostState.genesis())

    code = _artifact("set").read_bytes()
    sid = ServiceId(102)
    ch = _register(state, sid, code)

    from jam.utils.dummy.dummy_package import create_dummy_package

    pkg = create_dummy_package()
    bad = b"\x00" * 8  # < 16 → too small
    wi = WorkItem(
        service=sid,
        code_hash=ch,
        payload=TBytes(bad),
        refine_gas_limit=Gas(40_000),
        accumulate_gas_limit=Gas(40_000),
        import_segments=ImportSpecs([]),
        extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    pkg.items.append(wi)

    r1, _e1, _u1 = PsiR(0, p=pkg, auth_trace=b"", i_segments=_isegs_for(pkg), e_offset=0).execute()
    assert r1.get_key() == "ok"
    pkg_hash = _pkg_hash_from_pkg(pkg)

    partial = StateContext(
        service_accounts=state.delta,
        validator_keys=state.iota,
        authorizer_keys=state.phi,
        privileges=state.chi,
    )
    ops = _op_tuples_for(pkg_hash, r1)
    u2, *_ = PsiA(partial, state.tau, sid, Gas(80_000), o=ops).execute()

    ack_key = _typed_pkg_key(pkg_hash)
    got = _get_storage_value(u2, sid, ack_key)
    assert got == b"ERR:payload_too_small"


def test_set_payload_truncated(tmp_path):
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, str(tmp_path))
    state = setup_state(settings.state_db, GhostState.genesis())

    code = _artifact("set").read_bytes()
    sid = ServiceId(103)
    ch = _register(state, sid, code)

    from jam.utils.dummy.dummy_package import create_dummy_package

    pkg = create_dummy_package()
    key, val = b"k", b"VVVVV"
    full = _kv_payload(key, val)
    bad = full[:-2]  # chop tail → truncated

    wi = WorkItem(
        service=sid,
        code_hash=ch,
        payload=TBytes(bad),
        refine_gas_limit=Gas(40_000),
        accumulate_gas_limit=Gas(40_000),
        import_segments=ImportSpecs([]),
        extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    pkg.items.append(wi)

    r1, _e1, _u1 = PsiR(0, p=pkg, auth_trace=b"", i_segments=_isegs_for(pkg), e_offset=0).execute()
    assert r1.get_key() == "ok"
    pkg_hash = _pkg_hash_from_pkg(pkg)

    partial = StateContext(
        service_accounts=state.delta,
        validator_keys=state.iota,
        authorizer_keys=state.phi,
        privileges=state.chi,
    )
    ops = _op_tuples_for(pkg_hash, r1)
    u2, *_ = PsiA(partial, state.tau, sid, Gas(80_000), o=ops).execute()

    ack_key = _typed_pkg_key(pkg_hash)
    got = _get_storage_value(u2, sid, ack_key)
    assert got == b"ERR:payload_truncated"
