from jam.types.base.sequences.bytes.byte_array import ByteArray32
from jam.types.base.sequences.bytes.bytes import Bytes

def parse_keyval_state(keyval_raw):
    def _parse(state_raw):
        keyval_state = {}
        for keyval in state_raw["keyvals"]:
            key = ByteArray32(keyval[0])
            val = Bytes(keyval[1])
            keyval_state[key] = val
        print("keyval_state", keyval_state)
        return keyval_state
    return _parse

def transform_block(block_raw):
    # Dummy implementation, replace with your logic
    input_block = block_raw
    args = {}
    return input_block, args