//! Peek Service — inner-VM demo (no_std, PolkaVM)
//! refine: machine -> poke -> invoke -> peek -> return bytes
//! accumulate/on_transfer: no-op

#![no_std] // <- Unconditional, the target has no std
extern crate alloc;

use alloc::vec::Vec as AVec;

use jam_pvm_common::{
    declare_service,
    refine::{invoke, machine, peek, poke, zero},
    Service,
};
use jam_types::{
    AccumulateItem,
    CodeHash,
    Hash,
    Option, // jam_types::Option<T>
    RefineContext,
    // types we need explicitly (avoid wildcard to prevent name clashes)
    ServiceId,
    SignedGas,
    Slot,
    TransferRecord,
    WorkOutput,
    WorkPackageHash,
    WorkPayload,
};
// The macro `declare_service!` uses `Some`/`None` unqualified — bring jam_types variants into scope.
use jam_types::Option::{None, Some};

pub struct PeekService;
declare_service!(PeekService);

impl Service for PeekService {
    fn refine(
        _id: ServiceId,
        payload: WorkPayload,
        _package_hash: WorkPackageHash,
        _context: RefineContext,
        _auth_code_hash: CodeHash,
    ) -> WorkOutput {
        // Example: treat payload as the inner VM's code (or look it up via refine::lookup)
        let code: AVec<u8> = payload.as_slice().into();

        // 1) Create inner VM and ensure a page exists
        let vm = machine(&code, 0).expect("vm create failed");
        zero(vm, 0, 1).expect("zero page failed");

        // 2) Poke arguments at an agreed address (0x10000 here)
        let args = payload.take();
        poke(vm, &args, 0x10000).expect("poke failed");

        // 3) Run with a default register set and sufficient gas
        let regs0 = [0u64; 13];
        let (_outcome, _remaining, regs) =
            invoke(vm, SignedGas::from(1_000_000), regs0).expect("invoke failed");

        // Convention: inner program writes [r7 .. r7+r8)
        let (ptr, len) = (regs[7], regs[8]);
        let out = peek(vm, ptr, len).expect("peek failed");

        // Return bytes as WorkOutput without relying on Into inference
        WorkOutput::from(out)
    }

    fn accumulate(_slot: Slot, _id: ServiceId, _items: AVec<AccumulateItem>) -> Option<Hash> {
        None
    }

    fn on_transfer(_slot: Slot, _id: ServiceId, _items: AVec<TransferRecord>) {}
}
