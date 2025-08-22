# perf/tests/test_create_service.py
from pathlib import Path
import struct
from jam.execution.pvm.memory import logger
from jam.state.state import setup_state, GhostState
from jam.settings import setup_setting
from jam.utils.dummy.dummy_package import create_dummy_package
from jam.types.protocol.core import Balance, BlobLength, Gas, ServiceId
from jam.types.protocol.crypto import Hash
from jam.types.state.delta import AccountMetadata, Ai, Ao, LookupTable, Timestamps
from jam.types.state.accumulation.types import StateContext, OperandTuples
from jam.types.work.item import WorkItem, ImportSpecs, ExtrinsicSpecs
import pytest
from tsrkit_types.bytes import Bytes
from tsrkit_types.enum import Uint
from jam.execution.host_calls.invocations.refine import PsiR

try:
    from jam.execution.host_calls.invocations.accumulate import PsiA
except Exception:
    PsiA = None


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
    """Register a service in the state with given code"""
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


def _isegs_for(pkg):
    """Get import segments for package"""
    return []


def test_create_service_success():
    """Test successful service creation"""
    # Setup
    db_path = "/tmp/test_create_service"
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
    state = setup_state(settings.state_db, GhostState.genesis())
    package = create_dummy_package()

    # --- artifacts ---
    creator_code = _artifact("create_service").read_bytes()
    # this will be the NEW service's code (preimage must be present)
    new_code = _artifact("hello").read_bytes()

    svc_creator = ServiceId(1)
    ch_creator = _register(state, svc_creator, creator_code)

    # Make sure the *calling* account holds the preimage for the new code
    new_hash = Hash.blake2b(new_code)
    state.delta[svc_creator].preimages[new_hash] = Bytes(new_code)
    state.delta[svc_creator].lookup[LookupTable(hash=new_hash, length=BlobLength(len(new_code)))] = Timestamps([state.tau])

    # payload = [code_hash(32)][code_len(u64)][min_item_gas(u64)][min_memo_gas(u64)]
    payload = bytes(new_hash) + struct.pack("<QQQ", len(new_code), 10_000, 1_000)

    wi = WorkItem(
        service=svc_creator,
        code_hash=ch_creator,
        payload=Bytes(payload),
        refine_gas_limit=Gas(50_000),
        accumulate_gas_limit=Gas(50_000),
        import_segments=ImportSpecs([]),
        extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    package.items.append(wi)

    # 1) refine — pass-through
    rR, eR, uR = PsiR(0, p=package, auth_trace=b"", i_segments=_isegs_for(package), e_offset=0).execute()
    assert rR.get_key() == "ok", f"Refine failed: {rR}"

    partial_state = StateContext(
        service_accounts=state.delta,
        validator_keys=state.iota,
        authorizer_keys=state.phi,
        privileges=state.chi
    )
    service_id = svc_creator
    timeslot = state.tau
    gas = Gas(50_000)
    operand = OperandTuples([])
    print("Acuu started")
    # 2) accumulate — actually call create_service
    u2, deferred, commit, gas_used, preimages = PsiA(
        u=partial_state, s=service_id, t=timeslot, g=gas, o=operand
    ).execute()

    # Verify the operation succeeded
    # print("psiA resultant",deferred,commit,gas_used,preimages,u2.service_accounts[service_id].service.balance)
    assert commit is not None, "Service creation should return a commit hash"

    # Check if we can read the created service ID from storage (if storage read is available)
    # This would require a storage read helper function

    print(f"Service creation completed:")
    print(f"  Commit hash: {commit}")
    print(f"  Gas used: {gas_used}")
    print(f"  Deferred transfers: {len(deferred) if deferred else 0}")


def test_create_service_invalid_payload():
    """Test service creation with invalid payload"""
    # Setup
    db_path = "/tmp/test_create_service_invalid"
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
    state = setup_state(settings.state_db, GhostState.genesis())
    package = create_dummy_package()

    creator_code = _artifact("create_service").read_bytes()
    svc_creator = ServiceId(1)
    ch_creator = _register(state, svc_creator, creator_code)

    # Invalid payload - too short
    invalid_payload = b"short_payload"

    wi = WorkItem(
        service=svc_creator,
        code_hash=ch_creator,
        payload=Bytes(invalid_payload),
        refine_gas_limit=Gas(50_000),
        accumulate_gas_limit=Gas(50_000),
        import_segments=ImportSpecs([]),
        extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    package.items.append(wi)

    # 1) refine
    rR, eR, uR = PsiR(0, p=package, auth_trace=b"", i_segments=_isegs_for(package), e_offset=0).execute()
    assert rR.get_key() == "ok", f"Refine failed: {rR}"

    partial_state = StateContext(
        service_accounts=state.delta,
        validator_keys=state.iota,
        authorizer_keys=state.phi,
        privileges=state.chi
    )

    # 2) accumulate
    u2, deferred, commit, gas_used, preimages = PsiA(
        u=partial_state, s=svc_creator, t=state.tau, g=Gas(50_000), o=OperandTuples([])
    ).execute()

    # Should not return a commit hash due to invalid payload
    assert commit is None, "Invalid payload should not produce a commit hash"


def test_create_service_missing_preimage():
    """Test service creation when code preimage is missing"""
    # Setup
    db_path = "/tmp/test_create_service_missing_preimage"
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
    state = setup_state(settings.state_db, GhostState.genesis())
    package = create_dummy_package()

    creator_code = _artifact("create_service").read_bytes()
    svc_creator = ServiceId(1)
    ch_creator = _register(state, svc_creator, creator_code)

    # Use a hash for code that doesn't exist in preimages
    fake_hash = Hash.blake2b(b"nonexistent_code")

    # payload = [code_hash(32)][code_len(u64)][min_item_gas(u64)][min_memo_gas(u64)]
    payload = bytes(fake_hash) + struct.pack("<QQQ", 1024, 10_000, 1_000)

    wi = WorkItem(
        service=svc_creator,
        code_hash=ch_creator,
        payload=Bytes(payload),
        refine_gas_limit=Gas(50_000),
        accumulate_gas_limit=Gas(50_000),
        import_segments=ImportSpecs([]),
        extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    package.items.append(wi)

    # 1) refine
    rR, eR, uR = PsiR(0, p=package, auth_trace=b"", i_segments=_isegs_for(package), e_offset=0).execute()
    assert rR.get_key() == "ok", f"Refine failed: {rR}"

    partial_state = StateContext(
        service_accounts=state.delta,
        validator_keys=state.iota,
        authorizer_keys=state.phi,
        privileges=state.chi
    )

    # 2) accumulate
    u2, deferred, commit, gas_used, preimages = PsiA(
        u=partial_state, s=svc_creator, t=state.tau, g=Gas(50_000), o=OperandTuples([])
    ).execute()

    # Should fail due to missing preimage
    assert commit is None, "Missing preimage should not produce a commit hash"


def test_create_multiple_services():
    """Test creating multiple services in sequence"""
    # Setup
    db_path = "/tmp/test_create_multiple_services"
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
    state = setup_state(settings.state_db, GhostState.genesis())

    creator_code = _artifact("create_service").read_bytes()
    new_code1 = _artifact("hello").read_bytes()
    new_code2 = _artifact("gas_probe").read_bytes()

    svc_creator = ServiceId(1)
    ch_creator = _register(state, svc_creator, creator_code)

    # Register preimages for both new services
    new_hash1 = Hash.blake2b(new_code1)
    new_hash2 = Hash.blake2b(new_code2)

    state.delta[svc_creator].preimages[new_hash1] = Bytes(new_code1)
    state.delta[svc_creator].lookup[LookupTable(hash=new_hash1, length=BlobLength(len(new_code1)))] = Timestamps([state.tau])

    state.delta[svc_creator].preimages[new_hash2] = Bytes(new_code2)
    state.delta[svc_creator].lookup[LookupTable(hash=new_hash2, length=BlobLength(len(new_code2)))] = Timestamps([state.tau])

    # Test creating first service
    package1 = create_dummy_package()
    payload1 = bytes(new_hash1) + struct.pack("<QQQ", len(new_code1), 15_000, 2_000)

    wi1 = WorkItem(
        service=svc_creator,
        code_hash=ch_creator,
        payload=Bytes(payload1),
        refine_gas_limit=Gas(50_000),
        accumulate_gas_limit=Gas(50_000),
        import_segments=ImportSpecs([]),
        extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    package1.items.append(wi1)

    # Execute first service creation
    rR1, eR1, uR1 = PsiR(0, p=package1, auth_trace=b"", i_segments=_isegs_for(package1), e_offset=0).execute()
    assert rR1.get_key() == "ok", f"First refine failed: {rR1}"

    partial_state = StateContext(
        service_accounts=state.delta,
        validator_keys=state.iota,
        authorizer_keys=state.phi,
        privileges=state.chi
    )

    u2_1, deferred1, commit1, gas_used1, preimages1 = PsiA(
        u=partial_state, s=svc_creator, t=state.tau, g=Gas(50_000), o=OperandTuples([])
    ).execute()

    assert commit1 is not None, "First service creation should succeed"

    # Test creating second service
    package2 = create_dummy_package()
    payload2 = bytes(new_hash2) + struct.pack("<QQQ", len(new_code2), 20_000, 3_000)

    wi2 = WorkItem(
        service=svc_creator,
        code_hash=ch_creator,
        payload=Bytes(payload2),
        refine_gas_limit=Gas(50_000),
        accumulate_gas_limit=Gas(50_000),
        import_segments=ImportSpecs([]),
        extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    package2.items.append(wi2)

    # Execute second service creation
    rR2, eR2, uR2 = PsiR(0, p=package2, auth_trace=b"", i_segments=_isegs_for(package2), e_offset=0).execute()
    assert rR2.get_key() == "ok", f"Second refine failed: {rR2}"

    # Update state with results from first creation
    partial_state2 = StateContext(
        service_accounts=u2_1.service_accounts,  # Use updated state
        validator_keys=state.iota,
        authorizer_keys=state.phi,
        privileges=state.chi
    )

    u2_2, deferred2, commit2, gas_used2, preimages2 = PsiA(
        u=partial_state2, s=svc_creator, t=state.tau, g=Gas(50_000), o=OperandTuples([])
    ).execute()

    assert commit2 is not None, "Second service creation should succeed"
    assert commit1 != commit2, "Different services should have different commit hashes"

    print(f"Created two services successfully:")
    print(f"  Service 1 commit: {commit1}")
    print(f"  Service 2 commit: {commit2}")


if __name__ == "__main__":
    test_create_service_success()
    test_create_service_invalid_payload()
    test_create_service_missing_preimage()
    test_create_multiple_services()
    print("All tests passed!")
