#![no_std]
extern crate alloc;

use alloc::{format, vec::Vec};
use jam_pvm_common::{declare_service, refine::machine, Service};
use jam_types::*;

pub struct MachineService;
declare_service!(MachineService);

#[inline(always)]
fn read_u64_le(x: &[u8]) -> u64 {
    let mut b = [0u8; 8];
    b.copy_from_slice(&x[..8]);
    u64::from_le_bytes(b)
}

impl Service for MachineService {
    fn refine(
        _id: ServiceId,
        payload: WorkPayload,
        _pkg: WorkPackageHash,
        _ctx: RefineContext,
        _auth: CodeHash,
    ) -> WorkOutput {
        // Payload ABI: [pc0: u64 LE][code...]
        let bytes = payload.take();
        if bytes.len() < 9 {
            // need at least 8 for pc0 and 1+ for code
            return b"ERR:InvalidLen".to_vec().into();
        }

        let pc0 = read_u64_le(&bytes[..8]);
        let code = &bytes[8..];

        match machine(code, pc0) {
            Ok(handle) => {
                // Success: 8-byte ACK → [handle u64 LE]
                let mut out = Vec::with_capacity(8);
                out.extend_from_slice(&handle.to_le_bytes());
                out.into()
            }
            Err(e) => {
                // Surface the exact ApiError variant via Debug
                let msg = format!("ERR:{:?}", e);
                msg.into_bytes().into()
            }
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
