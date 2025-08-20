
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
from perf.tests.utils.helper import create_svc_ch  # <-- use this helper


def _artifact(name: str) -> Path:


def _isegs_for(pkg):
    return [[] for _ in range(len(pkg.items))]


def test_foreign_lookup_ok(db_path):
    # --- setup ---
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
    state = setup_state(settings.state_db, GhostState.genesis())

    # reader (the service under test) and foreign (the source of preimage)
    reader_code  = _artifact("foreign_lookup").read_bytes()
    foreign_code = _artifact("hello").read_bytes()  # any valid .jam blob

    svc_reader  = ServiceId(31)
    svc_foreign = ServiceId(32)

    ch_reader   = create_svc_ch(state, svc_reader, reader_code)
    _           = create_svc_ch(state, svc_foreign, foreign_code)

    # Seed a preimage in the foreign account
    blob      = foreign_code
    blob_hash = Hash.blake2b(blob)
    state.delta[svc_foreign].preimages[blob_hash] = TBytes(blob)
    state.delta[svc_foreign].lookup[LookupTable(hash=blob_hash, length=BlobLength(len(blob)))] = Timestamps([state.tau])

    # Ask reader to fetch first 16 bytes of that preimage
    from_off, req_len = 0, 16
    payload = struct.pack("<QQQ", int(svc_foreign), from_off, req_len) + bytes(blob_hash)

    pkg = create_dummy_package()
    wi = WorkItem(
        service=svc_reader, code_hash=ch_reader, payload=TBytes(payload),
        refine_gas_limit=Gas(50_000), accumulate_gas_limit=Gas(50_000),
        import_segments=ImportSpecs([]), extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    pkg.items.append(wi)

    r, e, u = PsiR(0, p=pkg, auth_trace=b"", i_segments=_isegs_for(pkg), e_offset=0).execute()
    assert r.get_key() == "ok"
    out = r.encode()
    assert not out.startswith(b"ERR:"), out
    expected = blob[from_off:from_off+req_len]
    assert out == struct.pack(">H", len(expected)) + expected


# def test_foreign_lookup_not_found(db_path):
#     settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
#     state = setup_state(settings.state_db, GhostState.genesis())

#     reader_code = _artifact("foreign_lookup").read_bytes()
#     svc_reader  = ServiceId(41)
#     ch_reader   = create_svc_ch(state, svc_reader, reader_code)

#     svc_foreign = ServiceId(42)
#     _           = create_svc_ch(state, svc_foreign, _artifact("hello").read_bytes())

#     # hash that doesn't exist in foreign preimages
#     fake_hash = Hash.blake2b(b"nope")
#     payload = struct.pack("<QQQ", int(svc_foreign), 0, 8) + bytes(fake_hash)

#     pkg = create_dummy_package()
#     wi = WorkItem(
#         service=svc_reader, code_hash=ch_reader, payload=TBytes(payload),
#         refine_gas_limit=Gas(50_000), accumulate_gas_limit=Gas(50_000),
#         import_segments=ImportSpecs([]), extrinsic=ExtrinsicSpecs([]),
#         export_count=Uint[16](0),
#     )
#     pkg.items.append(wi)

#     r, e, u = PsiR(0, p=pkg, auth_trace=b"", i_segments=_isegs_for(pkg), e_offset=0).execute()
#     assert r.get_key() == "ok"
#     out = r.encode()
#     assert out.startswith(b"ERR:NotFound"), out
