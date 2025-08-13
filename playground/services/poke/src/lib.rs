// #![cfg_attr(any(target_arch = "riscv32", target_arch = "riscv64"), no_std)]
#![no_std]
extern crate alloc;

use alloc::vec::Vec;
use jam_pvm_common::{declare_service, refine::poke, Service};
use jam_types::*;

pub struct PokeService;
declare_service!(PokeService);

#[inline(always)]
fn read_u64_le(x: &[u8]) -> u64 {
    let mut b = [0u8; 8];
    b.copy_from_slice(&x[..8]);
    u64::from_le_bytes(b)
}

impl Service for PokeService {
    fn refine(
        _id: ServiceId,
        payload: WorkPayload,
        _pkg: WorkPackageHash,
        _ctx: RefineContext,
        _auth: CodeHash,
    ) -> WorkOutput {
        let bytes = payload.take();
        if bytes.len() < 8 {
            // not enough for dst; return empty (or b"ERR:InvalidLen" if you prefer)
            return Vec::<u8>::new().into();
        }

        let dst = read_u64_le(&bytes[..8]);
        let data = &bytes[8..];

        if !data.is_empty() {
            // explicitly discard the Result to avoid unused_must_use warning
            let _ = poke(dst, data, data.len() as u64);
        }

        // 16-byte ACK: [dst_le][len_le]
        let mut out = Vec::with_capacity(16);
        out.extend_from_slice(&dst.to_le_bytes());
        out.extend_from_slice(&(data.len() as u64).to_le_bytes());
        out.into()
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
