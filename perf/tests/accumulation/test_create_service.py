# perf/tests/test_create_service.py
from pathlib import Path
import struct
from jam.execution.pvm.memory import logger

from jam.state.state import setup_state
from jam.settings import setup_setting
from jam.utils.dummy.dummy_package import create_dummy_package

from jam.types.protocol.core import Balance, BlobLength, Gas, ServiceId
from jam.types.protocol.crypto import Hash
from jam.types.state.delta import AccountMetadata, Ai, Ao, LookupTable, Timestamps
from jam.types.work.item import WorkItem, ImportSpecs, ExtrinsicSpecs
from tsrkit_types.bytes import Bytes
from tsrkit_types.enum import Uint

from jam.execution.host_calls.invocations.refine import PsiR
try:
    from jam.execution.host_calls.invocations.accumulate import PsiA   # <- adjust if name differs
except Exception:
    PsiA = None

def _artifact(name: str) -> Path:

def _register(state, sid: ServiceId, code: bytes):
    ch = Hash.blake2b(code)
    state.delta[sid].service = AccountMetadata(
        code_hash=ch, balance=Balance(1_000_000),
        gas_limit=Gas(50_000), min_gas=Gas(1_000),
        num_i=Ai(0), num_o=Ao(0),
    )
    state.delta[sid].preimages[ch] = Bytes(code)
    state.delta[sid].lookup[LookupTable(hash=ch, length=BlobLength(len(code)))] = Timestamps([state.tau])
    return ch

def _isegs_for(pkg):

    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
    state = setup_state(settings.state_db, GhostState.genesis())
    package = create_dummy_package()

    # --- artifacts ---
    creator_code = _artifact("create_service").read_bytes()
    # this will be the NEW service's code (preimage must be present)
    new_code     = _artifact("hello").read_bytes()

    svc_creator = ServiceId(1)
    ch_creator  = _register(state, svc_creator, creator_code)

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
    assert rR.get_key() == "ok"

    partial_state= StateContext(
        service_accounts=state.delta,
        validator_keys=state.iota,
        authorizer_keys=state.phi,
        privileges=state.chi
    )
    service_id = svc_creator
    timeslot=state.tau
    gas=Gas(50_000)
    operand=OperandTuples([])

    # 2) accumulate — actually call create_service
    u2, deferred, commit, gas_used, preimages = PsiA(u=partial_state,s=service_id, t=timeslot, g=gas, o=operand).execute()

    # print(u2,deferred,commit,gas_used,preimages)



    # Verify it created a service by finding any account with this code_hash
    # (Optionally, you can also read the /last_created key if you have a storage read helper)
    # found = False
    # # NOTE: adapt this iteration to your delta indexing if needed
    # for sid in range(1, 10_000):
    #     try:
    #         if state.delta[ServiceId(sid)].service.code_hash == new_hash:
    #             found = True
    #             break
    #     except Exception:
    #         pass
    # assert found, "new service with provided code_hash not found after accumulate()"
