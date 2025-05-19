import json
from pathlib import Path
from harness.w3f.pvm.types import PvmTestcase
from jam.execution.pvm.pvm import PVM

PVM_ROOT = Path(__file__).parents[3] / "ext" / "pvm-koute" / "pvm" / "programs"

def fetch_vectors(pattern: str):
    return [
        (f.name, json.load(open(f)))
        for f in PVM_ROOT.glob(pattern)
    ]

def test_pvm_vectors(pattern):
    for name, vector in fetch_vectors(pattern):
        print(f"\n ⏭️Running test case {name} ...")
        tc = PvmTestcase.from_json(vector)
        print("\nProcessing test case: ", tc.name)
        status, pc, gas, registers, memory = PVM.execute(
            bytes(tc.program),
            tc.initial_pc,
            tc.initial_gas,
            tc.initial_regs,
            tc.initial_memory.to_memory(tc.initial_page_map),
        )
        assert pc == tc.expected_pc
        assert status.value.name == tc.expected_status
        assert registers == tc.expected_regs
        assert memory == tc.expected_memory.to_memory(tc.initial_page_map)
        print("✅Passed")