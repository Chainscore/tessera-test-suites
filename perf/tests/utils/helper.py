from pathlib import Path
from jam.state.accounts import AccountMetadata


def _artifact(name: str) -> Path:



def create_svc_ch(state, sid: ServiceId, code: bytes):
    ch = Hash.blake2b(code)
    state.delta[sid].service = AccountMetadata(
        code_hash=ch,
        balance=Balance(1_000_000),
        gas_limit=Gas(50_000),
        min_gas=Gas(1_000),
        num_i=Ai(0),
        num_o=Ao(0),
    )
    state.delta[sid].preimages[ch] = Bytes(code)
    state.delta[sid].lookup[LookupTable(hash=ch, length=BlobLength(len(code)))] = Timestamps([state.tau])
    return ch

def operand_from_psir(package, r: WorkExecResult, segments, gas_used, o_bytes=b""):
    # WorkPackageHash := blake2b(package.encode())
    h = OpaqueHash(bytes(Hash.blake2b(package.encode())))

    # ExportsRoot: if you don’t have a helper to compute a real root over `segments`,
    # zero it out (most accumulate code doesn’t read it unless you’re testing exports)
    e = OpaqueHash([0]*32)

    return OperandTuple(
        h = h,
        e = e,
        a = OpaqueHash([0]*32),     # placeholders unless you exercise those paths
        y = OpaqueHash([0]*32),
        g = Uint[64](int(gas_used)),# gas from PsiR (the `u` you got back)
        d = r,                      # WorkExecResult from PsiR
        o = Bytes(o_bytes),         # put the item payload or any witness bytes you want
    )
