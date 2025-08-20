import struct
from pathlib import Path

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

def _register(state, svc_id, code_bytes):
    code_hash = Hash.blake2b(code_bytes)
    state.delta[svc_id].service = AccountMetadata(
        code_hash=code_hash, balance=Balance(1_000_000),
        gas_limit=Gas(10_000), min_gas=Gas(1_000), num_i=Ai(0), num_o=Ao(0)
    )
    state.delta[svc_id].preimages[code_hash] = Bytes(code_bytes)
    state.delta[svc_id].lookup[LookupTable(hash=code_hash, length=BlobLength(len(code_bytes)))] = Timestamps([state.tau])
    return code_hash

def test_machine_refine_then_zero(db_path: str):
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
    state = setup_state(settings.state_db, GhostState.genesis())
    pkg = create_dummy_package()

    builds = Path(__file__).parents[4] / "tessera-test-suites" / "playground" / "builds"
    machine_code = (builds / "machine-service.jam").read_bytes()  # your MachineService
    zero_prog    = (builds / "zero-service.jam").read_bytes()     # program to load into inner VM
    zero_code    = (builds / "zero-service.jam").read_bytes()     # your ZeroService (if separate name, adjust)

    svc_machine = ServiceId(1)
    svc_zero    = ServiceId(2)

    ch_machine = _register(state, svc_machine, machine_code)
    ch_zero    = _register(state, svc_zero, zero_code)

    # 1) Create inner VM from zero_prog with pc0=0
    payload_machine = struct.pack("<Q", 0) + zero_prog
    wi1 = WorkItem(
            service=svc_machine,
            code_hash=ch_machine,
            payload=Bytes(payload_machine),
            refine_gas_limit=Gas(1_000),
            accumulate_gas_limit=Gas(1_000),
            import_segments=ImportSpecs([]),
            extrinsic=ExtrinsicSpecs([]),
            export_count=Uint[16](1)
    )
    pkg.items.append(wi1)
    r1, e1, u1 = PsiR(0, p=pkg, auth_trace=b"", i_segments=[[]], e_offset=0).execute()

    out1 = r1.encode()
    assert not out1.startswith(b"ERR:"), f"machine error: {out1!r}"
    (handle,) = struct.unpack("<Q", out1[:8])
    # print("inner handle:", handle)

    # 2) Zero 1 page at page 0 on that inner VM
    payload_zero = struct.pack("<QQQ", handle, 0, 1)  # vm_handle, page, count
    wi2 = WorkItem(
            service=svc_zero,
            code_hash=ch_zero,
            payload=Bytes(payload_zero),
            refine_gas_limit=Gas(1_000),
            accumulate_gas_limit=Gas(1_000),
            import_segments=ImportSpecs([]),
            extrinsic=ExtrinsicSpecs([]),
            export_count=Uint[16](1)
    )
    pkg.items.append(wi2)
    r2, e2, u2 = PsiR(1, p=pkg, auth_trace=b"", i_segments=[[]], e_offset=0).execute()
    out2 = r2.encode()
    if out2.startswith(b"ERR:"):
        print("zero error:", out2[4:].decode())
    else:
        h, page, count = struct.unpack("<QQQ", out2[:24])
        print(f"zero result: handle={h}, page={page}, count={count}")
    return handle
