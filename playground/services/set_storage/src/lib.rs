#![no_std]
extern crate alloc;

use jam_pvm_common::accumulate::set_storage;
use jam_pvm_common::{declare_service, Service};
use jam_types::*;

pub struct KvSet;
declare_service!(KvSet);

// We use a super-compact payload: [k_len:u16 LE][v_len:u16 LE][key][value]
#[inline(always)]
fn le_u16(x: &[u8]) -> u16 {
    let mut b = [0u8; 2];
    b.copy_from_slice(&x[..2]);
    u16::from_le_bytes(b)
}

impl Service for KvSet {
    // refine is pass-through so accumulate sees the raw payload
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
        let mut wrote_anything = false;

        for it in items {
            let Ok(bytes) = it.result else { continue };
            if bytes.len() < 4 {
                // too small for 2×u16 header
                let _ = set_storage(b"/echo_set", b"ERR:too_small");
                continue;
            }

            let klen = le_u16(&bytes[0..2]) as usize;
            let vlen = le_u16(&bytes[2..4]) as usize;
            let need = 4 + klen + vlen;
            if bytes.len() < need {
                let _ = set_storage(b"/echo_set", b"ERR:truncated");
                continue;
            }

            let key = &bytes[4..4 + klen];
            let val = &bytes[4 + klen..need];

            match set_storage(key, val) {
                Ok(_prev_len) => {
                    wrote_anything = true;
                    let _ = set_storage(b"/echo_set", b"OK");
                }
                Err(_e) => {
                    // StorageFull or another ApiError — keep it simple
                    let _ = set_storage(b"/echo_set", b"ERR:set_storage");
                }
            }
        }

        if wrote_anything {
            // Return a simple non-zero commitment so the test can assert accumulate ran
            let mut msg = [0u8; 32];
            msg[0..4].copy_from_slice(*b"KVOK");
            return Some(Hash::from(msg));
        }
        None
    }

    fn on_transfer(_slot: Slot, _id: ServiceId, _items: alloc::vec::Vec<TransferRecord>) {}
}
