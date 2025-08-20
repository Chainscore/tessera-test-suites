// playground/services/peek_into/src/lib.rs
#![cfg_attr(any(target_arch = "riscv32", target_arch = "riscv64"), no_std)]

extern crate alloc;
use alloc::vec;
// use alloc::vec::Vec;
use jam_pvm_common::{declare_service, refine::peek_into, Service};
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
        // payload format: [vm_handle:u64][inner_src:u64][buf_len:u64]
        let bytes = payload.take();
        if bytes.len() < 24 {
            return b"ERR:BadPayload".to_vec().into();
        }

        let vm_handle = u64::from_le_bytes(bytes[0..8].try_into().unwrap());
        let inner_src = u64::from_le_bytes(bytes[8..16].try_into().unwrap());
        let buf_len = u64::from_le_bytes(bytes[16..24].try_into().unwrap()) as usize;

        let mut buf = vec![0u8; buf_len];

        match peek_into(vm_handle, &mut buf[..], inner_src) {
            Ok(()) => buf.into(), // return memory contents
            Err(_) => b"ERR:PeekFailed".to_vec().into(),
        }
    }

    fn accumulate(_slot: Slot, _id: ServiceId, _items: Vec<AccumulateItem>) -> Option<Hash> {
        None
    }

    fn on_transfer(_slot: Slot, _id: ServiceId, _items: Vec<TransferRecord>) {}
}
