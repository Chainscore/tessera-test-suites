import json
from pathlib import Path
import shutil
from time import time

from jam.settings import setup_setting

import pytest
from tsrkit_types import Bytes

from jam.log_setup import logger, setup_logging
from jam.state.state import setup_state
from rockstore import RockStore
from jam.block.block import Block

TRACE_ROOT = Path(__file__).parents[3] / "ext" / "jam-conformance" / "fuzz-reports" / "0.7.0" / "traces"

def fetch_vectors(module: str, pattern: str):
    """
    Fetch jam-conformance trace vectors from timestamped directories.
    module parameter is used for compatibility but jam-conformance has different structure.
    pattern should match JSON files in timestamp directories.
    """
    vectors = []

    files = []

    if not module or not pattern:
        raise ValueError("Must provide module and pattern")

    if pattern == "all":
        files = list(TRACE_ROOT.rglob("*.json"))
    else:
        for timestamp_dir in TRACE_ROOT.glob(module.replace('"', "").replace("'", "")):
            if timestamp_dir.is_dir():
                matched = list(timestamp_dir.glob(pattern.replace('"', "").replace("'", "")))
                files.extend(matched)

    print(f"\nFetched: {len(files)} vectors\n")

    # Process JSON files matching the pattern in each timestamp directory
    for trace_file in files:
        try:
            with open(trace_file, 'r') as f:
                trace_data = json.load(f)

            # Validate trace structure
            if not all(key in trace_data for key in ['pre_state', 'post_state']):
                continue

            # Create descriptive name: timestamp_filename
            name = f"{trace_file.parent.name}_{trace_file.name}"
            vectors.append((name, trace_data))

        except (json.JSONDecodeError, IOError):
            continue
    
    return vectors

RETIRED = [
    "1758819527",
    "1758708840",
    "1758622403",
    "1758622442"
]

FAILURES = [
    "1757422206_00000011.json",
    "1757862468_00000160.json",
    "1757862472_00000160.json",
    "1758621412_00000025.json",
    "1758621498_00000025.json",
    "1758621547_00000032.json",
    "1758636775_00000014.json",
    "1758636819_00000022.json",
    "1758636961_00000018.json",
    "1758637024_00000018.json",
    "1758637136_00000019.json",
    "1758637250_00000016.json",
    "1758637297_00000016.json",
    "1758637363_00000023.json",
    "1758637447_00000061.json",
    "1758637447_00000062.json",
    "1758637485_00000019.json"
]
@pytest.mark.asyncio
async def test_traces(module, pattern, db_path, rpc):
    db_path = db_path
    
    setup_logging(theme="gruvbox", node_name="test")

    count = 0
    passed = 0
    retired = 0
    skipped = 0
    fail = 0
    failed = []
    for name, vector in fetch_vectors(module, pattern):
        module_id = name.split("_")[0]
        count += 1
        if name not in FAILURES:
            # print(">>Skipped", name)
            skipped += 1
            continue

        print(f"\n ⏭️Running test case {name} ...")
        if Path("data/tmp").exists():
            shutil.rmtree("data/tmp")



        if module_id in RETIRED:
            print("!Retired", module_id)
            retired += 1
            continue

        t = time()
        settings = setup_setting(data_path=f"data/tmp/{t}/main", rpc_flag=rpc)
        
        db = RockStore(f"data/tmp/{t}/main")
        post_db = RockStore(f"data/tmp/{t}/post")
        
        if name == "00000000.json" or name == "genesis.json":
            print("Skipping genesis...")
            continue

        # Check if vector has block data for transitions
        block = Block.from_json(vector["block"])

        pre_data = {Bytes.from_json(keyval["key"]):Bytes.from_json(keyval["value"]) for keyval in vector["pre_state"]["keyvals"]}
        state = setup_state(db, pre_data)
        print("SETUP STATE ROOT", state.root.hex())

        logger.info("Starting transition...", len_state=len(pre_data))
        PRE_PI = state.pi
        PRE_BETA = state.beta
        PRE_RHO = state.rho

        # try:
        state.transition(block, False)
        state.settle(block.header.hash())
        print("TRANSITIONED STATE ROOT", state.root.hex(), state.store._updates)
        # except Exception as e:
        #     failed.append((name, str(e)))
        #     print("STATE TRANSITION ERROR OCCURRED", e)

        from deepdiff import DeepDiff
        
        post_data = {Bytes.from_json(keyval["key"]): Bytes.from_json(keyval["value"]) for keyval in vector["post_state"]["keyvals"]}
        post_state = setup_state(post_db, post_data)
        print("POST STATE ROOT", post_state.root.hex())

        try:
            if post_state.pi != state.pi:
                print("MISMATCHED PI")
                print("DIFF\n", DeepDiff(state.pi.to_json(), post_state.pi.to_json(), significant_digits=0, verbose_level=2, view="tree"))
            if post_state.rho != state.rho:
                print("MISMATCHED RHO")
                print("DIFF\n", DeepDiff(state.rho.to_json(), post_state.rho.to_json(), significant_digits=0, verbose_level=2, view="tree"))

            if post_state.beta != state.beta:
                print("MISMATCHED BETA")
                print("DIFF", DeepDiff(state.beta.to_json(), post_state.beta.to_json(), significant_digits=0, verbose_level=2, view="tree"))
        except Exception as e:
            failed.append((name, str(e)))
            print("POST STATE COMPARISON ERROR OCCURRED", e)

        actual = {key.hex(): value.hex() for key, value in state.store._DB.get_all().items()}
        expected = {bytes.fromhex(keyval["key"][2:]).hex(): bytes.fromhex(keyval["value"][2:]).hex() for keyval in vector["post_state"]["keyvals"]}
        value_diff = DeepDiff(actual, expected, significant_digits=0, verbose_level=2, view="tree")
        # assert value_diff == {}, f"\nValue Diff: {name}\nDiff:\n{value_diff.pretty()}"
        for k,v in expected.items():
            if k not in actual:
                print("NEW KEY", k, v)
            elif v != actual[k]:
                print("DIFF: ", k, "\nEXP \t", v, "\nACT \t", actual[k], "\nPRE \t", pre_data[Bytes.fromhex(k)].hex() if Bytes.fromhex(k) in pre_data else None)

        try:
            assert state.root == post_state.root
            assert state.root.hex() == vector["post_state"]["state_root"][2:]
            passed += 1
            print("✅Passed")
        except Exception as e:
            fail += 1
            failed.append((name, str(e)))
            print("❌Failed", type(e), str(e))

    print("\n\n\n")
    print("TOTAL : ", count, "  PASSED : ", passed, "  FAILED : ", fail, " RETIRED : ", retired, " SKIPPED : ", skipped)
    # for k in failed:
    #     print(k[0], "Error : ", k[1], "\n")
