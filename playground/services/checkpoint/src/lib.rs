//! Counter Service - Minimal Version
//!
//! A simple JAM service with minimal operations to avoid runtime errors.

#![cfg_attr(any(target_arch = "riscv32", target_arch = "riscv64"), no_std)]

extern crate alloc;

use jam_pvm_common::{
    accumulate::{checkpoint, set_storage},
    declare_service, Service,
};
use jam_types::*;

pub struct CheckpointDemo;
declare_service!(CheckpointDemo);

impl Service for CheckpointDemo {
    // Pass payload through to accumulation (mode byte).
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
        for it in items {
            if let Ok(bytes) = it.result {
                // bytes[0] is "mode": 0 = normal, 1 = panic after checkpoint
                let mode = bytes.get(0).copied().unwrap_or(0);

                // 1) Write A
                let _ = set_storage(b"pa\x8c+JO\x823\x98\xbc\xf8utw\xcaA\x93\\\\\xd7\xa8\x08\xdc\x16\x04\x17\xf6U\x82\x8d~\x0f", b"one");

                // 2) Take a checkpoint of the current accumulation state
                checkpoint();

                // 3) Write B AFTER the checkpoint
                let _ = set_storage(b"/b", b"two");

                // 4) Optionally crash: any writes after the checkpoint will be rolled back
                if mode == 1 {
                    panic!("boom after checkpoint");
                }
            }
        }
        None
    }

    fn on_transfer(_slot: Slot, _id: ServiceId, _items: alloc::vec::Vec<TransferRecord>) {}
}
