
from pathlib import Path
from jam.state.state import setup_state
from jam.settings import setup_setting
from jam.utils.dummy.dummy_package import create_dummy_package

from jam.types.protocol.core import Balance, BlobLength, Gas, ServiceId
from jam.types.protocol.crypto import Hash
from jam.types.state.delta import AccountMetadata, Ai, Ao, LookupTable, Timestamps
from jam.types.work.item import WorkItem, ImportSpecs, ExtrinsicSpecs
from jam.types.work import WorkExecResult
import pytest
from tsrkit_types.bytes import Bytes
from tsrkit_types.enum import Uint

from jam.execution.host_calls.invocations.refine import PsiR
from jam.execution.host_calls.invocations.accumulate import PsiA  # your PsiA class
from jam.types.state.accumulation.types import StateContext, OperandTuples

def _artifact(name: str) -> Path:
    p = (
        Path(__file__).parents[4]
        / "tessera-test-suites"
        / "playground"
        / "builds"
        / f"{name}-service.jam"
    )
    if not p.exists():
        pytest.skip(f"Missing artifact: {p}")
    return p

def _register(state, sid: ServiceId, code: bytes):
    ch = Hash.blake2b(code)
    state.delta[sid].service = AccountMetadata(
        code_hash=ch, balance=Balance(1_000_000),
        gas_limit=Gas(20000), min_gas=Gas(1000),
        num_i=Ai(0), num_o=Ao(0)
    )
    state.delta[sid].preimages[ch] = Bytes(code)
    state.delta[sid].lookup[LookupTable(hash=ch, length=BlobLength(len(code)))] = Timestamps([state.tau])
    return ch

def _isegs_for(pkg):
    return [[] for _ in range(len(pkg.items))]

def _read_from_statectx(u: StateContext, sid: ServiceId, key: bytes) -> bytes | None:
    """
    Helper to peek the service storage from the returned StateContext.
    In most JAM setups, raw key->value is stored under a hashed key internally.
    The helper below uses the same hashing as the runtime: blake2b(key).
    """
    key_hash = Hash.blake2b(key)  # 32-byte digest type
    # The exact attribute to reach storage may differ in your tree; adapt if needed:
    storage = u.service_accounts[sid].storage

def test_checkpoint(db_path, mode, expect_a, expect_b):
    # --- state/setup ---
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
    state = setup_state(settings.state_db, GhostState.genesis())
    package = create_dummy_package()

    # --- artifact & registration ---
    code = _artifact("checkpoint").read_bytes()
    svc  = ServiceId(1)
    ch   = _register(state, svc, code)

    # --- WorkItem: payload[0] == mode ---
    wi = WorkItem(
        service=svc, code_hash=ch, payload=Bytes(bytes([mode])),
        refine_gas_limit=Gas(20_000), accumulate_gas_limit=Gas(20_000),
        import_segments=ImportSpecs([]), extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    package.items.append(wi)

    # 1) refine (pass-through)
    rR, eR, uR = PsiR(0, p=package, auth_trace=b"", i_segments=_isegs_for(package), e_offset=0).execute()
    assert rR.get_key() == "ok"
    print(
        "Refinement DONE!!"
    )
    # 2) accumulate (does the writes + checkpoint + optional panic)
    partial = StateContext(
        service_accounts=state.delta,
        validator_keys=state.iota,
        authorizer_keys=state.phi,
        privileges=state.chi,
    )
    u2, deferred, commit, gas_used, preimages = PsiA(
        u=partial, s=svc, t=state.tau, g=Gas(20_000), o=OperandTuples([])
    ).execute()


    # PANIC path still returns collapsed StateContext (PsiA.collapse chooses context.y)
    # Now check storage according to expectation:
    data=b"/a"
    key=Hash.blake2b(data)
    got_a = _read_from_statectx(u2, svc, key) is not None
    # got_b = _read_from_statectx(u2, svc, Hash.blake2b(b"/b")) is not None
    # assert got_a is expect_a
    # assert got_b is expect_b
