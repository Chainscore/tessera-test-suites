#![cfg_attr(any(target_arch = "riscv32", target_arch = "riscv64"), no_std)]
extern crate alloc;

use alloc::vec::Vec;
use jam_pvm_common::{declare_service, refine::lookup, Service};
use jam_types::*;

pub struct LookupService;
declare_service!(LookupService);

impl Service for LookupService {
    // Payload ABI: [hash: 32 bytes]. Returns the preimage if found, or b"NONE".
    fn refine(
        _id: ServiceId,
        payload: WorkPayload,
        _pkg: WorkPackageHash,
        _ctx: RefineContext,
        _auth: CodeHash,
    ) -> WorkOutput {
        let bytes = payload.take();
        if bytes.len() < 32 {
            return b"ERR:payload_too_small".to_vec().into();
        }
        let mut h = [0u8; 32];
        h.copy_from_slice(&bytes[0..32]);

        match lookup(&h) {
            Some(v) => v.into(),
            None => b"NONE".to_vec().into(),
        }
    }

    fn accumulate(
        _slot: Slot,
        _id: ServiceId,
        _items: alloc::vec::Vec<AccumulateItem>,
    ) -> Option<Hash> {
        None
    }

    fn on_transfer(_slot: Slot, _id: ServiceId, _items: alloc::vec::Vec<TransferRecord>) {}
}
