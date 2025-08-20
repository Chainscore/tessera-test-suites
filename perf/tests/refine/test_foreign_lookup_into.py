# perf/tests/refine/test_foreign_lookup_into.py

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
    p = (
        Path(__file__).parents[4]
        / "tessera-test-suites"
        / "playground"
        / "builds"
        / f"{name}-service.jam"


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
    state.delta[sid].lookup[LookupTable(hash=ch, length=BlobLength(len(code)))] = Timestamps([state.tau])
    return ch


def _isegs_for(pkg):
    return [[] for _ in range(len(pkg.items))]


def _fix_account_ids(state, *sids):
    # Ensure account ids are typed (not plain ints) so historical_lookup keying works.
    for sid in sids:
        state.delta[sid].id = ServiceId(int(sid))


def test_foreign_lookup_into_ok(db_path):
    # --- state/setup ---
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
    state = setup_state(settings.state_db, GhostState.genesis())

    # --- artifacts ---
    reader_code  = _artifact("foreign_lookup_into").read_bytes()
    foreign_code = _artifact("hello").read_bytes()  # any small .jam blob

    svc_reader  = ServiceId(31)
    svc_foreign = ServiceId(32)

    ch_reader   = _register(state, svc_reader, reader_code)
    _           = _register(state, svc_foreign, foreign_code)

    # historical_lookup expects typed ServiceId ids in accounts
    _fix_account_ids(state, svc_reader, svc_foreign)

    # Seed preimage in foreign account
    blob      = foreign_code
    blob_hash = Hash.blake2b(blob)
    state.delta[svc_foreign].preimages[blob_hash] = TBytes(blob)
    state.delta[svc_foreign].lookup[LookupTable(hash=blob_hash, length=BlobLength(len(blob)))] = Timestamps([state.tau])

    # payload: [sid:u64][buf_len:u64][hash:32]
    buf_len = 16
    payload = struct.pack("<QQ", int(svc_foreign), buf_len) + bytes(blob_hash)

    pkg = create_dummy_package()
    wi = WorkItem(
        service=svc_reader,
        code_hash=ch_reader,
        payload=TBytes(payload),
        refine_gas_limit=Gas(50_000),
        accumulate_gas_limit=Gas(50_000),
        import_segments=ImportSpecs([]),
        extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    pkg.items.append(wi)

    r, e, u = PsiR(0, p=pkg, auth_trace=b"", i_segments=_isegs_for(pkg), e_offset=0).execute()
    assert r.get_key() == "ok"
    out = r.encode()

    # Should be [written:u64] + first 'written' bytes
    assert len(out) >= 8
    written = int.from_bytes(out[:8], "little")
    assert written == buf_len
    assert out[8:8+written] == blob[:buf_len]


# def test_foreign_lookup_into_not_found(db_path):
#     settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
#     state = setup_state(settings.state_db, GhostState.genesis())

#     reader_code = _artifact("foreign_lookup_into").read_bytes()
#     svc_reader  = ServiceId(41)
#     ch_reader   = _register(state, svc_reader, reader_code)

#     # still need typed id for the lookup host call (even if it won't find anything)
#     _fix_account_ids(state, svc_reader)

#     # fake hash (not in any foreign account)
#     fake_hash = Hash.blake2b(b"nope")
#     # target "foreign" sid can be anything; just keep consistent types
#     target_sid = ServiceId(42)
#     _fix_account_ids(state, target_sid)  # ensure typed id is set for this slot too

#     buf_len = 8
#     payload = struct.pack("<QQ", int(target_sid), buf_len) + bytes(fake_hash)

#     pkg = create_dummy_package()
#     wi = WorkItem(
#         service=svc_reader,
#         code_hash=ch_reader,
#         payload=TBytes(payload),
#         refine_gas_limit=Gas(50_000),
#         accumulate_gas_limit=Gas(50_000),
#         import_segments=ImportSpecs([]),
#         extrinsic=ExtrinsicSpecs([]),
#         export_count=Uint[16](0),
#     )
#     pkg.items.append(wi)

#     r, e, u = PsiR(0, p=pkg, auth_trace=b"", i_segments=_isegs_for(pkg), e_offset=0).execute()
#     assert r.get_key() == "ok"
#     out = r.encode()
#     assert out == b"NONE"
