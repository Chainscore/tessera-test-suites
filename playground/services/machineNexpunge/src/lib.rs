#![no_std]
extern crate alloc;

use alloc::{format, vec::Vec};
use jam_pvm_common::{
    declare_service,
    refine::{expunge, machine},
    Service,
};
use jam_types::*;

pub struct SpawnExpungeService;
declare_service!(SpawnExpungeService);

#[inline(always)]
fn read_u64_le(x: &[u8]) -> u64 {
    let mut b = [0u8; 8];
    b.copy_from_slice(&x[..8]);
    u64::from_le_bytes(b)
}

impl Service for SpawnExpungeService {
    fn refine(
        _id: ServiceId,
        payload: WorkPayload,
        _pkg: WorkPackageHash,
        _ctx: RefineContext,
        _auth: CodeHash,
    ) -> WorkOutput {
        // ABI: payload = [pc0: u64 LE] + [inner_code .jam bytes]
        let bytes = payload.take();
        if bytes.len() < 9 {
            return b"ERR:InvalidLen".to_vec().into();
        }

        let pc0 = read_u64_le(&bytes[..8]);
        let code = &bytes[8..];

        // 1) create inner VM
        match machine(code, pc0) {
            Ok(handle) => {
                // 2) delete it immediately; get final instruction counter (ic)
                match expunge(handle) {
                    Ok(final_ic) => {
                        // return 16-byte ACK: [handle u64][final_ic u64]
                        let mut out = Vec::with_capacity(16);
                        out.extend_from_slice(&handle.to_le_bytes());
                        out.extend_from_slice(&final_ic.to_le_bytes());
                        out.into()
                    }
                    Err(e) => format!("ERR:EXPUNGE:{:?}", e).into_bytes().into(),
                }
            }
            Err(e) => format!("ERR:MACHINE:{:?}", e).into_bytes().into(),
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
