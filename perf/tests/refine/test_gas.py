# perf/tests/test_gas_service.py

from pathlib import Path

from jam.execution.host_calls.invocations.functions.refine_fns import Segments
from jam.execution.pvm.memory import logger
from jam.state.ghost import GhostState
from jam.state.state import setup_state
from jam.types.protocol.core import Balance, BlobLength, Gas, ServiceId
from jam.types.protocol.crypto import Hash
from jam.types.state.delta import AccountMetadata, Ai, Ao, LookupTable, Timestamps
from jam.types.work.item import ExtrinsicSpecs, ImportSpecs, WorkItem
from tsrkit_types.bytes import Bytes
from tsrkit_types.enum import Uint
from jam.settings import setup_setting
from jam.utils.dummy.dummy_package import create_dummy_package
from jam.execution.host_calls.invocations.refine import PsiR


def test_gas_refine(db_path):
    service = "gas"
    payload = b"ins"

    settings = setup_setting("data/god_mode", 3000, 2**16 - 1, db_path)
    state = setup_state(settings.state_db, GhostState.genesis())

    package = create_dummy_package()
    wi_service_code = open(Path(__file__).parents[4] / "tessera-test-suites" / "playground" / "builds" / f"{service}-service.jam", "rb").read()
    wi_code_hash = Hash.blake2b(wi_service_code)
    wi_service = ServiceId(1)

    state.delta[wi_service].service = AccountMetadata(code_hash=wi_code_hash, balance=Balance(1_000_000), gas_limit=Gas(1_000), min_gas=Gas(1_000), num_i=Ai(0), num_o=Ao(0))
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
            export_count=Uint[16](1)
    )
    package.items.append(wi)
    print("Items:", package.items)
    r, e, u = PsiR(0, p=package, auth_trace=b"", i_segments=[[]], e_offset=0).execute()
    # print(f"🎉 Work Item executed | Status: {r} | Gas consumed {u} | Exported Segments {e}")

    assert(r.get_key() == "ok")
    assert(r == b'^\xeb\xfa\x02\x00\x00\x00\x00' and e ==Segments([]) )
    logger.info("Gas test passed, consumed: {} status {}".format(u,r.get_key()))
