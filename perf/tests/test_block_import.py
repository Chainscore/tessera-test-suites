import json
from math import floor
import os
import time
import pytest
from pathlib import Path

from tsrkit_types import Bytes
from jam.log_setup import logger, setup_logging
from jam.state.state import setup_state
from jam.block.block import Block
from ..tools import Profiler

import dotenv

dotenv.load_dotenv(".env")


TRACE_ROOT = Path(__file__).parent.parent.parent / "ext" / "w3f-davxy"

def fetch_vector(module: str, pattern: str):
    vector_dir = TRACE_ROOT / "traces" / module
    return [
        (f.name, json.load(open(f)))
        for f in vector_dir.glob(pattern.replace('"', '').replace("'", ""))
    ]

setup_logging("default", "test")

@pytest.mark.asyncio
async def test_traces(db_path):
    db_path = db_path

    from jam.state.state import state as _state
    state = _state

    from jam.settings import setup_setting
    settings = setup_setting(db_path, 1)
    
    module = "safrole"

    counter = 0
    start_block = 1
    n_blocks = 100
    
    w_profiler = False
    
    """
    With Profiler
    #4: 2.05s -> 1.99s -> 1.89s -> 1.36s -> 0.71s
    #8: 4.85s -> 3.34s -> 3.08s -> 1.96s -> 1.25s
    
    Without Profiler
    #4: 1s -> 1.26s -> 1.06s -> 0.52s
    #8: 2.29s -> 2s -> 1.64s -> 1.08s
    
    0-100: 60+s -> 42.92s -> 30s -> 24.36s -> 22.57s
    """
    inspect = 0
    if inspect:
        start_block = 4
        n_blocks = 1
        w_profiler = 0

    total_import_time = 0

    while counter < n_blocks:
        try:
            # Construct the filename with proper zero-padding
            block_num = start_block + counter
            padded_num = f"{block_num:08d}"
            filename = f"{padded_num}.json"
            name, vector = fetch_vector(module, filename)[0]
            print(f"\n ⏭️Running test case {name} ...")
        except IndexError as e:
            block_num = start_block + counter
            padded_num = f"{block_num:08d}"
            filename = f"{padded_num}.json"
            print("Finished!", filename, "not found.")
            break

        if not vector:
            print("No vector found.")
            break
        
        if counter == 0:
            pre_data = {Bytes.from_json(keyval["key"]):Bytes.from_json(keyval["value"]) for keyval in vector["pre_state"]["keyvals"]}
            state = setup_state(settings.state_db, pre_data)
        
        assert state.root.hex() == vector["pre_state"]["state_root"][2:]
        block = Block.from_json(vector["block"])

        logger.info("Starting transition...")
        start_time = time.perf_counter()
        
        if w_profiler:
            with Profiler("block transition", limit=100):
                state._force_transition(block)
        else:
            state._force_transition(block)
            
        end_time = time.perf_counter()
        logger.info(f"Transition took {(1000 * (end_time - start_time)):.2f} ms")
        total_import_time += end_time - start_time

        assert state.root.hex() == vector["post_state"]["state_root"][2:]
        print(f"✅Passed block: {start_block + counter}")
        counter += 1
    
    print(f"Imported {counter} blocks in {total_import_time:.2f} seconds")
    print(f"Average import time: {1000 * total_import_time / counter:.2f} ms block")
    