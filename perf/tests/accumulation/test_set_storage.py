# import struct
# from pathlib import Path

# import pytest

# from jam.execution.host_calls.invocations.refine import PsiR
# from jam.execution.host_calls.invocations.accumulate import PsiA

# from jam.settings import setup_setting
# from jam.state.ghost import GhostState
# from jam.state.state import setup_state

# from jam.types.protocol.core import (
#     Balance,
#     BlobLength,
#     ExportsRoot,
#     Gas,
#     OpaqueHash,
#     ServiceId,
#     WorkPackageHash,
# )
# from jam.types.protocol.crypto import Hash
# from jam.types.state.delta import AccountMetadata, Ai, Ao, LookupTable, Timestamps
# from jam.types.work.item import WorkItem, ImportSpecs, ExtrinsicSpecs
# from jam.types.state.accumulation.types import (
#     StateContext,
#     OperandTuple,
#     OperandTuples,
# )

# from tsrkit_types.enum import Uint
# from tsrkit_types.bytes import Bytes as TBytes
# from tsrkit_types import Bytes as RawBytes


# # ---------- helpers ----------

# def _artifact(name: str) -> Path:
#     p = (
#         Path(__file__).parents[4]
#         / "tessera-test-suites"
#         / "playground"
#         / "builds"
#         / f"{name}-service.jam"
#     )
#     if not p.exists():
#         pytest.skip(f"Missing artifact: {p}")
#     return p


# def _register(state, sid: ServiceId, code: bytes):
#     ch = Hash.blake2b(code)

#     state.delta[sid].service = AccountMetadata(
#         code_hash=ch,
#         balance=Balance(1_000_000),
#         gas_limit=Gas(80_000),
#         min_gas=Gas(1_000),
#         num_i=Ai(0),
#         num_o=Ao(0),
#     )
#     state.delta[sid].preimages[ch] = TBytes(code)

#     # Seed lookup to satisfy AccountData.historical_lookup()
#     state.delta[sid].lookup[LookupTable(hash=ch, length=BlobLength(1))] = Timestamps([state.tau])
#     state.delta[sid].lookup[LookupTable(hash=ch, length=BlobLength(len(code)))] = Timestamps([state.tau])

#     return ch


# def _isegs_for(pkg):
#     return [[] for _ in range(len(pkg.items))]


# def _kv_payload(k: bytes, v: bytes) -> bytes:
#     # Layout A: [k_len][k][v_len][v]
#     return struct.pack("<Q", len(k)) + k + struct.pack("<Q", len(v)) + v


# def _pkg_hash_from_pkg(pkg) -> WorkPackageHash:
#     return WorkPackageHash(Hash.blake2b(pkg.encode()))


# def _op_tuples_for(pkg_hash: WorkPackageHash, r1, gas_used: Gas) -> OperandTuples:
#     zero32 = bytes(32)
#     return OperandTuples([
#         OperandTuple(
#             h=pkg_hash,                 # WorkPackageHash (32-bytes newtype)
#             e=ExportsRoot(zero32),      # exports root (unused here)
#             a=OpaqueHash(zero32),       # auth root (unused here)
#             y=OpaqueHash(zero32),       # yield root (unused here)
#             g=Uint(int(gas_used)),      # refine gas, if your VM expects it
#             d=r1,                       # WorkExecResult from refine()
#             o=RawBytes(b""),            # extra bytes (unused)
#         )
#     ])


# def _typed_pkg_key(pkg_hash: WorkPackageHash) -> RawBytes[32]:
#     # Turn WorkPackageHash into Bytes[32] so we can read the 32B ACK without guessing a hash
#     return RawBytes[32].decode_from(pkg_hash.encode())[0]


# def _read_storage_hashed(state_like: StateContext, sid: ServiceId, raw_key: bytes) -> bytes | None:
#     """
#     Read service storage value by *raw* key; host may map raw keys to 32B with different hashes.
#     Try blake2b first, fall back to keccak256.
#     """
#     acc = state_like.service_accounts[sid]

#     k_blake = TBytes[32](bytes(Hash.blake2b(raw_key)))
#     k_keccak = TBytes[32](bytes(Hash.keccak256(raw_key)))

#     def _try(k32):
#         try:
#             v = acc.storage.get(k32)
#         except AttributeError:
#             try:
#                 v = acc.storage[k32]
#             except KeyError:
#                 return None
#         if v is None:
#             return None
#         return v.to_bytes() if hasattr(v, "to_bytes") else bytes(v)

#     return _try(k_blake) or _try(k_keccak)


# # ---------- test ----------

# def test_set_storage_refine_then_accumulate(tmp_path):
#     # 1) state setup
#     settings = setup_setting("data/god_mode", 3000, 2**16 - 1, str(tmp_path))
#     state = setup_state(settings.state_db, GhostState.genesis())

#     svc = ServiceId(4242)
#     code = _artifact("set_storage").read_bytes()
#     ch = _register(state, svc, code)

#     # KV to store
#     key = b"mykey"
#     val = b"seed-value"

#     # 2) package + refine
#     from jam.utils.dummy.dummy_package import create_dummy_package
#     pkg = create_dummy_package()
#     payload = _kv_payload(key, val)

#     wi = WorkItem(
#         service=svc,
#         code_hash=ch,
#         payload=TBytes(payload),
#         refine_gas_limit=Gas(50_000),
#         accumulate_gas_limit=Gas(50_000),
#         import_segments=ImportSpecs([]),
#         extrinsic=ExtrinsicSpecs([]),
#         export_count=Uint[16](0),
#     )
#     pkg.items.append(wi)

#     r1, _e1, u1 = PsiR(0, p=pkg, auth_trace=b"", i_segments=_isegs_for(pkg), e_offset=0).execute()
#     assert r1.get_key() == "ok"
#     pkg_hash = _pkg_hash_from_pkg(pkg)

#     # 3) accumulate with an OperandTuple built from refine output
#     ops = _op_tuples_for(pkg_hash, r1, u1)
#     partial = StateContext(
#         service_accounts=state.delta,
#         validator_keys=state.iota,
#         authorizer_keys=state.phi,
#         privileges=state.chi,
#     )
#     u2, *_ = PsiA(partial, state.tau, svc, Gas(50_000), o=ops).execute()

#     # 4) assertions

#     # (a) success sentinel written at raw key "/echo_set"
#     echo = _read_storage_hashed(u2, svc, b"/echo_set")
#     assert echo == b"OK", f"accumulate didn’t succeed, echo_set={echo!r}"

#     # (b) read-back value mirrored at "/echo_get"
#     echoed = _read_storage_hashed(u2, svc, b"/echo_get")
#     assert echoed == val, f"echo_get mismatch: expected {val!r}, got {echoed!r}"

#     # (c) 32-byte ACK under the package hash (no hashing ambiguity)
#     ack_key = _typed_pkg_key(pkg_hash)
#     acc = u2.service_accounts[svc]
#     try:
#         ack = acc.storage.get(ack_key)
#     except AttributeError:
#         ack = acc.storage[ack_key]
#     ack = ack.to_bytes() if hasattr(ack, "to_bytes") else bytes(ack)
#     assert ack == b"OK", f"ack under pkg-hash missing or wrong: {ack!r}"

#     # (d) the actual KV now present under whatever hash the host uses
#     stored = _read_storage_hashed(u2, svc, key)
#     assert stored == val, f"stored value mismatch: expected {val!r}, got {stored!r}"

import struct
from pathlib import Path
import pytest

from jam.execution.host_calls.invocations.refine import PsiR
from jam.execution.host_calls.invocations.accumulate import PsiA

from jam.settings import setup_setting
from jam.state.ghost import GhostState
from jam.state.state import setup_state

from jam.types.protocol.core import (
    Balance, BlobLength, ExportsRoot, Gas, OpaqueHash, ServiceId, WorkPackageHash,
)
from jam.types.protocol.crypto import Hash
from jam.types.state.delta import AccountMetadata, Ai, Ao, LookupTable, Timestamps
from jam.types.work.item import WorkItem, ImportSpecs, ExtrinsicSpecs
from jam.types.state.accumulation.types import StateContext, OperandTuple, OperandTuples

from tsrkit_types import U16
from tsrkit_types.enum import Uint
from tsrkit_types.bytes import Bytes as TBytes


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

    state.delta[sid].service = AccountMetadata(
        code_hash=ch,
        balance=Balance(1_000_000),
        gas_limit=Gas(80_000),
        min_gas=Gas(1_000),
        num_i=Ai(0),
        num_o=Ao(0),
    )
    state.delta[sid].preimages[ch] = TBytes(code)

    # seed historical_lookup entries (many trees look for length==1)
    state.delta[sid].lookup[LookupTable(hash=ch, length=BlobLength(1))] = Timestamps([state.tau])
    state.delta[sid].lookup[LookupTable(hash=ch, length=BlobLength(len(code)))] = Timestamps([state.tau])

    return ch


def _isegs_for(pkg):
    return [[] for _ in range(len(pkg.items))]


def _kv_payload(k: bytes, v: bytes) -> bytes:
    return struct.pack("<Q", len(k)) + k + struct.pack("<Q", len(v)) + v


def _pkg_hash_from_pkg(pkg) -> WorkPackageHash:
    return WorkPackageHash(Hash.blake2b(pkg.encode()))


def _op_tuples_for(pkg_hash, r1, u1_gas: Gas = Gas(1)) -> OperandTuples:
    # Use a positive per-item accumulate gas; some builders ignore zero-gas items.
    zero32 = bytes(32)
    return OperandTuples([
        OperandTuple(
            h=OpaqueHash(bytes(pkg_hash)),      # WorkPackageHash as an opaque 32B
            e=ExportsRoot(zero32),
            a=OpaqueHash(zero32),
            y=OpaqueHash(zero32),
            g=Uint(int(max(1, int(u1_gas)))),   # <- IMPORTANT: non-zero
            d=r1,                                # refine result (WorkExecResult)
            o=TBytes(b""),                       # no extra operand bytes
        )
    ])


def _to_bytes(x):
    return x.to_bytes() if hasattr(x, "to_bytes") else bytes(x)


def _read_storage_multi(state_like: StateContext, sid: ServiceId, raw_key: bytes) -> bytes | None:
    acc = state_like.service_accounts[sid]

    # try raw key
    try:
        v = acc.storage.get(TBytes(raw_key))
        if v is not None:
            return _to_bytes(v)
    except Exception:
        pass

    # try blake2b(key)
    try:
        v = acc.storage.get(TBytes[32](bytes(Hash.blake2b(raw_key))))
        if v is not None:
            return _to_bytes(v)
    except Exception:
        pass

    # try keccak(key)
    try:
        v = acc.storage.get(TBytes[32](bytes(Hash.keccak256(raw_key))))
        if v is not None:
            return _to_bytes(v)
    except Exception:
        pass

    return None


def _typed_pkg_key(pkg_hash: WorkPackageHash):
    return TBytes[32].decode_from(pkg_hash.encode())[0]


# ---------- the test ----------

def test_set_storage_refine_then_accumulate(tmp_path):
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, str(tmp_path))
    state = setup_state(settings.state_db, GhostState.genesis())

    svc = ServiceId(4242)
    code = _artifact("set_storage").read_bytes()
    ch = _register(state, svc, code)

    key = b"mykey"
    val = b"seed-value"

    from jam.utils.dummy.dummy_package import create_dummy_package
    pkg = create_dummy_package()
    payload = _kv_payload(key, val)

    wi = WorkItem(
        service=svc,
        code_hash=ch,
        payload=TBytes(payload),
        refine_gas_limit=Gas(50_000),
        accumulate_gas_limit=Gas(50_000),
        import_segments=ImportSpecs([]),
        extrinsic=ExtrinsicSpecs([]),
        export_count=Uint(0),
    )
    pkg.items.append(wi)

    r1, _e1, u1 = PsiR(0, p=pkg, auth_trace=b"", i_segments=_isegs_for(pkg), e_offset=0).execute()
    assert r1.get_key() == "ok"
    pkg_hash = _pkg_hash_from_pkg(pkg)
    ops = _op_tuples_for(pkg_hash, r1, Gas(10))  # pass a positive item gas

    partial = StateContext(
        service_accounts=state.delta,
        validator_keys=state.iota,
        authorizer_keys=state.phi,
        privileges=state.chi,
    )
    u2, *_ = PsiA(partial, state.tau, svc, Gas(50_000), o=ops).execute()
    # success sentinel
    echo = _read_storage_multi(u2, svc, b"/echo_set")
    assert echo == b"OK", f"accumulate didn’t succeed, echo_set={echo!r}"

    # echoed value
    echoed = _read_storage_multi(u2, svc, b"/echo_get")
    assert echoed == val, f"echo_get mismatch: expected {val!r}, got {echoed!r}"

    # ack under exact package-hash
    ack = u2.service_accounts[svc].storage.get(_typed_pkg_key(pkg_hash))
    assert ack is not None, "ack under pkg-hash missing"
    assert _to_bytes(ack) == b"OK"

    # actual KV
    stored = _read_storage_multi(u2, svc, key)
    assert stored == val, f"stored value mismatch: expected {val!r}, got {stored!r}"
