
from pathlib import Path

from jam.block.block import Block
from jam.block.header.header import TimeSlot
from jam.execution.pvm.memory import logger
from jam.state.ghost import GhostState
from jam.state.state import setup_state
from jam.state.storage import Finality
from jam.types.protocol.core import Balance, BlobLength, Gas, ServiceId
from jam.types.protocol.crypto import Hash
from jam.execution.host_calls.invocations.accumulate import PsiA, StateContext  # your PsiA
from jam.types.state.accumulation.types import ExportsRoot, OperandTuple, OperandTuples, WorkPackageHash
from jam.types.state.beta import BlockHistory
from jam.types.state.delta import AccountMetadata, Ai, Ao, LookupTable, Timestamps
from jam.types.work.execution import BeefyRoot, HeaderHash
from jam.types.work.item import ExtrinsicSpecs, ImportSpecs, WorkItem
from jam.types.work.package import RefineContext
from jam.utils.merkle.mountain_merkle import OpaqueHash
from tsrkit_types.bytes import Bytes
from tsrkit_types.enum import Uint
from jam.settings import setup_setting
from jam.execution.host_calls.invocations.refine import PsiR
from jam.utils.dummy.dummy_package import create_dummy_package
from jam.utils.merkle import MMRFunctions

def _ops(pkg_hash: WorkPackageHash, r1, item_gas: int = 10) -> OperandTuples:
    """
    Build a single-item OperandTuples with non-zero per-item gas,
    so the VM keeps and processes the item.
    """
    zero32 = bytes(32)
    return OperandTuples([
        OperandTuple(
            h=pkg_hash,
            e=ExportsRoot(zero32),
            a=OpaqueHash(zero32),
            y=OpaqueHash(zero32),
            g=Uint(item_gas),   # non-zero
            d=r1,               # refine result
            o=Bytes(b""),    # no extra operand bytes
        )
    ])

def _pkg_hash(pkg) -> WorkPackageHash:
    return WorkPackageHash(Hash.blake2b(pkg.encode()))


def test_gas_refine(db_path):
    service = "is_available_accu"
    payload=b"007" #Length error
    # payload=Hash.blake2b(b"payload") #panic error for not found

    settings = setup_setting(name="Bob",port= 40001, seed=1, data_path=db_path)
    state = setup_state(settings.state_db, genesis="dev-spec.json")
    block1=Block.genesis()
    print("block1 header hash",Hash.blake2b(block1.encode()).hex())
    header_hash = block1.save(settings.main_db)
    Finality.set_head(header_hash, settings.main_db)
    Finality.finalise(header_hash, settings.main_db)
    state.transition(block1)
    block2=block1.produce(time_slot=TimeSlot(1),ticket=None)
    print("block2 header hash",Hash.blake2b(block2.encode()).hex())

    state.transition(block2)

    wp = create_dummy_package()
    wi_service_code = open(Path(__file__).parents[4] / "tessera-test-suites" / "playground" / "builds" / f"{service}-service.jam", "rb").read()
    wi_code_hash = Hash.blake2b(wi_service_code)
    wi_service = ServiceId(1)

    payload=wi_code_hash # successfully fetching the data
    print("beta bhai",state.beta.to_json())
    if len(state.beta):
        merklizer = MMRFunctions()
        lookup_anchor: Block = Finality.load_final(settings.main_db)
        last_block: Block = Finality.load_latest(settings.main_db)
        anchor: BlockHistory = state.beta[-1]
        refine_context = RefineContext.empty()

        refine_context.anchor = anchor.header_hash
        refine_context.state_root = state.root
        refine_context.beefy_root = BeefyRoot(merklizer.super_peak(anchor.mmr))
        # refine_context.lookup_anchor = HeaderHash(lookup_anchor.header.hash())
        # refine_context.lookup_anchor_slot = lookup_anchor.header.slot

        refine_context.lookup_anchor = HeaderHash(last_block.header.hash())
        refine_context.lookup_anchor_slot = last_block.header.slot
        wp.context = refine_context
        logger.info("OVERRIDDEN REFINE CONTEXT", context=refine_context.to_json())
    state.delta[wi_service].service = AccountMetadata(code_hash=wi_code_hash, balance=Balance(1_000_000), gas_limit=Gas(500), min_gas=Gas(500), num_i=Ai(0), num_o=Ao(0))
    state.delta[wi_service].preimages[wi_code_hash] = Bytes(wi_service_code)
    state.delta[wi_service].lookup[LookupTable(hash=wi_code_hash, length=BlobLength(len(wi_service_code)))] = Timestamps([state.tau])
    wi = WorkItem(
            service=wi_service,
            code_hash=wi_code_hash,
            payload=Bytes(payload),
            refine_gas_limit=Gas(1_000),
            accumulate_gas_limit=Gas(1_000),
            import_segments=ImportSpecs([]),
            extrinsic=ExtrinsicSpecs([]),
            export_count=Uint[16](0)
    )
    wp.items.append(wi)
    print("Items:", wp.items)
    try:
        # Attempt to execute the work item
        r, e, u = PsiR(0, p=wp, auth_trace=b"", i_segments=[[]], e_offset=0).execute()

        # If the execution succeeds, this code will run
        print(f"🎉 Work Item executed successfully | Status: {r} | Gas consumed {u} | Exported Segments {e}")
        partial_state = StateContext(
            service_accounts=state.delta, validator_keys=state.iota,
            authorizer_keys=state.phi, privileges=state.chi,
        )
        timeslot = TimeSlot(state.tau)
        gas = Gas(5_0000)
        from jam.types.state.accumulation.types import OperandTuples
        # operands = OperandTuples([])
        operands=_ops(_pkg_hash(wp),r,item_gas=10000)
        # operands.append(OperandTuple(

        # ))
        new_state_ctx, deferred_transfers, commit_opt, gas_left, preimages = PsiA(
            partial_state, timeslot, wi_service, gas, operands
        ).execute()
        print("updated storage",new_state_ctx.service_accounts[wi_service].storage[Bytes[32](bytes(Hash.blake2b(b"/is_avail/last")))])
        print("updated data",deferred_transfers, commit_opt, gas_left, preimages )
    except Exception as e:
        # Catch any other unexpected exceptions
        print(f"❌ An unexpected error occurred: {e}")
