# from pathlib import Path
# import struct
# # from jam.accumulation.types import OperandTuples, StateContext
# import pytest

# from jam.state.ghost import GhostState
# from jam.state.state import setup_state
# from jam.settings import setup_setting

# from jam.utils.dummy.dummy_package import create_dummy_package

# from jam.types.protocol.core import Balance, BlobLength, Gas, ServiceId
# from jam.types.protocol.crypto import Hash
# from jam.types.state.delta import AccountMetadata, Ai, Ao, LookupTable, Timestamps
# from jam.types.work.item import WorkItem, ImportSpecs, ExtrinsicSpecs
# from tsrkit_types.bytes import Bytes as TBytes
# from tsrkit_types.enum import Uint

# from jam.execution.host_calls.invocations.refine import PsiR
# from jam.execution.host_calls.invocations.accumulate import OperandTuples, PsiA, StateContext


# def _artifact(name: str) -> Path:
#     p = Path(__file__).parents[4] / "tessera-test-suites" / "playground" / "builds" / f"{name}-service.jam"
#     if not p.exists():
#         pytest.skip(f"Missing artifact: {p}")
#     return p


# def _register(state, sid: ServiceId, code: bytes):
#     ch = Hash.blake2b(code)
#     state.delta[sid].service = AccountMetadata(
#         code_hash=ch, balance=Balance(1_000_000),
#         gas_limit=Gas(50_000), min_gas=Gas(1_000),
#         num_i=Ai(0), num_o=Ao(0),
#     )
#     state.delta[sid].preimages[ch] = TBytes(code)
#     state.delta[sid].lookup[LookupTable(hash=ch, length=BlobLength(len(code)))] = Timestamps([state.tau])
#     return ch


# def _isegs_for(pkg):
#     return [[] for _ in range(len(pkg.items))]


# def _scale_vec_u8_key(raw: bytes) -> bytes:
#     # Minimal compact-encoding for small (<64) Vec<u8> keys used by typed storage
#     l = len(raw)
#     assert l < 64
#     return bytes([(l << 2)]) + raw


# def test_get_readonly_found_and_missing(db_path):
#     # Setup
#     settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
#     state = setup_state(settings.state_db, GhostState.genesis())

#     get_code = _artifact("get_1").read_bytes()
#     svc = ServiceId(20)
#     ch  = _register(state, svc, get_code)
#     print("Hellow bro")
#     # ===== Seed a value under the typed key (found case) =====
#     seed_key = b"mykey"
#     typed_key = _scale_vec_u8_key(seed_key)
#     hkey32 = TBytes[32](bytes(Hash.blake2b(typed_key)))
#     state.delta[svc].storage[hkey32] = TBytes(b"seed-value")

#     # Build package A with payload [k_len][k_bytes]
#     pkgA = create_dummy_package()
#     payloadA = struct.pack("<Q", len(seed_key)) + seed_key
#     wiA = WorkItem(
#         service=svc, code_hash=ch, payload=TBytes(payloadA),
#         refine_gas_limit=Gas(50_000), accumulate_gas_limit=Gas(50_000),
#         import_segments=ImportSpecs([]), extrinsic=ExtrinsicSpecs([]),
#         export_count=Uint[16](0),
#     )
#     pkgA.items.append(wiA)

#     # refine -> accumulate
#     rA, eA, uA = PsiR(0, p=pkgA, auth_trace=b"", i_segments=_isegs_for(pkgA), e_offset=0).execute()
#     assert rA.get_key() == "ok"

#     partialA = StateContext(
#         service_accounts=state.delta,
#         validator_keys=state.iota,
#         authorizer_keys=state.phi,
#         privileges=state.chi,
#     )
#     updatedA, *_ = PsiA(
#         u=partialA, t=state.tau, s=svc, g=Gas(50_000), o=OperandTuples([])
#     ).execute()

#     # Service wrote the fetched value under the work-package hash
#     pkgA_key32 = TBytes[32](bytes(Hash.blake2b(pkgA.encode())))
#     print("Hellobrodaa",updatedA.service_accounts[svc].storage[pkgA_key32])
#     assert bytes(updatedA.service_accounts[svc].storage[pkgA_key32]) == b"seed-value"
#     # Original key remains unchanged
#     assert bytes(updatedA.service_accounts[svc].storage[hkey32]) == b"seed-value"

#     # ===== Missing key =====
#     missing_key = b"does-not-exist"
#     pkgB = create_dummy_package()
#     payloadB = struct.pack("<Q", len(missing_key)) + missing_key
#     wiB = WorkItem(
#         service=svc, code_hash=ch, payload=TBytes(payloadB),
#         refine_gas_limit=Gas(50_000), accumulate_gas_limit=Gas(50_000),
#         import_segments=ImportSpecs([]), extrinsic=ExtrinsicSpecs([]),
#         export_count=Uint,
#     )
#     pkgB.items.append(wiB)

#     rB, eB, uB = PsiR(0, p=pkgB, auth_trace=b"", i_segments=_isegs_for(pkgB), e_offset=0).execute()
#     assert rB.get_key() == "ok"

#     partialB = StateContext(
#         service_accounts=updatedA.service_accounts,  # carry forward latest state
#         validator_keys=state.iota,
#         authorizer_keys=state.phi,
#         privileges=state.chi,
#     )
#     updatedB, *_ = PsiA(
#         u=partialB, t=state.tau, s=svc, g=Gas(50_000), o=OperandTuples([])
#     ).execute()

#     pkgB_key32 = TBytes[32](bytes(Hash.blake2b(pkgB.encode())))
#     assert bytes(updatedB.service_accounts[svc].storage[pkgB_key32]) == b"ERR:NotFound"

# perf/tests/accumulation/test_set_get_storage.py

from jam.state.state import setup_state
from jam.settings import setup_setting
from jam.utils.dummy.dummy_package import create_dummy_package

from jam.types.protocol.core import Balance, BlobLength, Gas, ServiceId
from jam.types.protocol.crypto import Hash
from jam.types.state.delta import AccountMetadata, Ai, Ao, LookupTable, Timestamps
from jam.types.work.item import WorkItem, ImportSpecs, ExtrinsicSpecs
from jam.types.state.accumulation.types import StateContext, OperandTuples
from tsrkit_types.bytes import Bytes as TBytes
from tsrkit_types.enum import Uint

from jam.execution.host_calls.invocations.refine import PsiR
from jam.execution.host_calls.invocations.accumulate import PsiA


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
    return ch

def _isegs_for(pkg):
    return [[] for _ in range(len(pkg.items))]


def test_set_then_get_storage(db_path):
    # --- setup ---
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
    state = setup_state(settings.state_db, GhostState.genesis())

    svc = ServiceId(42)
    key = b"mykey"
    val = b"seed-value"

    # ===== SET phase (register set bytecode, run refine+accumulate) =====
    set_code = _artifact("set_storage").read_bytes()
    ch_set = _register(state, svc, set_code)

    pkg_set = create_dummy_package()
    payload_set = struct.pack("<Q", len(key)) + key + struct.pack("<Q", len(val)) + val
    wi_set = WorkItem(
        service=svc, code_hash=ch_set, payload=TBytes(payload_set),
        refine_gas_limit=Gas(50_000), accumulate_gas_limit=Gas(50_000),
        import_segments=ImportSpecs([]), extrinsic=ExtrinsicSpecs([]),
        export_count=Uint,
    )
    pkg_set.items.append(wi_set)

    rS, eS, uS = PsiR(0, p=pkg_set, auth_trace=b"", i_segments=_isegs_for(pkg_set), e_offset=0).execute()
    assert rS.get_key() == "ok"

    partial = StateContext(
        service_accounts=state.delta,
        validator_keys=state.iota,
        authorizer_keys=state.phi,
        privileges=state.chi,
    )
    updated_state, *_ = PsiA(
        u=partial, t=state.tau, s=svc, g=Gas(50_000), o=OperandTuples([])
    ).execute()

    # Check echo: value stored under hash("/echo_set") == "OK"
    echo_set_key32 = TBytes[32](bytes(Hash.blake2b(b"/echo_set")))
    assert bytes(updated_state.service_accounts[svc].storage[echo_set_key32]) == b"OK"

    # ===== GET phase (switch code to get bytecode, run refine+accumulate) =====
    get_code = _artifact("get_storage").read_bytes()
    ch_get = _register(state, svc, get_code)  # same service account, new code

    pkg_get = create_dummy_package()
    payload_get = struct.pack("<Q", len(key)) + key
    wi_get = WorkItem(
        service=svc, code_hash=ch_get, payload=TBytes(payload_get),
        refine_gas_limit=Gas(50_000), accumulate_gas_limit=Gas(50_000),
        import_segments=ImportSpecs([]), extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[15](0),
    )
    pkg_get.items.append(wi_get)

    rG, eG, uG = PsiR(0, p=pkg_get, auth_trace=b"", i_segments=_isegs_for(pkg_get), e_offset=0).execute()
    assert rG.get_key() == "ok"

    partial2 = StateContext(
        service_accounts=updated_state.service_accounts,  # carry forward storage
        validator_keys=state.iota,
        authorizer_keys=state.phi,
        privileges=state.chi,
    )
    updated2, *_ = PsiA(
        u=partial2, t=state.tau, s=svc, g=Gas(50_000), o=OperandTuples([])
    ).execute()

    # GET found: echo under "/echo_get" must equal original value
    echo_get_key32 = TBytes[32](bytes(Hash.blake2b(b"/echo_get")))
    assert bytes(updated2.service_accounts[svc].storage[echo_get_key32]) == val

    # ===== GET missing key =====
    pkg_miss = create_dummy_package()
    missing = b"nope"
    payload_miss = struct.pack("<Q", len(missing)) + missing
    wi_miss = WorkItem(
        service=svc, code_hash=ch_get, payload=TBytes(payload_miss),
        refine_gas_limit=Gas(50_000), accumulate_gas_limit=Gas(50_000),
        import_segments=ImportSpecs([]), extrinsic=ExtrinsicSpecs([]),
        export_count=Uint,
    )
    pkg_miss.items.append(wi_miss)

    rM, eM, uM = PsiR(0, p=pkg_miss, auth_trace=b"", i_segments=_isegs_for(pkg_miss), e_offset=0).execute()
    assert rM.get_key() == "ok"

    partial3 = StateContext(
        service_accounts=updated2.service_accounts,
        validator_keys=state.iota,
        authorizer_keys=state.phi,
        privileges=state.chi,
    )
    updated3, *_ = PsiA(
        u=partial3, t=state.tau, s=svc, g=Gas(50_000), o=OperandTuples([])
    ).execute()

    assert bytes(updated3.service_accounts[svc].storage[echo_get_key32]) == b"ERR:NotFound"
