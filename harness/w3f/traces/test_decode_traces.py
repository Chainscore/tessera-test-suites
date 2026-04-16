from .trace import Trace, StateKeyVals
import json
from pathlib import Path
import shutil
from time import time

from jam import chain_config
from jam.settings import setup_setting

import pytest
from tsrkit_types import Bytes

from jam.log_setup import logger, setup_logging
from jam.state.state import setup_state
from rockstore import RockStore
from jam.block.block import Block
from deepdiff import DeepDiff

TRACE_ROOT = Path(__file__).parents[3] / "ext" / "jam-conformance" / "fuzz-reports" / "0.7.2" / "traces"


def fetch_vectors(module: str, pattern: str):
    if not module or not pattern:
        raise ValueError("Must provide module and pattern")

    if pattern == "all":
        files = TRACE_ROOT.rglob("*.bin")
    else:
        files = TRACE_ROOT.glob(f"{module.strip('\"\'')}/{pattern.strip('\"\'')}")

    vectors = [(f"{f.parent.name}_{f.name}", f.read_bytes()) for f in files if f.is_file()]
    print(f"\nFetched: {len(vectors)} vectors\n")
    return vectors

@pytest.mark.asyncio
async def test_decode_traces(module, pattern, db_path, rpc):
    setup_logging(theme="gruvbox", node_name="test")
    for name, vector in fetch_vectors(module, pattern):
        t = time()
        settings = setup_setting(data_path=f"data/tmp/{t}/main")
        
        db = RockStore(f"data/tmp/{t}/main")
        post_db = RockStore(f"data/tmp/{t}/post")

        print(f"\n ⏭️Running test case {name} ...")
        
        trace = Trace.decode(vector)
        state = setup_state(db, {item.key:item.value for item in trace.pre_state.keyvals})

        state.transition(trace.block, False)
        state.settle(trace.block.header.hash())

        post_state = setup_state(post_db, {item.key:item.value for item in trace.post_state.keyvals})

        assert state.root == post_state.root
        assert state.root == trace.post_state.state_root