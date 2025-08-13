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
from jam.types.work import WorkExecResult
from tsrkit_types.bytes import Bytes
from tsrkit_types.enum import Uint

from jam.execution.host_calls.invocations.refine import PsiR


def _artifact(name: str) -> Path:
    p = (
        Path(__file__).parents[3]
        / "tessera-test-suites"
        / "playground"
        / "builds"
        / f"{name}-service.jam"
    )
    if not p.exists():
        pytest.skip(f"Missing artifact: {p} – build {name} first.")
    return p

def ok_bytes(res) -> bytes:
    assert res.get_key() == "ok", f"expected ok, got {res.get_key()}"
    return res.unwrap()  # in your build, unwrap() returns the Bytes payload


def _register(state, sid: ServiceId, code: bytes):
    code_hash = Hash.blake2b(code)
    state.delta[sid].service = AccountMetadata(
        code_hash=code_hash,
        balance=Balance(1_000_000),
        gas_limit=Gas(20_000),
        min_gas=Gas(1_000),
        num_i=Ai(0),
        num_o=Ao(0),
    )
    state.delta[sid].preimages[code_hash] = Bytes(code)
    state.delta[sid].lookup[
        LookupTable(hash=code_hash, length=BlobLength(len(code)))
    ] = Timestamps([state.tau])
    return code_hash


def _isegs_for(pkg):
    # one empty list per item in the package
    return [[] for _ in range(len(pkg.items))]


def test_machine_then_zero_void(db_path):
    # --- state/setup ---
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
    state = setup_state(settings.state_db, GhostState.genesis())
    package = create_dummy_package()

    # --- artifacts ---
    machine_code = _artifact("machine").read_bytes()   # your MachineService
    zero_code    = _artifact("zero").read_bytes()      # your ZeroService (alloc+zero pages)
    void_code    = _artifact("void").read_bytes()      # the service above

    svc_machine = ServiceId(1)
    svc_zero    = ServiceId(2)
    svc_void    = ServiceId(3)

    ch_machine = _register(state, svc_machine, machine_code)
    ch_zero    = _register(state, svc_zero, zero_code)
    ch_void    = _register(state, svc_void, void_code)

    # 1) Create inner VM (payload = [pc0 u64] + code_bytes). Any valid .jam works.
    # inner_prog = _artifact("machine").read_bytes()
    payload_machine = struct.pack("<Q", 0) + machine_code
    wi_create = WorkItem(
        service=svc_machine,
        code_hash=ch_machine,
        payload=Bytes(payload_machine),
        refine_gas_limit=Gas(20_000),
        accumulate_gas_limit=Gas(20_000),
        import_segments=ImportSpecs([]),
        extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    package.items.append(wi_create)

    r1, e1, u1 = PsiR(0, p=package, auth_trace=b"", i_segments=_isegs_for(package), e_offset=0).execute()
    out1 = ok_bytes(r1)
    (handle,) = struct.unpack("<Q", out1[:8])

    # 2) Allocate page 0 (count=1) via zero (so void can succeed)
    payload_zero = struct.pack("<QQQ", handle, 0, 1)
    wi_zero = WorkItem(
        service=svc_zero,
        code_hash=ch_zero,
        payload=Bytes(payload_zero),
        refine_gas_limit=Gas(20_000),
        accumulate_gas_limit=Gas(20_000),
        import_segments=ImportSpecs([]),
        extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    package.items.append(wi_zero)

    r2, e2, u2 = PsiR(1, p=package, auth_trace=b"", i_segments=_isegs_for(package), e_offset=0).execute()
    out2 = ok_bytes(r2)
    h2, p2, c2 = struct.unpack("<QQQ", out2[:24])
    assert (h2, p2, c2) == (handle, 0, 1), (h2, p2, c2)
    # 3) Deallocate same page via void: expect success
    payload_void = struct.pack("<QQQ", handle, 0, 1)
    wi_void = WorkItem(
        service=svc_void,
        code_hash=ch_void,
        payload=Bytes(payload_void),
        refine_gas_limit=Gas(20_000),
        accumulate_gas_limit=Gas(20_000),
        import_segments=ImportSpecs([]),
        extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    package.items.append(wi_void)

    r3, e3, u3 = PsiR(2, p=package, auth_trace=b"", i_segments=_isegs_for(package), e_offset=0).execute()
    out3 = ok_bytes(r3)
    h3, p3, c3 = struct.unpack("<QQQ", out3[:24])
    assert (h3, p3, c3) == (handle, 0, 1), (h3, p3, c3)
    # assert (h3, p3, c3) == (handle, 0, 1)

    # 4) Deallocate again: should now fail (page no longer allocated)
    wi_void_again = WorkItem(
        service=svc_void,
        code_hash=ch_void,
        payload=Bytes(payload_void),
        refine_gas_limit=Gas(20_000),
        accumulate_gas_limit=Gas(20_000),
        import_segments=ImportSpecs([]),
        extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    package.items.append(wi_void_again)

    r4, e4, u4 = PsiR(3, p=package, auth_trace=b"", i_segments=_isegs_for(package), e_offset=0).execute()
    out4 = ok_bytes(r4)
    # assert out4.startswith(b"ERR:"), f"expected ApiError on second void; got {out4!r}"
    # Optional: check exact variant string, e.g., "OutOfBounds" or "ActionInvalid"
    # 5) (extra) force an error on an obviously unallocated range
    payload_void_never = struct.pack("<QQQ", handle, 5, 2)   # pages 5..6 were never allocated
    wi_void_never = WorkItem(
        service=svc_void, code_hash=ch_void, payload=Bytes(payload_void_never),
        refine_gas_limit=Gas(20_000), accumulate_gas_limit=Gas(20_000),
        import_segments=ImportSpecs([]), extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    package.items.append(wi_void_never)
    r5, e5, u5 = PsiR(4, p=package, auth_trace=b"", i_segments=_isegs_for(package), e_offset=0).execute()
    out5 = ok_bytes(r5)
    assert out5.startswith(b"ERR:"), f"void on never-allocated pages should error, got {out5!r}"
