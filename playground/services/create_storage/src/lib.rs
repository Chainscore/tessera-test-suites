#![cfg_attr(any(target_arch = "riscv32", target_arch = "riscv64"), no_std)]

extern crate alloc;

use alloc::vec::Vec;
use core::convert::TryFrom;
use jam_pvm_common::{accumulate::set_storage, declare_service, Service};
use jam_types::*;

pub struct HelloService;
declare_service!(HelloService);

fn le_u32(x: u32) -> [u8; 4] {
    x.to_le_bytes()
}

// 32-byte constant key used to store items.len()
const KEY_ITEMS_LEN: [u8; 32] = *b"acc_items_len___________________"; // 12 + 20 = 32

impl Service for HelloService {
    fn refine(
        _id: ServiceId,
        payload: WorkPayload,
        _package_hash: WorkPackageHash,
        _context: RefineContext,
        _auth_code_hash: CodeHash,
    ) -> WorkOutput {
        let mut msg = b"Hello, ".to_vec();
        msg.extend_from_slice(&payload.take());
        msg.extend_from_slice(b"! Welcome to JAM!");
        msg.into()
    }

    fn accumulate(_slot: Slot, _id: ServiceId, items: Vec<AccumulateItem>) -> Option<Hash> {
        // Always write the number of items (even if items is empty)
        set_storage(&KEY_ITEMS_LEN, &le_u32(items.len() as u32))
            .expect("storage write for acc_items_len failed");

        // Optionally also write each successful item under its package hash:
        for it in items {
            if let Ok(data) = it.result {
                // it.package is 32 bytes already (WorkPackageHash)
                set_storage(it.package.as_slice(), &data)
                    .expect("storage write for item package failed");
            }
        }
        None
    }

    fn on_transfer(_slot: Slot, _id: ServiceId, _items: Vec<TransferRecord>) {}
}
