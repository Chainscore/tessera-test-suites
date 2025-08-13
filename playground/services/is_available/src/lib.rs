#![no_std]
extern crate alloc;

use alloc::vec::Vec;
use jam_pvm_common::{declare_service, refine::is_available, Service};
use jam_types::*;

pub struct IsAvailableService;
declare_service!(IsAvailableService);

impl Service for IsAvailableService {
    fn refine(
        _id: ServiceId,
        payload: WorkPayload,
        _pkg: WorkPackageHash,
        _ctx: RefineContext,
        _auth: CodeHash,
    ) -> WorkOutput {
        let bytes = payload.take();
        if bytes.len() != 32 {
            return b"ERR:InvalidLen".to_vec().into();
        }

        let mut h = [0u8; 32];
        h.copy_from_slice(&bytes[..32]);

        let ok = is_available(&h);
        let out = [if ok { 1u8 } else { 0u8 }];
        Vec::from(out).into()
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
