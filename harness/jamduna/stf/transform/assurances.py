from os import stat
from typing import Dict, Tuple
from jam.state.ghost import GhostState
from jam.types.block import Block
from jam.types.extrinsics.assurances import AssurancesExtrinsic
from jam.assurances.assurances import Assurances
from jam.types.protocol.crypto import HeaderHash
from jam.types.state.kappa import Kappa
from jam.types.state.rho import Rho
from jam.types.state.sigma import Sigma
from jam.types.state.tau import Tau
from jam.types.base import Bytes
from jam.state.merkle import StateTrie
from jam.state.state import State, setup_state, set_state
from jam.storage.db.kv import KVStore
from pathlib import Path
from jam.config.logging import logger


def t_kv_pre_state(vector, db):
    
        block = Block.from_json(vector["block"])

        gen_path = Path(__file__).parent / "genesis.json"

        if len(vector["pre_state"]["keyvals"]) != 0:
            trie = StateTrie()
            pre_data = {Bytes(keyval["key"]):Bytes(keyval["value"]) for keyval in vector["pre_state"]["keyvals"]}
            trie.merkelize(pre_data, db)
            state = State(db, trie)
            set_state(state)
        else:
            state = setup_state(GhostState.genesis(genesis_path=gen_path), db)

        return state

def t_kv_post_state(vector, post_db):
    post_data = {Bytes(keyval["key"]): Bytes(keyval["value"]) for keyval in vector["post_state"]["keyvals"]}
    post_trie = StateTrie()
    post_trie.merkelize(post_data, post_db)
    post_state = State(post_db, post_trie)

    return post_state

     

def transform_state(vector_state : dict) -> Sigma:
    """
    Transform the vector state into a GhostState object.
    """
    state = GhostState.genesis()
    state.rho = vector_state.rho
    state.kappa = vector_state.kappa

    return state

def subset_to_compare(state) -> Tuple:
    """
    Pull out only the fields we actually want to assert on
    (validator‐stats and slot in this example).
    """
    return (
        state.rho,
        state.kappa
    )

def transition(state, block):
    _, new_wrs = Assurances.transition(state, block)
    return state
