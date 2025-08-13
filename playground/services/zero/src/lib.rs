#![no_std]
extern crate alloc;

use alloc::{format, vec::Vec};
use jam_pvm_common::{declare_service, refine::zero, Service};
use jam_types::*;

pub struct ZeroService;
declare_service!(ZeroService);

#[inline(always)]
fn read_u64_le(x: &[u8]) -> u64 {
    let mut b = [0u8; 8];
    b.copy_from_slice(&x[..8]);
    u64::from_le_bytes(b)
}

impl Service for ZeroService {
    fn refine(
        _id: ServiceId,
        payload: WorkPayload,
        _pkg: WorkPackageHash,
        _ctx: RefineContext,
        _auth: CodeHash,
    ) -> WorkOutput {
        // Payload ABI (24 bytes total):
        // [vm_handle: u64 LE][page: u64 LE][count: u64 LE]
        let bytes = payload.take();
        if bytes.len() < 24 {
            return b"ERR:InvalidLen".to_vec().into();
        }

        let vm_handle = read_u64_le(&bytes[0..8]);
        let page = read_u64_le(&bytes[8..16]);
        let count = read_u64_le(&bytes[16..24]);

        match zero(vm_handle, page, count) {
            Ok(()) => {
                // ACK what we zeroed: 24 bytes [vm_handle][page][count]
                let mut out = Vec::with_capacity(24);
                out.extend_from_slice(&vm_handle.to_le_bytes());
                out.extend_from_slice(&page.to_le_bytes());
                out.extend_from_slice(&count.to_le_bytes());
                out.into()
            }
            Err(e) => {
                // Surface the exact ApiError variant (e.g., OutOfBounds)
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
