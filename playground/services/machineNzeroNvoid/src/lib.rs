#![no_std]
extern crate alloc;

use alloc::{format, vec::Vec};
use jam_pvm_common::{
    declare_service,
    refine::{machine, void, zero},
    Service,
};
use jam_types::*;

pub struct VmOpsService;
declare_service!(VmOpsService);

#[inline(always)]
fn le_u64(x: &[u8]) -> u64 {
    let mut b = [0u8; 8];
    b.copy_from_slice(&x[..8]);
    u64::from_le_bytes(b)
}

/// Op codes
const OP_MACHINE: u8 = 0x01; // payload: [1][pc0: u64][code...]
const OP_ZERO: u8 = 0x02; // payload: [2][handle: u64][page: u64][count: u64]
const OP_VOID: u8 = 0x03; // payload: [3][handle: u64][page: u64][count: u64]

impl Service for VmOpsService {
    fn refine(
        _id: ServiceId,
        payload: WorkPayload,
        _pkg: WorkPackageHash,
        _ctx: RefineContext,
        _auth: CodeHash,
    ) -> WorkOutput {
        let bytes = payload.take();
        if bytes.is_empty() {
            return b"ERR:InvalidLen".to_vec().into();
        }

        match bytes[0] {
            // MACHINE
            OP_MACHINE => {
                if bytes.len() < 1 + 8 + 1 {
                    return b"ERR:InvalidLen".to_vec().into();
                }
                let pc0 = le_u64(&bytes[1..9]);
                let code = &bytes[9..];
                match machine(code, pc0) {
                    Ok(handle) => {
                        let mut out = Vec::with_capacity(8);
                        out.extend_from_slice(&handle.to_le_bytes());
                        out.into()
                    }
                    Err(e) => format!("ERR:MACHINE:{:?}", e).into_bytes().into(),
                }
            }

            // ZERO
            OP_ZERO => {
                if bytes.len() < 1 + 8 + 8 + 8 {
                    return b"ERR:InvalidLen".to_vec().into();
                }
                let handle = le_u64(&bytes[1..9]);
                let page = le_u64(&bytes[9..17]);
                let count = le_u64(&bytes[17..25]);

                match zero(handle, page, count) {
                    Ok(()) => {
                        let mut out = Vec::with_capacity(24);
                        out.extend_from_slice(&handle.to_le_bytes());
                        out.extend_from_slice(&page.to_le_bytes());
                        out.extend_from_slice(&count.to_le_bytes());
                        out.into()
                    }
                    Err(e) => format!("ERR:ZERO:{:?}", e).into_bytes().into(),
                }
            }

            // VOID
            OP_VOID => {
                if bytes.len() < 1 + 8 + 8 + 8 {
                    return b"ERR:InvalidLen".to_vec().into();
                }
                let handle = le_u64(&bytes[1..9]);
                let page = le_u64(&bytes[9..17]);
                let count = le_u64(&bytes[17..25]);

                match void(handle, page, count) {
                    Ok(()) => {
                        let mut out = Vec::with_capacity(24);
                        out.extend_from_slice(&handle.to_le_bytes());
                        out.extend_from_slice(&page.to_le_bytes());
                        out.extend_from_slice(&count.to_le_bytes());
                        out.into()
                    }
                    Err(e) => format!("ERR:VOID:{:?}", e).into_bytes().into(),
                }
            }

            _ => b"ERR:BadOp".to_vec().into(),
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
