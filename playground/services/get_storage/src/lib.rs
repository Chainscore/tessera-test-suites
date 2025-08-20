#![no_std]
extern crate alloc;

use alloc::vec::Vec;
use jam_pvm_common::{
    accumulate::{get_storage, set_storage},
    declare_service, Service,
};
use jam_types::*;

pub struct GetStorage;
declare_service!(GetStorage);

#[inline(always)]
fn le_u64(x: &[u8]) -> u64 {
    let mut b = [0u8; 8];
    b.copy_from_slice(&x[..8]);
    u64::from_le_bytes(b)
}

impl Service for GetStorage {
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
                    let _ = set_storage(b"/echo_get", b"ERR:bad_payload");
                    continue;
                }
                let k_len = le_u64(&bytes[0..8]) as usize;
                if bytes.len() < 8 + k_len {
                    let _ = set_storage(b"/echo_get", b"ERR:truncated_key");
                    continue;
                }
                let key = &bytes[8..8 + k_len];

                match get_storage(key) {
                    Some(val) => {
                        // echo the fetched value so tests can observe it
                        let _ = set_storage(b"/echo_get", &val);
                    }
                    None => {
                        let _ = set_storage(b"/echo_get", b"NONE");
                    }
                }
            }
        }
        None
    }

    fn on_transfer(_slot: Slot, _id: ServiceId, _items: alloc::vec::Vec<TransferRecord>) {}
}
