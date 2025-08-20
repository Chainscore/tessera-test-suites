#![cfg_attr(any(target_arch = "riscv32", target_arch = "riscv64"), no_std)]
extern crate alloc;

// use alloc::vec::Vec;
use jam_pvm_common::{declare_service, refine::is_foreign_available, Service};
use jam_types::*;

pub struct IsForeignAvailable;
declare_service!(IsForeignAvailable);

#[inline(always)]
fn read_u64_le(x: &[u8]) -> u64 {
    let mut b = [0u8; 8];
    b.copy_from_slice(&x[..8]);
    u64::from_le_bytes(b)
}

impl Service for IsForeignAvailable {
    // Refine-only: ABI = [target_sid: u64][hash: 32]
    fn refine(
        _id: ServiceId,
        payload: WorkPayload,
        _pkg: WorkPackageHash,
        _ctx: RefineContext,
        _auth: CodeHash,
    ) -> WorkOutput {
        let bytes = payload.take();
        if bytes.len() < 8 + 32 {
            return b"ERR:InvalidLen".to_vec().into();
        }

        let sid_u64 = read_u64_le(&bytes[0..8]);
        let sid: ServiceId = (sid_u64 as u32).into();

        let mut h = [0u8; 32];
        h.copy_from_slice(&bytes[8..40]);

        let ok = is_foreign_available(sid, &h);
        let v: u64 = if ok { 1 } else { 0 };
        v.to_le_bytes().to_vec().into()
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
