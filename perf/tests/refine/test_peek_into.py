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
    """
    Some runners wrap results as [u16_be_len][payload]. If so, strip it.
    Otherwise return as-is.
    """
    if len(work_output_bytes) >= 2:
        n = int.from_bytes(work_output_bytes[:2], "big")
        if n == len(work_output_bytes) - 2:
            return work_output_bytes[2:]
    return work_output_bytes


def test_peek_into_zero_memory(db_path):
    # --- state & services ---
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
    state = setup_state(settings.state_db, GhostState.genesis())

    machine_code   = _artifact("machine").read_bytes()      # creates inner VM and returns handle
    peek_into_code = _artifact("peek_into").read_bytes()    # service under test
    inner_prog     = _artifact("zero").read_bytes()         # any valid .jam program

    svc_machine   = ServiceId(11)
    svc_peek_into = ServiceId(12)

    ch_machine    = _register(state, svc_machine, machine_code)
    ch_peek_into  = _register(state, svc_peek_into, peek_into_code)

    # --- 1) create inner VM via MachineService: payload = [pc0 u64] + code_bytes
    payload_create = struct.pack("<Q", 0) + inner_prog
    pkg = create_dummy_package()
    wi_create = WorkItem(
        service=svc_machine,
        code_hash=ch_machine,
        payload=TBytes(payload_create),
        refine_gas_limit=Gas(30_000),
        accumulate_gas_limit=Gas(30_000),
        import_segments=ImportSpecs([]),
        extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    pkg.items.append(wi_create)

    r1, e1, u1 = PsiR(0, p=pkg, auth_trace=b"", i_segments=_isegs_for(pkg), e_offset=0).execute()
    assert r1.get_key() == "ok"
    out1 = _decode_bytes_result(r1.encode())
    assert len(out1) >= 8
    (handle,) = struct.unpack("<Q", out1[:8])

    # --- 2) peek 16 bytes from address 0 (new VM memory is zero-initialized)
    buf_len   = 16
    inner_src = 0
    payload_peek = struct.pack("<QQQ", handle, buf_len, inner_src)

    wi_peek = WorkItem(
        service=svc_peek_into,
        code_hash=ch_peek_into,
        payload=TBytes(payload_peek),
        refine_gas_limit=Gas(30_000),
        accumulate_gas_limit=Gas(30_000),
        import_segments=ImportSpecs([]),
        extrinsic=ExtrinsicSpecs([]),
        export_count=Uint,
    )
    pkg.items.append(wi_peek)

    r2, e2, u2 = PsiR(1, p=pkg, auth_trace=b"", i_segments=_isegs_for(pkg), e_offset=0).execute()
    assert r2.get_key() == "ok"
    out2 = _decode_bytes_result(r2.encode())
    assert out2 == b"\x00" * buf_len


def test_peek_into_small_lengths(db_path):
    # --- state & services ---
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
    state = setup_state(settings.state_db, GhostState.genesis())

    machine_code   = _artifact("machine").read_bytes()
    peek_into_code = _artifact("peek_into").read_bytes()
    inner_prog     = _artifact("zero").read_bytes()

    svc_machine   = ServiceId(21)
    svc_peek_into = ServiceId(22)

    ch_machine    = _register(state, svc_machine, machine_code)
    ch_peek_into  = _register(state, svc_peek_into, peek_into_code)

    # Create the VM
    payload_create = struct.pack("<Q", 0) + inner_prog
    pkg = create_dummy_package()
    pkg.items.append(
        WorkItem(
            service=svc_machine, code_hash=ch_machine, payload=TBytes(payload_create),
            refine_gas_limit=Gas(30_000), accumulate_gas_limit=Gas(30_000),
            import_segments=ImportSpecs([]), extrinsic=ExtrinsicSpecs([]),
            export_count=Uint[16](0),
        )
    )
    r1, e1, u1 = PsiR(0, p=pkg, auth_trace=b"", i_segments=_isegs_for(pkg), e_offset=0).execute()
    assert r1.get_key() == "ok"
    (handle,) = struct.unpack("<Q", _decode_bytes_result(r1.encode())[:8])

    # Peek 0 bytes → empty result
    payload0 = struct.pack("<QQQ", handle, 0, 0)
    pkg.items.append(
        WorkItem(
            service=svc_peek_into, code_hash=ch_peek_into, payload=TBytes(payload0),
            refine_gas_limit=Gas(30_000), accumulate_gas_limit=Gas(30_000),
            import_segments=ImportSpecs([]), extrinsic=ExtrinsicSpecs([]),
            export_count=Uint[16](0),
        )
    )
    r2, e2, u2 = PsiR(1, p=pkg, auth_trace=b"", i_segments=_isegs_for(pkg), e_offset=0).execute()
    assert r2.get_key() == "ok"
    assert _decode_bytes_result(r2.encode()) == b""

    # Peek 5 bytes → five zeros
    payload5 = struct.pack("<QQQ", handle, 5, 0)
    pkg.items.append(
        WorkItem(
            service=svc_peek_into, code_hash=ch_peek_into, payload=TBytes(payload5),
            refine_gas_limit=Gas(30_000), accumulate_gas_limit=Gas(30_000),
            import_segments=ImportSpecs([]), extrinsic=ExtrinsicSpecs([]),
            export_count=Uint[16](0),
        )
    )
    r3, e3, u3 = PsiR(2, p=pkg, auth_trace=b"", i_segments=_isegs_for(pkg), e_offset=0).execute()
    assert r3.get_key() == "ok"
    assert _decode_bytes_result(r3.encode()) == b"\x00" * 5
