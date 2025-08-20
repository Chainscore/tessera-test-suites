#![no_std]
extern crate alloc;

use alloc::format;
use jam_pvm_common::{accumulate::set_storage, declare_service, Service};
use jam_types::*;

pub struct SetStorage;
declare_service!(SetStorage);

#[inline(always)]
fn le_u64(x: &[u8]) -> u64 {
    let mut b = [0u8; 8];
    b.copy_from_slice(&x[..8]);
    u64::from_le_bytes(b)
}

impl Service for SetStorage {
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
        if items.is_empty() {
            // Fallback marker so tests can detect that accumulate actually ran
            let _ = set_storage(b"/echo_set", b"EMPTY");
            return None;
        }

        for it in items {
            if let Ok(bytes) = it.result {
                // payload = [k_len:u64][k_bytes][v_len:u64][v_bytes]
                if bytes.len() < 16 {
                    let _ = set_storage(b"/echo_set", b"ERR:bad_payload");
                    continue;
                }
                let k_len = le_u64(&bytes[0..8]) as usize;
                let need1 = 8 + k_len + 8;
                if bytes.len() < need1 {
                    let _ = set_storage(b"/echo_set", b"ERR:truncated_len");
                    continue;
                }
                let key = &bytes[8..8 + k_len];
                let v_len = le_u64(&bytes[8 + k_len..8 + k_len + 8]) as usize;
                let need2 = need1 + v_len;
                if bytes.len() < need2 {
                    let _ = set_storage(b"/echo_set", b"ERR:truncated_val");
                    continue;
                }
                let val = &bytes[8 + k_len + 8..need2];

                match set_storage(key, val) {
                    Ok(_) => {
                        let _ = set_storage(b"/echo_set", b"OK");
                    }
                    Err(e) => {
                        let _ = set_storage(b"/echo_set", format!("ERR:{:?}", e).as_bytes());
                    }
                }
            }
        }
        None
    }

    fn on_transfer(_slot: Slot, _id: ServiceId, _items: alloc::vec::Vec<TransferRecord>) {}
}
