from pathlib import Path

from jam.state.state import setup_state
from jam.settings import setup_setting
from jam.utils.dummy.dummy_package import create_dummy_package

from jam.types.protocol.core import Balance, BlobLength, Gas, ServiceId
from jam.types.protocol.crypto import Hash
from jam.types.state.delta import AccountMetadata, Ai, Ao, LookupTable, Timestamps
from jam.types.work.item import WorkItem, ImportSpecs, ExtrinsicSpecs
from tsrkit_types.bytes import Bytes
from tsrkit_types.enum import Uint
from perf.tests.utils.helper import _artifact,create_svc_ch
from jam.execution.host_calls.invocations.refine import PsiR

def test_machine_handle(db_path):
    # --- env/state ---
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
    state = setup_state(settings.state_db, GhostState.genesis())
    package = create_dummy_package()

    # --- artifacts ---
    machine_code = _artifact("machine").read_bytes()
    inner_prog   = _artifact("zero").read_bytes()

    svc_machine = ServiceId(1)
    ch_machine = create_svc_ch(state, svc_machine, machine_code)

    # --- create inner VM ---
    payload_machine = struct.pack("<Q", 0) + inner_prog
    wi_create = WorkItem(
        service=svc_machine,
        code_hash=ch_machine,
        payload=Bytes(payload_machine),
        refine_gas_limit=Gas(10_000),
        accumulate_gas_limit=Gas(10_000),
        import_segments=ImportSpecs([]),
        extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    package.items.append(wi_create)

    r1, e1, u1, = PsiR(0, p=package, auth_trace=b"", i_segments=[[]], e_offset=0).execute()
    assert r1.get_key()=='ok'
    out1 = r1.encode()
    (handle,) = struct.unpack("<Q", out1[:8])
    print(f"GEMINI_DEBUG: handle from machine call = {handle}")
    assert handle == 1
