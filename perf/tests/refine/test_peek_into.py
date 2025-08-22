from pathlib import Path
import struct
import pytest

from jam.state.ghost import GhostState
from jam.state.state import setup_state
from jam.settings import setup_setting
from jam.utils.dummy.dummy_package import create_dummy_package

from jam.types.protocol.core import Balance, BlobLength, Gas, ServiceId
from jam.types.protocol.crypto import Hash
from jam.types.state.delta import AccountMetadata, Ai, Ao, LookupTable, Timestamps
from jam.types.work.item import WorkItem, ImportSpecs, ExtrinsicSpecs
from tsrkit_types.bytes import Bytes as TBytes
from tsrkit_types.enum import Uint
from jam.execution.host_calls.invocations.refine import PsiR


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
        gas_limit=Gas(50_000),
        min_gas=Gas(1_000),
        num_i=Ai(0),
        num_o=Ao(0),
    )
    # also seed preimage+lookup so the service can be fetched historically if needed
    state.delta[sid].preimages[ch] = TBytes(code)
    state.delta[sid].lookup[LookupTable(hash=ch, length=BlobLength(len(code)))] = Timestamps([state.tau])
    return ch


def _isegs_for(pkg):
    return [[] for _ in range(len(pkg.items))]


def _decode_bytes_result(work_output_bytes: bytes) -> bytes:
    """If the result is [u16_be_len][payload], strip it, else return as-is."""
    if len(work_output_bytes) >= 2:
        n = int.from_bytes(work_output_bytes[:2], "big")
        if n == len(work_output_bytes) - 2:
            return work_output_bytes[2:]
    return work_output_bytes


def _make_create_and_peek_payload(pc0: int, code_bytes: bytes, inner_src: int, buf_len: int) -> bytes:
    # layout: [pc0 u64][code_len u32][code][inner_src u64][buf_len u64]
    return (
        struct.pack("<Q", pc0) +
        struct.pack("<I", len(code_bytes)) +
        code_bytes +
        struct.pack("<QQ", inner_src, buf_len)
    )


def test_peek_into_zero_memory_onecall(db_path):
    # --- state & service ---
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
    state = setup_state(settings.state_db, GhostState.genesis())

    peek_into_code = _artifact("peek_into").read_bytes()    # the service under test
    zero_prog      = _artifact("zero").read_bytes()         # a valid .jam program (contents don't matter)
    svc_peek_into  = ServiceId(12)

    ch_peek = _register(state, svc_peek_into, peek_into_code)

    # Create a VM and immediately peek 16 bytes at address 0 — should be zero-initialized
    payload = _make_create_and_peek_payload(
        pc0=0,
        code_bytes=zero_prog,
        inner_src=0,
        buf_len=16,
    )

    pkg = create_dummy_package()
    wi  = WorkItem(
        service=svc_peek_into,
        code_hash=ch_peek,
        payload=TBytes(payload),
        refine_gas_limit=Gas(30_000),
        accumulate_gas_limit=Gas(30_000),
        import_segments=ImportSpecs([]),
        extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    pkg.items.append(wi)

    r, e, u = PsiR(0, p=pkg, auth_trace=b"", i_segments=_isegs_for(pkg), e_offset=0).execute()
    assert r.get_key() == "ok"
    out = _decode_bytes_result(r.encode())
    assert out == b"\x00" * 16


def test_peek_into_small_lengths_onecall(db_path):
    # --- state & service ---
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
    state = setup_state(settings.state_db, GhostState.genesis())

    peek_into_code = _artifact("peek_into").read_bytes()
    zero_prog      = _artifact("zero").read_bytes()
    svc_peek_into  = ServiceId(22)

    ch_peek = _register(state, svc_peek_into, peek_into_code)

    # Case A: buf_len = 0 → empty result
    payload0 = _make_create_and_peek_payload(
        pc0=0,
        code_bytes=zero_prog,
        inner_src=0,
        buf_len=0,
    )
    pkg = create_dummy_package()
    pkg.items.append(
        WorkItem(
            service=svc_peek_into,
            code_hash=ch_peek,
            payload=TBytes(payload0),
            refine_gas_limit=Gas(30_000),
            accumulate_gas_limit=Gas(30_000),
            import_segments=ImportSpecs([]),
            extrinsic=ExtrinsicSpecs([]),
            export_count=Uint[16](0),
        )
    )
    r0, e0, u0 = PsiR(0, p=pkg, auth_trace=b"", i_segments=_isegs_for(pkg), e_offset=0).execute()
    assert r0.get_key() == "ok"
    assert _decode_bytes_result(r0.encode()) == b""

    # Case B: buf_len = 5 at inner_src = 0 → five zeros
    payload5 = _make_create_and_peek_payload(
        pc0=0,
        code_bytes=zero_prog,
        inner_src=0,
        buf_len=5,
    )
    pkg2 = create_dummy_package()
    pkg2.items.append(
        WorkItem(
            service=svc_peek_into,
            code_hash=ch_peek,
            payload=TBytes(payload5),
            refine_gas_limit=Gas(30_000),
            accumulate_gas_limit=Gas(30_000),
            import_segments=ImportSpecs([]),
            extrinsic=ExtrinsicSpecs([]),
            export_count=Uint[16](0),
        )
    )
    r5, e5, u5 = PsiR(0, p=pkg2, auth_trace=b"", i_segments=_isegs_for(pkg2), e_offset=0).execute()
    assert r5.get_key() == "ok"
    assert _decode_bytes_result(r5.encode()) == b"\x00" * 5


    # Case C: peek near the end of the first page (VM typically starts with 1 x 4KiB page)
    # Keep the whole read in-bounds so peek_into succeeds.
    inner_src = 4096 - 7  # last 7 bytes of page 0
    payload_far = _make_create_and_peek_payload(
        pc0=0,
        code_bytes=zero_prog,
        inner_src=inner_src,
        buf_len=7,
    )
    pkg3 = create_dummy_package()
    pkg3.items.append(
        WorkItem(
            service=svc_peek_into,
            code_hash=ch_peek,
            payload=TBytes(payload_far),
            refine_gas_limit=Gas(30_000),
            accumulate_gas_limit=Gas(30_000),
            import_segments=ImportSpecs([]),
            extrinsic=ExtrinsicSpecs([]),
            export_count=Uint[16](0),
        )
    )
    r_far, e_far, u_far = PsiR(0, p=pkg3, auth_trace=b"", i_segments=_isegs_for(pkg3), e_offset=0).execute()
    assert r_far.get_key() == "ok"
    assert _decode_bytes_result(r_far.encode()) == b"\x00" * 7
