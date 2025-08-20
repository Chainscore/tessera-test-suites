// playground/services/foreign_lookup_into/src/lib.rs
#![cfg_attr(any(target_arch = "riscv32", target_arch = "riscv64"), no_std)]

extern crate alloc;

use alloc::{vec, vec::Vec};
use jam_pvm_common::{declare_service, refine::foreign_lookup_into, Service};
use jam_types::*;

pub struct ForeignLookupIntoService;
declare_service!(ForeignLookupIntoService);

#[inline(always)]
fn le_u64(x: &[u8]) -> u64 {
    let mut b = [0u8; 8];
    b.copy_from_slice(&x[..8]);
    u64::from_le_bytes(b)
}

impl Service for ForeignLookupIntoService {
    fn refine(
        _id: ServiceId,
        payload: WorkPayload,
        _pkg: WorkPackageHash,
        _ctx: RefineContext,
        _auth: CodeHash,
    ) -> WorkOutput {
        // payload: [sid:u64][buf_len:u64][hash:32]
        let bytes = payload.take();
        if bytes.len() < 48 {
            return b"ERR:BadPayload".to_vec().into();
        }
        let sid_u64 = le_u64(&bytes[0..8]);
        let buf_len = le_u64(&bytes[8..16]) as usize;

        let mut h = [0u8; 32];
        h.copy_from_slice(&bytes[16..48]);

        let sid = ServiceId::from(sid_u64 as u32);

        let mut out = vec![0u8; buf_len];
        match foreign_lookup_into(sid, &h, &mut out[..]) {
            Some(written) => {
                let w = written as usize;
                let mut ack = Vec::with_capacity(8 + w);
                ack.extend_from_slice(&(written as u64).to_le_bytes());
                ack.extend_from_slice(&out[..w]);
                ack.into()
            }
            None => b"NONE".to_vec().into(),
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
