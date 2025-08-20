
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

def _decode_bytes_result(work_output_bytes: bytes) -> bytes:
    """
    If the result is [u16_be_len][payload], strip the 2-byte BE length.
    Otherwise, return as-is.
    """
    if len(work_output_bytes) >= 2:
        n = int.from_bytes(work_output_bytes[:2], "big")
        if n == len(work_output_bytes) - 2:
            return work_output_bytes[2:]
    return work_output_bytes


def test_lookup_into_found_and_truncated(db_path):
    # --- setup ---
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
    state = setup_state(settings.state_db, GhostState.genesis())

    code = _artifact("lookup_into").read_bytes()
    svc  = ServiceId(71)
    ch   = _register(state, svc, code)

    # Seed THIS service’s preimage store
    blob = b"hello-preimage-body"
    blob_hash = Hash.blake2b(blob)
    state.delta[svc].preimages[blob_hash] = TBytes(blob)
    state.delta[svc].lookup[LookupTable(hash=blob_hash, length=BlobLength(len(blob)))] = Timestamps([state.tau])

    # === case A: buffer big enough -> full blob back ===
    pkg = create_dummy_package()
    payload = struct.pack("<Q", len(blob) + 10) + bytes(blob_hash)  # buf_len >= blob
    wi = WorkItem(
        service=svc, code_hash=ch, payload=TBytes(payload),
        refine_gas_limit=Gas(50_000), accumulate_gas_limit=Gas(50_000),
        import_segments=ImportSpecs([]), extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    pkg.items.append(wi)
    r, e, u = PsiR(0, p=pkg, auth_trace=b"", i_segments=_isegs_for(pkg), e_offset=0).execute()
    assert r.get_key() == "ok"
    assert _decode_bytes_result(r.encode()) ==blob

    # === case B: buffer smaller -> truncated ===
    pkg2 = create_dummy_package()
    trunc = 5
    payload2 = struct.pack("<Q", trunc) + bytes(blob_hash)  # buf_len < blob
    wi2 = WorkItem(
        service=svc, code_hash=ch, payload=TBytes(payload2),
        refine_gas_limit=Gas(50_000), accumulate_gas_limit=Gas(50_000),
        import_segments=ImportSpecs([]), extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    pkg2.items.append(wi2)
    r2, e2, u2 = PsiR(0, p=pkg2, auth_trace=b"", i_segments=_isegs_for(pkg2), e_offset=0).execute()
    assert r2.get_key() == "ok"
    assert _decode_bytes_result(r2.encode()) == blob[:trunc]


def test_lookup_into_missing(db_path):
    # --- setup ---
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
    state = setup_state(settings.state_db, GhostState.genesis())

    code = _artifact("lookup_into").read_bytes()
    svc  = ServiceId(72)
    ch   = _register(state, svc, code)

    # Ask for a hash that does not exist in this service’s preimage store
    missing_hash = Hash.blake2b(b"definitely-missing")
    payload = struct.pack("<Q", 16) + bytes(missing_hash)

    pkg = create_dummy_package()
    wi = WorkItem(
        service=svc, code_hash=ch, payload=TBytes(payload),
        refine_gas_limit=Gas(50_000), accumulate_gas_limit=Gas(50_000),
        import_segments=ImportSpecs([]), extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    pkg.items.append(wi)

    r, e, u = PsiR(0, p=pkg, auth_trace=b"", i_segments=_isegs_for(pkg), e_offset=0).execute()
    assert r.get_key() == "ok"

    assert _decode_bytes_result(r.encode()) == b'NONE'
