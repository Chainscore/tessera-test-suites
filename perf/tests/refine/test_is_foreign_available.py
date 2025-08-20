# perf/tests/refine/test_is_foreign_available.py

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

def _register(state, sid: ServiceId, code: bytes):
    ch = Hash.blake2b(code)
    state.delta[sid].service = AccountMetadata(
        code_hash=ch, balance=Balance(1_000_000),
        gas_limit=Gas(50_000), min_gas=Gas(1_000),
        num_i=Ai(0), num_o=Ao(0),
    )
    state.delta[sid].preimages[ch] = TBytes(code)
    state.delta[sid].lookup[LookupTable(hash=ch, length=BlobLength(len(code)))] = Timestamps([state.tau])
    # ensure account.id is the typed ServiceId (needed by historical_lookup path)
    try:
        state.delta[sid].id = sid
    except Exception:
        pass
    return ch

def _isegs_for(pkg):
    return [[] for _ in range(len(pkg.items))]

def test_is_foreign_available_ok(db_path):
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
    state = setup_state(settings.state_db, GhostState.genesis())

    reader_code  = _artifact("is_foreign_available").read_bytes()
    foreign_code = _artifact("hello").read_bytes()

    svc_reader  = ServiceId(31)
    svc_foreign = ServiceId(32)

    ch_reader   = _register(state, svc_reader, reader_code)
    _           = _register(state, svc_foreign, foreign_code)

    # seed preimage in foreign account
    blob      = foreign_code
    blob_hash = Hash.blake2b(blob)
    state.delta[svc_foreign].preimages[blob_hash] = TBytes(blob)
    state.delta[svc_foreign].lookup[
        LookupTable(hash=blob_hash, length=BlobLength(len(blob)))
    ] = Timestamps([state.tau])

    payload = struct.pack("<Q", int(svc_foreign)) + bytes(blob_hash)

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

    # IMPORTANT: get the payload (WorkOutput) bytes, not the choice encoding
    out = r.unwrap()
    assert len(out) >= 8
    (flag,) = struct.unpack("<Q", out[:8])
    assert flag == 1

# def test_is_foreign_available_false(db_path):
#     settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
#     state = setup_state(settings.state_db, GhostState.genesis())

#     reader_code  = _artifact("is_foreign_available").read_bytes()
#     foreign_code = _artifact("hello").read_bytes()

#     svc_reader  = ServiceId(41)
#     svc_foreign = ServiceId(42)

#     ch_reader   = _register(state, svc_reader, reader_code)
#     _           = _register(state, svc_foreign, foreign_code)

#     # hash that doesn't exist in foreign preimages
#     fake_hash = Hash.blake2b(b"definitely-missing")

#     payload = struct.pack("<Q", int(svc_foreign)) + bytes(fake_hash)

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

#     out = r.unwrap()
#     assert len(out) >= 8
#     (flag,) = struct.unpack("<Q", out[:8])
#     assert flag == 0
