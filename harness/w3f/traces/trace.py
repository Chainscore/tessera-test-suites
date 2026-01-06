from tsrkit_types import structure, Bytes, TypedVector
from jam.block.block import Block


@structure
class KeyVal:
    key: Bytes[31]
    value: Bytes


@structure
class StateKeyVals:
    state_root: Bytes[32]
    keyvals: TypedVector[KeyVal]


@structure
class Trace:
    pre_state: StateKeyVals
    block: Block
    post_state: StateKeyVals
