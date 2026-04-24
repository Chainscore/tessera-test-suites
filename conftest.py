import shutil
import tempfile
import pytest
import os
import sys
import json
from pathlib import Path

from jam.log_setup import setup_logging

DEV_SPEC = Path(__file__).parent.parent / "dev-spec.json"


# Add tsr-py directory to path for imports if running from tessera-test-suites
if 'tessera-test-suites' in os.getcwd():
    tsr_py_path = Path(os.getcwd()).parent / 'tessera'
    if tsr_py_path.exists() and str(tsr_py_path) not in sys.path:
        sys.path.insert(0, str(tsr_py_path))

# Set up logging environment variables if not already set
if "JAM_LOG_LEVEL" not in os.environ:
    os.environ["JAM_LOG_LEVEL"] = "error"
if "JAM_LOG_LEVEL_BLOCK" not in os.environ:
    os.environ["JAM_LOG_LEVEL_BLOCK"] = "error"
if "JAM_LOG_LEVEL_NODE" not in os.environ:
    os.environ["JAM_LOG_LEVEL_NODE"] = "error"
if "JAM_LOG_LEVEL_NETWORK" not in os.environ:
    os.environ["JAM_LOG_LEVEL_NETWORK"] = "error"
if "JAM_LOG_LEVEL_PVM" not in os.environ:
    os.environ["JAM_LOG_LEVEL_PVM"] = "error"

setup_logging("default", "test")


def _init_jam_node(tmp_path, seed=0, rpc=False, port=40000, rpc_port=19800):
    """Create a minimal JamNode for testing STF vectors."""
    from jam.config import NodeConfig
    from jam.jam_node import JamNode
    from jam.settings import Settings
    from jam.state.state import State
    from jam.block.block import Block
    from jam.api.rpc.service import RPCService
    from jam.block.block_view import BlockView
    from jam.finality.service import FinalityService
    from jam.network.service import NetworkService
    from jam.operations.service import OperatorService

    config = NodeConfig(
        PORT=port,
        RPC_PORT=rpc_port,
        SEED=str(seed),
        DATA_PATH=str(tmp_path) + "/",
        RPC_FLAG=rpc,
        LOG_LEVEL="WARNING",
    )

    node = JamNode(config)
    node._settings = Settings(config)
    node._responder = RPCService(node)
    node._ledger = BlockView(node)
    node._grandpa = FinalityService(node)
    node._ledger.initialize()

    node._router = NetworkService(node)
    node._operator = OperatorService(node)

    # Initialize state from genesis
    from jam.state.state import setup_state
    node.state = setup_state(node, genesis="dev-spec.json")
    node.state.store.enable_writes()
    node.state.store.enable_cache()

    # Save genesis block
    spec = json.loads(DEV_SPEC.read_text())
    block = Block.decode(bytes.fromhex(spec["genesis_header"]))
    block.save(node.settings.main_db)
    node.grandpa.set_head(block)
    node.grandpa.finalise(block, initial=True)

    return node


@pytest.fixture
def db_path():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
async def jam_node(tmp_path):
    """Create a JamNode for tests that need full node infrastructure."""
    node = _init_jam_node(tmp_path)
    try:
        yield node
    finally:
        node.settings.clear()


def pytest_addoption(parser):
    # boolean flag: present -> True
    parser.addoption(
        "--no-rpc",
        action="store_false",
        default=True,
        help="Flag for turning rpc off"
    )

@pytest.fixture
def rpc(request):
    return request.config.getoption("--no-rpc")