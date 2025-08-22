from pathlib import Path
import struct
import pytest

from jam.execution.host_calls.invocations.refine import PsiR
from jam.execution.host_calls.invocations.accumulate import PsiA

from jam.settings import setup_setting
from jam.state.ghost import GhostState
from jam.state.state import setup_state

from jam.types.protocol.core import (
    Balance, Gas, ServiceId, WorkPackageHash, BlobLength, ExportsRoot,
)
from jam.types.protocol.crypto import Hash, OpaqueHash
from jam.types.state.delta import AccountMetadata, Ai, Ao, LookupTable, Timestamps
from jam.types.state.accumulation.types import StateContext, OperandTuple, OperandTuples
from jam.types.work.item import WorkItem, ImportSpecs, ExtrinsicSpecs

from tsrkit_types.enum import Uint
from tsrkit_types.bytes import Bytes as TBytes
from tsrkit_types import Bytes as RawBytes


# ---------- helpers ----------

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


def _isegs_for(pkg):
    return [[] for _ in range(len(pkg.items))]


def _pkg_hash(pkg) -> WorkPackageHash:
    return WorkPackageHash(Hash.blake2b(pkg.encode()))


def _ops(pkg_hash: WorkPackageHash, r1, item_gas: int = 10) -> OperandTuples:
    zero32 = bytes(32)
    return OperandTuples([
        OperandTuple(
            h=pkg_hash,
            e=ExportsRoot(zero32),
            a=OpaqueHash(zero32),
            y=OpaqueHash(zero32),
            g=Uint(item_gas),   # must be non-zero or VM may drop the item
            d=r1,
            o=RawBytes(b""),
        )
    ])


def _read_hashed(u_state: StateContext, sid: ServiceId, raw_key: bytes) -> bytes | None:
    """Read storage via hashed key (blake2b(raw_key)) from returned StateContext."""
    acc = u_state.service_accounts[sid]
    k32 = TBytes[32](bytes(Hash.blake2b(raw_key)))
    try:
        v = acc.storage[k32]
    except KeyError:
        return None
    return v.to_bytes() if hasattr(v, "to_bytes") else bytes(v)


def _register_ejector(state, sid: ServiceId, code: bytes):
    ch = Hash.blake2b(code)
    state.delta[sid].service = AccountMetadata(
        code_hash=ch,
        balance=Balance(1_000_000),
        gas_limit=Gas(80_000),
        min_gas=Gas(1_000),
        num_i=Ai(0), num_o=Ao(0),
    )
    state.delta[sid].preimages[ch] = TBytes(code)
    state.delta[sid].lookup[LookupTable(hash=ch, length=BlobLength(len(code)))] = Timestamps([state.tau])
    return ch


def _register_ejectable_target(state, target: ServiceId, ejector: ServiceId, target_balance: int, code_hash_bytes: bytes):
    """
    Make the target look like an ejectable 'zombie':
      - code_hash = LE32(ejector_id) padded to 32 (i.e., `code_hash_bytes`)
      - ONLY ONE preimage lookup item for that hash, UNREQUESTED/DROPPABLE
      - EMPTY STORAGE
    """
    # set metadata with the special code_hash
    ch = Hash.blake2b(code_hash_bytes)
    state.delta[target].service = AccountMetadata(
        code_hash=ch, # CodeHash is same underlying; jam-py types accept Hash bytes here
        balance=Balance(target_balance),
        gas_limit=Gas(1),   # irrelevant
        min_gas=Gas(0),
        num_i=Ai(0), num_o=Ao(0),
    )

    # one preimage entry for that hash; blob can be empty
    state.delta[target].preimages[ch] = TBytes(code_hash_bytes)
    # CRITICAL: unrequested/droppable → zero timestamps; length=0
    state.delta[target].lookup[LookupTable(hash=ch, length=BlobLength(len(code_hash_bytes)))] = Timestamps([])

    # no storage writes → remains empty


# ---------- test ----------

def test_eject_zombie_service(tmp_path):
    # --- state setup ---
    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, str(tmp_path))
    state = setup_state(settings.state_db, GhostState.genesis())

    # Ejector service (this runs our code)
    ejector_id = ServiceId(7777)
    ejector_code = _artifact("ejectt").read_bytes()
    ejector_ch = _register_ejector(state, ejector_id, ejector_code)

    # Target service to eject
    target_id = ServiceId(5555)
    target_balance = 123_456

    # Build code_hash = LE32(ejector_id) padded to 32 bytes
    le4 = int(ejector_id).to_bytes(4, "little")
    target_code_hash_bytes = le4 + bytes(28)  # 32-byte CodeHash

    _register_ejectable_target(state, target_id, ejector_id, target_balance, target_code_hash_bytes)

    # --- build package with EJECT op ---
    from jam.utils.dummy.dummy_package import create_dummy_package
    pkg = create_dummy_package()

    # payload = [0xE0][target_id: u32 LE][code_hash: 32]
    payload = bytes([0xE0]) + int(target_id).to_bytes(4, "little") + target_code_hash_bytes

    wi = WorkItem(
        service=ejector_id,
        code_hash=ejector_ch,
        payload=TBytes(payload),
        refine_gas_limit=Gas(50_000),
        accumulate_gas_limit=Gas(50_000),
        import_segments=ImportSpecs([]),
        extrinsic=ExtrinsicSpecs([]),
        export_count=Uint[16](0),
    )
    pkg.items.append(wi)

    # --- refine ---
    r1, _e1, _u1 = PsiR(0, p=pkg, auth_trace=b"", i_segments=[], e_offset=0).execute()
    assert r1.get_key() == "ok"

    # --- accumulate ---
    ops = _ops(_pkg_hash(pkg), r1, item_gas=10)
    partial = StateContext(
        service_accounts=state.delta,
        validator_keys=state.iota,
        authorizer_keys=state.phi,
        privileges=state.chi,
    )

    # pre balances
    pre_ejector_bal = int(state.delta[ejector_id].service.balance)
    pre_target_bal = int(state.delta[target_id].service.balance)

    u_after, transfers, commit, gas_used, preimages = PsiA(partial, state.tau, ejector_id, Gas(50_000), o=ops).execute()

    # commitment exists ⇒ accumulate ran
    assert commit.unwrap() != OpaqueHash(bytes(32))

    # (1) service recorded success
    assert _read_hashed(u_after, ejector_id, b"/eject_last") == b"OK"

    # (2) funds transferred to ejector
    post_ejector_bal = int(u_after.service_accounts[ejector_id].service.balance)
    assert post_ejector_bal == pre_ejector_bal + pre_target_bal

    # OPTIONAL sanity: target should be "gone" or emptied (implementation-dependent).
    # We at least expect its balance to be zero now if the account handle still exists.
    tgt_post_bal = int(u_after.service_accounts[target_id].service.balance)
    assert tgt_post_bal == 0
