import struct
from pathlib import Path
import pytest

from jam.execution.host_calls.invocations.refine import PsiR
from jam.execution.host_calls.invocations.accumulate import PsiA  # STOCK PsiA

from jam.settings import setup_setting
from jam.state.ghost import GhostState
from jam.state.state import setup_state

from jam.types.protocol.core import Balance, Gas, ServiceId, WorkPackageHash, BlobLength, ExportsRoot
from jam.types.protocol.crypto import Hash, OpaqueHash
from jam.types.state.delta import AccountMetadata, Ai, Ao, LookupTable, Timestamps
from jam.types.work.item import WorkItem, ImportSpecs, ExtrinsicSpecs
from jam.types.state.accumulation.types import StateContext, OperandTuple, OperandTuples

from tsrkit_types.bytes import Bytes as TBytes
from tsrkit_types.enum import Uint


# ---------- helpers ----------

def _artifact(name: str) -> Path:
    p = Path(__file__).parents[4] / "tessera-test-suites" / "playground" / "builds" / f"{name}-service.jam"
    if not p.exists():
        pytest.skip(f"Missing artifact: {p}")
    return p

def _register(state, sid: ServiceId, code: bytes):
    ch = Hash.blake2b(code)
    state.delta[sid].service = AccountMetadata(
        code_hash=ch, balance=Balance(1_000_000),
        gas_limit=Gas(80_000), min_gas=Gas(1_000),
        num_i=Ai(0), num_o=Ao(0),
    )
    state.delta[sid].preimages[ch] = TBytes(code)
    # common lookup seeding pattern
    state.delta[sid].lookup[LookupTable(hash=ch, length=BlobLength(1))] = Timestamps([state.tau])
    state.delta[sid].lookup[LookupTable(hash=ch, length=BlobLength(len(code)))] = Timestamps([state.tau])
    return ch

def _isegs_for(pkg): return [[] for _ in range(len(pkg.items))]
def _pkg_hash(pkg) -> WorkPackageHash: return WorkPackageHash(Hash.blake2b(pkg.encode()))

def _ops(pkg_hash, r1, item_gas=10) -> OperandTuples:
    zero32 = bytes(32)
    return OperandTuples([
        OperandTuple(
            h=pkg_hash,
            e=ExportsRoot(zero32),
            a=OpaqueHash(zero32),
            y=OpaqueHash(zero32),
            g=Uint(int(max(1, item_gas))),  # nonzero or item may be dropped
            d=r1,
            o=TBytes(b""),
        )
    ])

def _gas_payload(iters: int) -> bytes:
    return b"\x10" + struct.pack("<Q", iters)


# ---------- test ----------

def test_gas_probe(tmp_path):
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, str(tmp_path))
    state = setup_state(settings.state_db, GhostState.genesis())

    sid = ServiceId(9090)
    code = _artifact("gas_probe").read_bytes()
    ch = _register(state, sid, code)

    from jam.utils.dummy.dummy_package import create_dummy_package

    # ---- big loop ----
    pkg1 = create_dummy_package()
    wi1 = WorkItem(
        service=sid, code_hash=ch, payload=TBytes(_gas_payload(50_000)),
        refine_gas_limit=Gas(50_000), accumulate_gas_limit=Gas(50_000),
        import_segments=ImportSpecs([]), extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    pkg1.items.append(wi1)

    r1, _, _ = PsiR(0, p=pkg1, auth_trace=b"", i_segments=_isegs_for(pkg1), e_offset=0).execute()
    assert r1.get_key() == "ok"

    ops1 = _ops(_pkg_hash(pkg1), r1, item_gas=10)
    partial = StateContext(
        service_accounts=state.delta,
        validator_keys=state.iota,
        authorizer_keys=state.phi,
        privileges=state.chi,
    )
    _, _, opt_hash1, _, _ = PsiA(partial, state.tau, sid, Gas(50_000), o=ops1).execute()
    assert opt_hash1.unwrap() != OpaqueHash(bytes(32))

    # ---- small loop ----
    pkg2 = create_dummy_package()
    wi2 = WorkItem(
        service=sid, code_hash=ch, payload=TBytes(_gas_payload(500)),
        refine_gas_limit=Gas(50_000), accumulate_gas_limit=Gas(50_000),
        import_segments=ImportSpecs([]), extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    pkg2.items.append(wi2)
    r2, _, _ = PsiR(0, p=pkg2, auth_trace=b"", i_segments=_isegs_for(pkg2), e_offset=0).execute()
    assert r2.get_key() == "ok"

    ops2 = _ops(_pkg_hash(pkg2), r2, item_gas=10)
    _, _, opt_hash2, _, _ = PsiA(
        StateContext(
            service_accounts=state.delta,
            validator_keys=state.iota,
            authorizer_keys=state.phi,
            privileges=state.chi,
        ),
        state.tau, sid, Gas(50_000), o=ops2
    ).execute()
    assert opt_hash2.unwrap() != OpaqueHash(bytes(32))

    # With different loop sizes, commitments should differ
    assert opt_hash1.unwrap() != opt_hash2.unwrap()
