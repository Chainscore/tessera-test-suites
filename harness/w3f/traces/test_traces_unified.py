"""
Dynamically handles both binary (.bin) and JSON (.json) trace files,
running the appropriate decoding and testing logic based on file type.
"""
import json
import shutil
from pathlib import Path
from typing import Iterator, NamedTuple, Dict, Any, Union
from time import time
import pytest
from deepdiff import DeepDiff
from jam import chain_config
from jam.settings import setup_setting
from jam.log_setup import setup_logging
from jam.state.state import setup_state
from rockstore import RockStore
from jam.block.block import Block
from tsrkit_types import Bytes

# Trace type definitions
from .trace import Trace


TRACE_ROOT = Path(__file__).parents[3] / "ext" / "jam-conformance" / "fuzz-reports" / "0.7.2" / "traces"


class TraceCase(NamedTuple):
    """Normalized trace test case data."""
    id: str  # e.g., "1766243315_8065_00000035"
    file_path: Path
    pre_state: Dict[bytes, bytes]
    block: Block
    post_state: Dict[bytes, bytes]
    expected_root: str  # Hex string without 0x


def load_trace_case(path: Path) -> TraceCase:
    """
    Loads and normalizes a trace file (bin or json) into a TraceCase.
    Raises ValueError on malformed data or unsupported format.
    """
    case_id = f"{path.parent.name}_{path.stem}"

    if path.suffix == ".bin":
        # Decode binary trace using structured types
        trace = Trace.decode(path.read_bytes())
        
        return TraceCase(
            id=case_id,
            file_path=path,
            pre_state={item.key: item.value for item in trace.pre_state.keyvals},
            block=trace.block,
            post_state={item.key: item.value for item in trace.post_state.keyvals},
            expected_root=trace.post_state.state_root.hex()
        )

    elif path.suffix == ".json":
        # Parse JSON and manually construct objects
        with open(path, 'r') as f:
            data = json.load(f)

        if not all(k in data for k in ['pre_state', 'post_state', 'block']):
             raise ValueError("Invalid JSON trace structure: missing top-level keys")

        return TraceCase(
            id=case_id,
            file_path=path,
            pre_state={
                Bytes.from_json(kv["key"]): Bytes.from_json(kv["value"]) 
                for kv in data["pre_state"]["keyvals"]
            },
            block=Block.from_json(data["block"]),
            post_state={
                Bytes.from_json(kv["key"]): Bytes.from_json(kv["value"]) 
                for kv in data["post_state"]["keyvals"]
            },
            expected_root=data["post_state"]["state_root"].replace("0x", "")
        )

    else:
        raise ValueError(f"Unsupported file format: {path.suffix}")


def get_trace_files(module: str, pattern: str) -> Iterator[Path]:
    """Yields paths to trace files matching the criteria."""
    if not module or not pattern:
        return

    # Clean input
    mod_filter = module.strip('"\'')
    pat_filter = pattern.strip('"\'')
    
    # Define search scope
    if pat_filter == "all":
        candidates = TRACE_ROOT.rglob("*")
        # Filter for extensions we support
        files = (p for p in candidates if p.suffix in ('.bin', '.json'))
    else:
        # Search specifically within module dirs
        # If module is glob-like (e.g. "*"), TRACE_ROOT.glob(mod_filter) works
        # If module is exact, it works too.
        candidates = []
        for d in TRACE_ROOT.glob(mod_filter):
            if d.is_dir():
                candidates.extend(d.glob(pat_filter))
        files = candidates

    for path in files:
        if path.is_file() and path.suffix in ('.bin', '.json'):
            yield path


def run_transition_check(case: TraceCase, db_path_base: str, rpc: bool) -> None:
    """
    Executes the validation logic for a single trace case.
    Raises AssertionError if validation fails.
    """
    # 1. Setup isolated environment
    # Use explicit timestamp to avoid collision if running fast cycles
    env_id = f"{int(time() * 1000000)}" 
    work_dir = Path(db_path_base) / env_id
    
    setup_setting(data_path=str(work_dir / "main"), rpc_flag=rpc)
    
    db_main = RockStore(str(work_dir / "main"))
    db_post = RockStore(str(work_dir / "post"))

    try:
        # 2. Setup Pre-State
        state = setup_state(db_main, case.pre_state)
        
        # 3. Apply Transition
        # Spec logic: verify author index constraint
        # if case.block.header.author_index < chain_config.num_validators:
        state.transition(case.block, False, True)
        state.settle(case.block.header.hash())
        
        # 4. Setup Expected Post-State (for deep comparison)
        expected_state = setup_state(db_post, case.post_state)
        
        # 5. Assertions
        # Check sub-roots (pi, rho, beta, gamma)
        for attr in ['pi', 'rho', 'beta', 'gamma']:
            actual_val = getattr(state, attr)
            expect_val = getattr(expected_state, attr)
            if actual_val != expect_val:
                print("COMPONENT: ", attr.upper())
                print("ACT\n", actual_val.to_json())
                print("EXP\n", expect_val.to_json())
                diff = DeepDiff(actual_val.to_json(), expect_val.to_json(),
                              significant_digits=0, verbose_level=2, view="tree")
                print(f"\n⚠️ Mismatched {attr.upper()}:\n{diff}")
        


        actual_kv = {k.hex(): v.hex() for k, v in state.store._DB.get_all().items()}
        expect_kv = {k.hex(): v.hex() for k, v in case.post_state.items()}

        val_diff = DeepDiff(actual_kv, expect_kv, significant_digits=0, verbose_level=2, view="tree")

        if val_diff:
            # Print friendly diff for debugging
            for k, v in expect_kv.items():
                if k not in actual_kv:
                    print(f"❌ Missing Key: {k}")
                elif actual_kv[k] != v:
                    print(f"❌ Value Diff [{k}]:\n   Exp: {v}\n   Act: {actual_kv[k]}")

            print(f"Storage Mismatch in {case.id}")

        # Check State Merkle Root
        if state.root.hex() != case.expected_root:
            raise AssertionError(
                f"Root Mismatch!\nExpected: {case.expected_root}\nActual:   {state.root.hex()}"
            )

    finally:
        # Cleanup
        db_main.flush()
        db_post.flush()
        if work_dir.exists():
            shutil.rmtree(work_dir)


@pytest.mark.asyncio
async def test_traces_unified(module, pattern, db_path, rpc):
    """
    Main test entry point for conformance traces.
    Parses both .bin and .json files dynamically.
    """
    setup_logging(theme="gruvbox", node_name="test")
    
    db_base = db_path or "data/tmp"
    if Path(db_base).exists():
        shutil.rmtree(db_base)
    
    failures = []
    skipped = 0
    passed = 0
    
    # Discovery
    files = list(get_trace_files(module, pattern))
    print(f"\n🔍 Found {len(files)} trace files matching pattern '{pattern}' in '{module}'\n")

    for i, path in enumerate(files):
        if path.name in ("00000000.json", "genesis.json", "genesis.bin"):
            skipped += 1
            print(f"⏩ Skipping {path.name}")
            continue

        try:
            case = load_trace_case(path)
            print(f"🔄 Testing {case.id} ... ", end="", flush=True)
        except Exception as e:
            print("LOADING CASE FAILED", e, path)
            continue

        try:

            run_transition_check(case, db_base, rpc)
            
            print("✅ Passed")
            print("\n\n\n\n\n")
            passed += 1

        except Exception as e:
            print(f"❌ Failed: {e}")
            print("\n\n\n\n\n")
            if len(files) == 1:
                raise e
            failures.append((path.name, str(e)))

    # Final Report
    print("\n" + "="*50)
    print(f"PASSED: {passed} | FAILED: {len(failures)} | SKIPPED: {skipped}")
    print("="*50)
    
    if failures:
        print("\nFailures:")
        print("")
        for name, err in failures:
            print(f" - {name}: {err}")
            print("")
        pytest.fail(f"{len(failures)} test cases failed.")
