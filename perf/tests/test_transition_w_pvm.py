#!/usr/bin/env python3
"""
PVM Performance Benchmarking Tests

Simple profiled tests for JAM PVM performance analysis.
"""

import json
from pathlib import Path
from jam.state.state import State, set_state
from jam.types.block import Block
from rockstore import RockStore
from jam.state.merkle import StateTrie
from tsrkit_types import Bytes
from jam.config.logging import setup_logging, get_logger

from ..tools import Profiler

import dotenv

dotenv.load_dotenv(".env")

# Initialize logging with proper theme and environment
setup_logging(theme="default", environment="testing")
logger = get_logger("perf-tests")

def test_transition_w_pvm(db_path):
    """Test PVM state transition with full PVM execution"""
    
    try:
        vector = json.load(open(Path(__file__).parent.parent.parent / "ext" / "w3f-davxy" / "traces" / "reports-l1" / "00000047.json"))
        db = RockStore(db_path)
        # Initialize state
        trie = StateTrie()
        pre_data = {Bytes.from_json(keyval["key"]):Bytes.from_json(keyval["value"]) for keyval in vector["pre_state"]["keyvals"]}
        trie.merkelize(pre_data, db)
        state = set_state(State(db, trie))
        
        block = Block.from_json(vector["block"])

        with Profiler("transition_w_pvm", limit=30):
            state.transition(block)

        print(f"✅ Processed block #{block.header.slot}")
            
    except ImportError as e:
        logger.error(f"Could not import JAM modules: {e}")
        print(f"❌ Could not import JAM modules: {e}")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"❌ Test failed: {e}")