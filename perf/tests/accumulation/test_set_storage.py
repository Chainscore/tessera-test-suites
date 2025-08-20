# perf/tests/accumulation/test_set_storage.py


from jam.state.state import setup_state
from jam.settings import setup_setting
from jam.utils.dummy.dummy_package import create_dummy_package

from jam.types.protocol.core import Balance, BlobLength, Gas, ServiceId
from jam.types.protocol.crypto import Hash, OpaqueHash
from jam.types.state.delta import AccountMetadata, Ai, Ao, LookupTable, Timestamps
from jam.types.work.item import WorkItem, ImportSpecs, ExtrinsicSpecs
from jam.types.work import WorkExecResult
from jam.types.state.accumulation.types import StateContext, OperandTuple, OperandTuples

from tsrkit_types.bytes import Bytes as TBytes
from tsrkit_types.enum import Uint

from jam.execution.host_calls.invocations.refine import PsiR
from jam.execution.host_calls.invocations.accumulate import PsiA


# --- helpers -----------------------------------------------------------------

def _artifact(name: str) -> Path:
    # Adjust parents[..] if your layout differs

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
    # one empty list per item in the package
    return [[] for _ in range(len(pkg.items))]

def _operand_from_psir(package, r: WorkExecResult, gas_used: Gas, o_bytes: bytes = b"") -> OperandTuple:
    """Build an OperandTuple the accumulate VM will accept."""
    return OperandTuple(
        h = OpaqueHash(bytes(Hash.blake2b(package.encode()))),  # WorkPackageHash
        e = OpaqueHash([0]*32),                                 # ExportsRoot (unused here)
        a = OpaqueHash([0]*32),
        y = OpaqueHash([0]*32),
        g = Uint[64](int(gas_used)),
        d = r,                                                  # refine result choice
        o = TBytes(o_bytes),                                    # optional witness
    )


# --- test --------------------------------------------------------------------

def test_set_storage_refine_then_accumulate(db_path):
    # 1) state setup
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
    state = setup_state(settings.state_db, GhostState.genesis())

    svc_set = ServiceId(42)
    set_code = _artifact("set_storage").read_bytes()
    ch_set = _register(state, svc_set, set_code)

    # key/value to store
    key = b"mykey"
    val = b"seed-value"

    # 2) package + refine (service’s refine is pass-through)
    pkg = create_dummy_package()
    payload = struct.pack("<Q", len(key)) + key + struct.pack("<Q", len(val)) + val
    wi = WorkItem(
        service=svc_set, code_hash=ch_set, payload=TBytes(payload),
        refine_gas_limit=Gas(50_000), accumulate_gas_limit=Gas(50_000),
        import_segments=ImportSpecs([]), extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    pkg.items.append(wi)

    rR, eR, uR = PsiR(0, p=pkg, auth_trace=b"", i_segments=_isegs_for(pkg), e_offset=0).execute()
    assert rR.get_key() == "ok"

    # 3) accumulate (must provide an OperandTuple so the VM builds AccumulateItem for our service)
    op = _operand_from_psir(pkg, rR, uR)
    ops = OperandTuples([op])

    partial = StateContext(
        service_accounts=state.delta,
        validator_keys=state.iota,
        authorizer_keys=state.phi,
        privileges=state.chi,
    )
    u_state, *_ = PsiA(u=partial, t=state.tau, s=svc_set, g=Gas(50_000), o=ops).execute()

    # 4) assertions

    # The service writes an echo under raw key "/echo_set" => hashed in state
    echo_key32 = TBytes[32](bytes(Hash.blake2b(b"/echo_set")))
    echo_bytes = u_state.service_accounts[svc_set].storage[echo_key32]
    assert echo_bytes is not None, "accumulate didn’t run (echo_set missing)"
    assert bytes(echo_bytes) == b"OK"

    # The actual KV write: set_storage stores under blake2b(key)
    data_key32 = TBytes[32](bytes(Hash.blake2b(key)))
    stored = u_state.service_accounts[svc_set].storage[data_key32]
    assert stored is not None, "stored value missing"
    assert bytes(stored) == val
