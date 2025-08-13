#![no_std]
extern crate alloc;

use alloc::{format, vec::Vec};
use jam_pvm_common::{declare_service, refine::expunge, Service};
use jam_types::*;

pub struct ExpungeService;
declare_service!(ExpungeService);

#[inline(always)]
fn read_u64_le(x: &[u8]) -> u64 {
    let mut b = [0u8; 8];
    b.copy_from_slice(&x[..8]);
    u64::from_le_bytes(b)
}

impl Service for ExpungeService {
    fn refine(
        _id: ServiceId,
        payload: WorkPayload,
        _pkg: WorkPackageHash,
        _ctx: RefineContext,
        _auth: CodeHash,
    ) -> WorkOutput {
        // Payload ABI: [vm_handle: u64 LE]
        let bytes = payload.take();
        if bytes.len() < 8 {
            return b"ERR:InvalidLen".to_vec().into();
        }

        let handle = read_u64_le(&bytes[0..8]);

        match expunge(handle) {
            Ok(final_ic) => {
                // ACK: 16 bytes -> [handle u64][final_ic u64]
                let mut out = Vec::with_capacity(16);
                out.extend_from_slice(&handle.to_le_bytes());
                out.extend_from_slice(&final_ic.to_le_bytes());
                out.into()
            }
            Err(e) => {
                // Surface the exact ApiError variant (e.g., IndexUnknown, OutOfBounds)
                let msg = format!("ERR:{:?}", e);
                msg.into_bytes().into()
            }
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
