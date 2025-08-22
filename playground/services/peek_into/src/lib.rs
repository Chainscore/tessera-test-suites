// playground/services/peek_into/src/lib.rs
#![cfg_attr(any(target_arch = "riscv32", target_arch = "riscv64"), no_std)]

extern crate alloc;

use alloc::vec;
use jam_pvm_common::Service;
use jam_pvm_common::{
    declare_service,
    refine::{machine, peek_into, zero},
};
use jam_types::*;

/// Service to demonstrate peek_into usage.
pub struct PeekIntoService;
declare_service!(PeekIntoService);

impl Service for PeekIntoService {
    fn refine(
        _id: ServiceId,
        payload: WorkPayload,
        _pkg: WorkPackageHash,
        _ctx: RefineContext,
        _auth: CodeHash,
    ) -> WorkOutput {
        let bytes = payload.take();

        // Mode A (back-compat): [handle u64][inner_src u64][buf_len u64] = 24 bytes
        if bytes.len() == 24 {
            let handle = u64::from_le_bytes(bytes[0..8].try_into().unwrap());
            let inner_src = u64::from_le_bytes(bytes[8..16].try_into().unwrap());
            let buf_len = u64::from_le_bytes(bytes[16..24].try_into().unwrap()) as usize;

            let mut buf = vec![0u8; buf_len];
            return match peek_into(handle, &mut buf[..], inner_src) {
                Ok(()) => buf.into(),
                Err(_) => b"ERR:PeekFailed".to_vec().into(),
            };
        }

        // Mode B: create + peek
        // Layout: [pc0 u64][code_len u32][code][inner_src u64][buf_len u64]
        if bytes.len() >= 8 + 4 + 8 + 8 {
            let pc0 = u64::from_le_bytes(bytes[0..8].try_into().unwrap());
            let code_len = u32::from_le_bytes(bytes[8..12].try_into().unwrap()) as usize;

            // ensure we have enough bytes for code + two trailing u64s
            if bytes.len() < 12 + code_len + 16 {
                return b"ERR:BadPayload".to_vec().into();
            }

            let code_end = 12 + code_len;
            let code = &bytes[12..code_end];

            let inner_src = u64::from_le_bytes(bytes[code_end..code_end + 8].try_into().unwrap());
            let buf_len =
                u64::from_le_bytes(bytes[code_end + 8..code_end + 16].try_into().unwrap()) as usize;

            // ✅ FIX: correct argument order — machine(code, pc0)
            let handle = match machine(code, pc0) {
                Ok(h) => h,
                Err(_) => return b"ERR:MachineFailed".to_vec().into(),
            };

            // Ensure the inner memory region exists (allocate/zero required pages).
            if buf_len > 0 {
                let page_size: u64 = 4096;
                let first_page = inner_src / page_size;
                let last_byte = inner_src.saturating_add(buf_len as u64).saturating_sub(1);
                let last_page = last_byte / page_size;
                let count = (last_page - first_page + 1) as u64;
                // Ignore result; if it still fails, peek_into will return an error that we map below.
                let _ = zero(handle, first_page, count);
            }

            let mut buf = vec![0u8; buf_len];
            return match peek_into(handle, &mut buf[..], inner_src) {
                Ok(()) => buf.into(),
                Err(_) => b"ERR:PeekFailed".to_vec().into(),
            };
        }

        b"ERR:BadPayload".to_vec().into()
    }

    fn accumulate(_slot: Slot, _id: ServiceId, _items: Vec<AccumulateItem>) -> Option<Hash> {
        None
    }

    fn on_transfer(_slot: Slot, _id: ServiceId, _items: Vec<TransferRecord>) {}
}
