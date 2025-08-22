from pathlib import Path
import struct
import pytest

from jam.execution.host_calls.invocations.refine import PsiR
from jam.execution.host_calls.invocations.accumulate import PsiA

from jam.settings import setup_setting
from jam.state.ghost import GhostState
from jam.state.state import setup_state

from jam.types.protocol.core import Balance, Gas, ServiceId, BlobLength, ExportsRoot
from jam.types.protocol.crypto import Hash, OpaqueHash
from jam.types.state.delta import AccountMetadata, Ai, Ao, LookupTable, Timestamps
from jam.types.state.accumulation.types import StateContext, OperandTuple, OperandTuples
from jam.types.work.item import WorkItem, ImportSpecs, ExtrinsicSpecs

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
    state.delta[sid].service = AccountMetadata(
        code_hash=ch,
        balance=Balance(1_000_000),
        gas_limit=Gas(50_000),
        min_gas=Gas(1_000),
        num_i=Ai(0),
        num_o=Ao(0),
    )
    state.delta[sid].preimages[ch] = TBytes(code)
    # one lookup entry is enough for loader; real length doesn’t matter in this test
    state.delta[sid].lookup[LookupTable(hash=ch, length=BlobLength(len(code)))] = Timestamps([state.tau])
    return ch


def _isegs_for(pkg):
    # one empty segment-list per item
    return [[] for _ in range(len(pkg.items))]


def _pkg_hash(pkg):
    return Hash.blake2b(pkg.encode())


def _ops(pkg_hash, r1, item_gas: int = 10) -> OperandTuples:
    zero32 = bytes(32)
    return OperandTuples([
        OperandTuple(
            h=pkg_hash,                # WorkPackageHash (opaque hash is acceptable here)
            e=ExportsRoot(zero32),
            a=OpaqueHash(zero32),
            y=OpaqueHash(zero32),
            g=Uint(item_gas),          # must be non-zero or VM may drop the item
            d=r1,                      # refine output result
            o=RawBytes(b""),
        )
    ])


def _read_hashed(u_state: StateContext, sid: ServiceId, raw_key: bytes) -> bytes | None:
    """
    Storage keys are addressed by blake2b(raw_key).
    Read back from the StateContext returned by PsiA.
    """
    acc = u_state.service_accounts[sid]
    k32 = TBytes[32](bytes(Hash.blake2b(raw_key)))
    try:
        v = acc.storage[k32]
    except KeyError:
        return None
    # unwrap if TBytes-like
    return v.to_bytes() if hasattr(v, "to_bytes") else bytes(v)


# ---------- test ----------

def test_kv_set_happy_path(tmp_path):
    # --- state setup ---
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, str(tmp_path))
    state = setup_state(settings.state_db, GhostState.genesis())

    sid = ServiceId(202)
    code = _artifact("set_storage").read_bytes()
    ch = _register(state, sid, code)

    # --- package payload (matches service: u16,u16,key,val) ---
    from jam.utils.dummy.dummy_package import create_dummy_package
    pkg = create_dummy_package()

    key = b"user:1:name"
    val = b"Alice"
    payload = struct.pack("<HH", len(key), len(val)) + key + val

    wi = WorkItem(
        service=sid,
        code_hash=ch,
        payload=TBytes(payload),
        refine_gas_limit=Gas(50_000),
        accumulate_gas_limit=Gas(50_000),
        import_segments=ImportSpecs([]),
        extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    pkg.items.append(wi)

    # --- refine (pass-through) ---
    r1, _e1, _u1 = PsiR(0, p=pkg, auth_trace=b"", i_segments=_isegs_for(pkg), e_offset=0).execute()
    assert r1.get_key() == "ok"

    # --- accumulate (non-zero per-item gas) ---
    ops = _ops(_pkg_hash(pkg), r1, item_gas=10)
    partial = StateContext(
        service_accounts=state.delta,
        validator_keys=state.iota,
        authorizer_keys=state.phi,
        privileges=state.chi,
    )
    u_after, _transfers, commit, _gas_left, _preimages = PsiA(partial, state.tau, sid, Gas(50_000), o=ops).execute()

    # prove accumulate ran
    assert commit.unwrap() != OpaqueHash(bytes(32)), "no commitment returned"

    # read back sentinel and the actual KV
    assert _read_hashed(u_after, sid, b"/echo_set") == b"OK"
    assert _read_hashed(u_after, sid, key) == val
