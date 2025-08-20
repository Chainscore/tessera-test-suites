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
    state.delta[sid].preimages[ch] = TBytes(code)
    state.delta[sid].lookup[LookupTable(hash=ch, length=BlobLength(len(code)))] = Timestamps([state.tau])
    return ch


def _isegs_for(pkg):
    return [[] for _ in range(len(pkg.items))]


def test_lookup_found(db_path):
    # --- setup ---
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
    state = setup_state(settings.state_db, GhostState.genesis())

    # register the lookup service
    lookup_code = _artifact("lookup").read_bytes()
    svc = ServiceId(77)
    ch  = _register(state, svc, lookup_code)

    # seed a preimage in THIS service's preimage store
    blob      = b"hello-preimage-body"
    blob_hash = Hash.blake2b(blob)
    state.delta[svc].preimages[blob_hash] = TBytes(blob)
    state.delta[svc].lookup[LookupTable(hash=blob_hash, length=BlobLength(len(blob)))] = Timestamps([state.tau])

    # payload: [hash:32]
    payload = bytes(blob_hash)

    pkg = create_dummy_package()
    wi = WorkItem(
        service=svc,
        code_hash=ch,
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
    out = r.unwrap()
    assert out == blob, f"expected preimage bytes, got {out!r}"


def test_lookup_missing(db_path):
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
    state = setup_state(settings.state_db, GhostState.genesis())

    lookup_code = _artifact("lookup").read_bytes()
    svc = ServiceId(78)
    ch  = _register(state, svc, lookup_code)

    # fake hash that doesn't exist
    fake_hash = Hash.blake2b(b"nope")
    payload   = bytes(fake_hash)

    pkg = create_dummy_package()
    wi = WorkItem(
        service=svc,
        code_hash=ch,
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
    out = r.unwrap()
    assert out == b"NONE"
