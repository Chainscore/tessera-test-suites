#![no_std]
extern crate alloc;

use alloc::{format, vec::Vec};
use jam_pvm_common::{declare_service, refine::void, Service};
use jam_types::*;

pub struct VoidService;
declare_service!(VoidService);

#[inline(always)]
fn read_u64_le(x: &[u8]) -> u64 {
    let mut b = [0u8; 8];
    b.copy_from_slice(&x[..8]);
    u64::from_le_bytes(b)
}

impl Service for VoidService {
    fn refine(
        _id: ServiceId,
        payload: WorkPayload,
        _pkg: WorkPackageHash,
        _ctx: RefineContext,
        _auth: CodeHash,
    ) -> WorkOutput {
        // Payload: [vm_handle u64][page u64][count u64]  (24 bytes)
        let bytes = payload.take();
        if bytes.len() < 24 {
            return b"ERR:InvalidLen".to_vec().into();
        }

        let handle = read_u64_le(&bytes[0..8]);
        let page = read_u64_le(&bytes[8..16]);
        let count = read_u64_le(&bytes[16..24]);

        match void(handle, page, count) {
            Ok(()) => {
                let mut out = Vec::with_capacity(24);
                out.extend_from_slice(&handle.to_le_bytes());
                out.extend_from_slice(&page.to_le_bytes());
                out.extend_from_slice(&count.to_le_bytes());
                out.into()
            }
            Err(e) => format!("ERR:VOID:{:?}", e).into_bytes().into(),
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
