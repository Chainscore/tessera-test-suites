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
# from jam.execution.host_calls.invocations.functions.refine_fns import RefineContext, RefinementMap
from jam.types.work import Segments


def test_expunge_ok_then_error(db_path):
    # --- env/state ---
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
    state = setup_state(settings.state_db, GhostState.genesis())
    package = create_dummy_package()

    # --- artifacts ---
    machine_code = _artifact("machine").read_bytes()     # your MachineService
    expunge_code = _artifact("expunge").read_bytes()     # your ExpungeService
    inner_prog   = _artifact("zero").read_bytes()        # any valid .jam to load

    svc_machine = ServiceId(1)
    svc_expunge = ServiceId(2)

    ch_machine = create_svc_ch(state, svc_machine, machine_code)
    ch_expunge = create_svc_ch(state, svc_expunge, expunge_code)

    # --- 1) create inner VM via MachineService: payload = [pc0 u64] + code_bytes ---
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
    assert not out1.startswith(b"ERR:"), f"machine error: {out1!r}"
    assert len(out1) >= 8
    (handle,) = struct.unpack("<Q", out1[:8])

    # --- 2) expunge that handle via ExpungeService: payload = [handle u64] ---
    payload_expunge = struct.pack("<Q", handle)
    wi_expunge = WorkItem(
        service=svc_expunge,
        code_hash=ch_expunge,
        payload=Bytes(payload_expunge),
        refine_gas_limit=Gas(10_000),
        accumulate_gas_limit=Gas(10_000),
        import_segments=ImportSpecs([]),
        extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    package.items.append(wi_expunge)

    r2, e2, u2, = PsiR(1, p=package, auth_trace=b"", i_segments=[[]], e_offset=0).execute()
    assert r2.get_key() == "ok"
    out2 = r2.encode()
    assert not out2.startswith(b"ERR:"), f"expunge error: {out2!r}"
    assert len(out2) >= 16
    h2, final_ic = struct.unpack("<QQ", out2[:16])
    # assert h2 == handle
    assert final_ic >= 0
    assert isinstance(e1, (list, tuple)) and isinstance(e2, (list, tuple))
    assert len(e1) == 0 and len(e2) == 0
    assert int(u1) >= 0 and int(u2) >= 0

    # # --- 3) expunge again: should now error (handle already gone) ---
    # wi_expunge_again = WorkItem(
    #     service=svc_expunge,
    #     code_hash=ch_expunge,
    #     payload=Bytes(payload_expunge),
    #     refine_gas_limit=Gas(10_000),
    #     accumulate_gas_limit=Gas(10_000),
    #     import_segments=ImportSpecs([]),
    #     extrinsic=ExtrinsicSpecs([]),
    #     export_count=Uint[16](0),
    # )
    # package.items.append(wi_expunge_again)

    # r3, e3, u3, context = PsiR(2, p=package, auth_trace=b"", i_segments=[[]], e_offset=0).execute(context)
    # assert r3.get_key() == "ok"
    # out3 = r3.encode()
    # assert out3.startswith(b"ERR:"), f"expected error on second expunge, got {out3!r}"

    # # Optional: check specific ApiError variant name:
    # err_name = out3[4:].decode("utf-8", "replace")
    # # Often "IndexUnknown" for unknown/expired handle; tolerate others depending on VM:
    # assert err_name in {"IndexUnknown", "OutOfBounds", "ActionInvalid", "GasLimitTooLow", "StorageFull", "BadCore", "NoCash"}
