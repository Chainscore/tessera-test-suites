#![no_std]
extern crate alloc;

use alloc::{vec, vec::Vec};
use jam_pvm_common::{declare_service, refine::lookup_into, Service};
use jam_types::*;

pub struct LookupIntoService;
declare_service!(LookupIntoService);

#[inline(always)]
fn le_u64(x: &[u8]) -> u64 {
    let mut b = [0u8; 8];
    b.copy_from_slice(&x[..8]);
    u64::from_le_bytes(b)
}

impl Service for LookupIntoService {
    // ABI: [buf_len: u64 LE][hash: 32]
    fn refine(
        _id: ServiceId,
        payload: WorkPayload,
        _pkg: WorkPackageHash,
        _ctx: RefineContext,
        _auth: CodeHash,
    ) -> WorkOutput {
        let bytes = payload.take();
        if bytes.len() < 8 + 32 {
            return b"ERR:BadPayload".to_vec().into();
        }

        let buf_len = le_u64(&bytes[0..8]) as usize;
        let mut h = [0u8; 32];
        h.copy_from_slice(&bytes[8..40]);

        // Create output buffer of requested size
        let mut out = vec![0u8; buf_len];

        match lookup_into(&h, &mut out) {
            Some(n) => out[..n].to_vec().into(), // return exactly what got written
            None => b"NONE".to_vec().into(),     // preimage not found
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
