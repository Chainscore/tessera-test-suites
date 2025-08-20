
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
from jam.execution.host_calls.invocations.accumulate import PsiA
from jam.types.state.accumulation.types import StateContext, OperandTuples


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
    return [[] for _ in range(len(pkg.items))]


def test_set_kv_accumulate(db_path):
    # --- setup state ---
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
    state = setup_state(settings.state_db, GhostState.genesis())
    package = create_dummy_package()

    # --- register service ---
    set_code = _artifact("set").read_bytes()
    svc = ServiceId(1)
    ch  = _register(state, svc, set_code)

    # --- payload for set: [k_len:u64][v_len:u64][key][val] ---
    key = b"mykey"
    val = b"my-value"
    payload = struct.pack("<QQ", len(key), len(val)) + key + val

    wi = WorkItem(
        service=svc, code_hash=ch, payload=Bytes(payload),
        refine_gas_limit=Gas(50_000), accumulate_gas_limit=Gas(50_000),
        import_segments=ImportSpecs([]), extrinsic=ExtrinsicSpecs([]),
        export_count=Uint,
    )
    package.items.append(wi)

    # --- run refine for item 0 (pass-through) ---
    rR, eR, uR = PsiR(0, p=package, auth_trace=b"", i_segments=_isegs_for(package), e_offset=0).execute()
    assert rR.get_key() == "ok"

    # --- run accumulate for service 1 (mutates storage) ---
    partial = StateContext(
        service_accounts=state.delta, validator_keys=state.iota,
        authorizer_keys=state.phi, privileges=state.chi,
    )
    updated_state, deferred, commit, gas_used, preimages = PsiA(
        u=partial, t=state.tau, s=svc, g=Gas(50_000), o=OperandTuples([])
    ).execute()

    # The service echoes 'val' into storage under the work-package-hash
    pkg_hash = bytes(Hash.blake2b(package.encode()))
    from tsrkit_types.bytes import Bytes as TBytes
    k32 = TBytes[32](pkg_hash)

    got = updated_state.service_accounts[svc].storage[k32]
    assert bytes(got) == val
