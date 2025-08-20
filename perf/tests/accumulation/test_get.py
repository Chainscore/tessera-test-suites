
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


def test_get_kv_accumulate(db_path):
    # --- setup ---
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
    state = setup_state(settings.state_db, GhostState.genesis())
    package = create_dummy_package()

    # --- register service ---
    get_code = _artifact("get").read_bytes()
    svc = ServiceId(2)
    ch  = _register(state, svc, get_code)

    # Pre-seed this service's storage with the *typed* key encoding: we keep it simple
    # by letting the service fetch using key=b"mykey" encoded as Vec<u8>. `set` encoded
    # the key as SCALE(Vec<u8>) => [compact-len][bytes]. But our `get` service doesn't
    # rely on that here: it just needs the typed key to match how the value was written.
    #
    # Easiest route: put the value directly using `set_storage` on a *known* 32-byte key,
    # then have the service read using `get::<Vec<u8>>(key_vec)`. To keep this test
    # consistent with the service, seed via a first accumulate call of a tiny “setter”
    # payload… but simpler: just seed via delta (tests can mutate the StateContext).
    from tsrkit_types.bytes import Bytes as TBytes
    seed_key = b"mykey"
    seed_val = b"seed-value"

    # Manually place an entry using the *same* typed key encoding used by the service:
    # because the service uses `get::<Vec<u8>>(Vec<u8>::from(key))`, the encoded storage
    # key is SCALE(Vec<u8>) of seed_key. We'll quickly craft that encoding: [compact len][bytes].
    # For small (<64) lengths, compact len is 1 byte: (len << 2) | 0b00.
    def encode_vec_u8(v: bytes) -> bytes:
        l = len(v)
        assert l < 64
        return bytes([ (l << 2) ]) + v

    typed_key = encode_vec_u8(seed_key)
    state.delta[svc].storage[TBytes[32](bytes(Hash.blake2b(typed_key)))] = Bytes(seed_val)  # one possible backing (impl detail)

    # Now ask the service to `get` using seed_key
    payload = struct.pack("<Q", len(seed_key)) + seed_key
    wi = WorkItem(
        service=svc, code_hash=ch, payload=Bytes(payload),
        refine_gas_limit=Gas(50_000), accumulate_gas_limit=Gas(50_000),
        import_segments=ImportSpecs([]), extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    package.items.append(wi)

    # refine then accumulate
    rR, eR, uR = PsiR(0, p=package, auth_trace=b"", i_segments=_isegs_for(package), e_offset=0).execute()
    assert rR.get_key() == "ok"

    partial = StateContext(
        service_accounts=state.delta, validator_keys=state.iota,
        authorizer_keys=state.phi, privileges=state.chi,
    )
    updated_state, *_ = PsiA(u=partial, t=state.tau, s=svc, g=Gas(50_000), o=OperandTuples([])).execute()

    # The service echoes the fetched value under the work-package-hash
    pkg_hash = bytes(Hash.blake2b(package.encode()))
    k32 = TBytes[32](pkg_hash)
    got = updated_state.service_accounts[svc].storage[k32]
    assert bytes(got) == seed_val
