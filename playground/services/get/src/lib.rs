#![no_std]
extern crate alloc;

use alloc::vec::Vec;
use jam_pvm_common::{
    accumulate::{get, set_storage},
    declare_service, Service,
};
use jam_types::*;

pub struct GetService;
declare_service!(GetService);

#[inline(always)]
fn le_u64(x: &[u8]) -> u64 {
    let mut b = [0u8; 8];
    b.copy_from_slice(&x[..8]);
    u64::from_le_bytes(b)
}

impl Service for GetService {
    // Pass-through so accumulate sees the raw payload
    fn refine(
        _id: ServiceId,
        payload: WorkPayload,
        _pkg: WorkPackageHash,
        _ctx: RefineContext,
        _auth: CodeHash,
    ) -> WorkOutput {
        payload.take().into()
    }

    fn accumulate(
        _slot: Slot,
        _id: ServiceId,
        items: alloc::vec::Vec<AccumulateItem>,
    ) -> Option<Hash> {
        for it in items {
            if let Ok(bytes) = it.result {
                // payload = [k_len:u64][k_bytes]
                if bytes.len() < 8 {
                    let _ = set_storage(it.package.as_slice(), b"ERR:payload_too_small");
                    continue;
                }
                let k_len = le_u64(&bytes[0..8]) as usize;
                let need = 8 + k_len;
                if bytes.len() < need {
                    let _ = set_storage(it.package.as_slice(), b"ERR:payload_truncated");
                    continue;
                }
                let key = bytes[8..8 + k_len].to_vec();

                // Try to decode stored value as Vec<u8>
                if let Some(val) = get::<Vec<u8>>(key) {
                    let _ = set_storage(it.package.as_slice(), &val); // echo to pkg-hash for the test
                } else {
                    let _ = set_storage(it.package.as_slice(), b"NONE");
                }
            }
        }
        None
    }

    fn on_transfer(_slot: Slot, _id: ServiceId, _items: alloc::vec::Vec<TransferRecord>) {}
}
