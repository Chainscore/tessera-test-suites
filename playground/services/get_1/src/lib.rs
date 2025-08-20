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
    // Forward payload so accumulate can see it
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
            // We'll write the "result" under this scratch key (doesn't touch the original KV)
            let out_key = it.package.as_slice();

            if let Ok(bytes) = it.result {
                // payload = [k_len:u64][k_bytes]
                if bytes.len() < 8 {
                    let _ = set_storage(out_key, b"ERR:BadPayload");
                    continue;
                }
                let k_len = le_u64(&bytes[0..8]) as usize;
                if bytes.len() < 8 + k_len {
                    let _ = set_storage(out_key, b"ERR:Truncated");
                    continue;
                }
                let key: Vec<u8> = bytes[8..8 + k_len].to_vec();

                // READ-ONLY fetch: decode Vec<u8> from typed storage
                match get::<Vec<u8>>(key) {
                    Some(val) => {
                        // Surface it for the test without modifying the original entry
                        let _ = set_storage(out_key, &val);
                    }
                    None => {
                        // Surface a not-found marker
                        let _ = set_storage(out_key, b"ERR:NotFound");
                    }
                }
            } else {
                let _ = set_storage(out_key, b"ERR:NoResult");
            }
        }
        None
    }

    fn on_transfer(_slot: Slot, _id: ServiceId, _items: alloc::vec::Vec<TransferRecord>) {}
}
