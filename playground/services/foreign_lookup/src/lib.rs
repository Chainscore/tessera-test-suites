#![cfg_attr(any(target_arch = "riscv32", target_arch = "riscv64"), no_std)]
extern crate alloc;

use jam_pvm_common::{declare_service, refine::foreign_lookup, Service};
use jam_types::*;

pub struct ForeignLookupService;
declare_service!(ForeignLookupService);

#[inline(always)]
fn le_u64(x: &[u8]) -> u64 {
    let mut b = [0u8; 8];
    b.copy_from_slice(&x[..8]);
    u64::from_le_bytes(b)
}

/// Payload: [target_sid:u64][from:u64][len:u64][hash:[u8;32]]
impl Service for ForeignLookupService {
    fn refine(
        _id: ServiceId,
        payload: WorkPayload,
        _pkg: WorkPackageHash,
        _ctx: RefineContext,
        _auth: CodeHash,
    ) -> WorkOutput {
        let bytes = payload.take();
        if bytes.len() < 56 {
            return b"ERR:InvalidLen".to_vec().into();
        }

        let sid_u64 = le_u64(&bytes[0..8]);
        let from = le_u64(&bytes[8..16]) as usize;
        let req_len = le_u64(&bytes[16..24]) as usize;

        let mut h = [0u8; 32];
        h.copy_from_slice(&bytes[24..56]);

        let sid_u32: u32 = match u32::try_from(sid_u64) {
            Ok(v) => v,
            Err(_) => return b"ERR:BadServiceId".to_vec().into(),
        };

        match foreign_lookup(sid_u32 as ServiceId, &h) {
            Some(blob) => {
                if from > blob.len() {
                    return b"ERR:OutOfBounds".to_vec().into();
                }
                let end = core::cmp::min(blob.len(), from.saturating_add(req_len));
                blob[from..end].to_vec().into()
            }
            None => b"ERR:NotFound".to_vec().into(),
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
