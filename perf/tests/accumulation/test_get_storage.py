
from jam.state.state import setup_state
from jam.settings import setup_setting
from jam.utils.dummy.dummy_package import create_dummy_package

from jam.types.protocol.core import Balance, BlobLength, Gas, ServiceId
from jam.types.protocol.crypto import Hash   # <-- Python hashing helper
from jam.types.state.delta import AccountMetadata, Ai, Ao, LookupTable, Timestamps
from jam.types.work.item import WorkItem, ImportSpecs, ExtrinsicSpecs
from tsrkit_types.bytes import Bytes
from tsrkit_types.enum import Uint

from jam.execution.host_calls.invocations.refine import PsiR


def _artifact(name: str) -> Path:


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
    state.delta[sid].preimages[ch] = Bytes(code)
    state.delta[sid].lookup[LookupTable(hash=ch, length=BlobLength(len(code)))] = Timestamps([state.tau])
    return ch


def _opt_decode(out: bytes):
    # 0x00 => None
    if not out:
        return None
    if out[0] == 0:
        return None
    if out[0] != 1 or len(out) < 9:
        return "ERR:bad-option"
    ln = int.from_bytes(out[1:9], "little")
    if len(out) < 9 + ln:
        return "ERR:short"
    return out[9:9+ln]


def test_get_storage_found_and_missing(db_path):
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
    state = setup_state(settings.state_db, GhostState.genesis())
    package = create_dummy_package()

    code = _artifact("get_storage").read_bytes()
    svc  = ServiceId(1)
    ch   = _register(state, svc, code)

    # Prepare a key/value in this service's storage
    raw_key = b"my-app-key"
    key32   = Bytes(Hash.blake2b(raw_key))   # <-- 32-byte key for the service
    value   = b"hello-from-storage"

    state.delta[svc].storage[key32] = Bytes(value)

    # 1) Found case: payload is exactly the 32-byte key
    wi1 = WorkItem(
        service=svc,
        code_hash=ch,
        payload=Bytes(key32),                   # payload: 32-byte key
        refine_gas_limit=Gas(20_000),
        accumulate_gas_limit=Gas(20_000),
        import_segments=ImportSpecs([]),
        extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    package.items.append(wi1)

    r1, e1, u1 = PsiR(0, p=package, auth_trace=b"", i_segments=[[]], e_offset=0).execute()
    assert r1.get_key() == "ok"
    out1 = r1.unwrap()                          # raw bytes from refine
    assert _opt_decode(out1) == value
    assert len(e1) == 0
    assert int(u1) >= 0

    # 2) Missing case: different key, not present
    missing_key32 = bytes(Hash.blake2b(b"missing-key"))
    wi2 = WorkItem(
        service=svc,
        code_hash=ch,
        payload=Bytes(missing_key32),
        refine_gas_limit=Gas(20_000),
        accumulate_gas_limit=Gas(20_000),
        import_segments=ImportSpecs([]),
        extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    package.items.append(wi2)

    r2, e2, u2 = PsiR(1, p=package, auth_trace=b"", i_segments=[[]], e_offset=0).execute()
    assert r2.get_key() == "ok"
    out2 = r2.unwrap()
    assert _opt_decode(out2) is None
    assert len(e2) == 0
    assert int(u2) >= 0
