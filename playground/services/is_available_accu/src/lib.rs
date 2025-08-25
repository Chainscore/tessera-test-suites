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

// Key for storing availability status - matching what the test expects
const KEY_IS_AVAIL_LAST: [u8; 32] = *b"/is_avail/last__________________"; // 14 + 18 = 32

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
        if let Err(_) = set_storage(&KEY_ITEMS_LEN, &le_u32(items.len() as u32)) {
            // If storage write fails, return early - don't panic
            return None;
        }

        let mut processed_count = 0u32;
        let mut last_successful_hash: Option<[u8; 32]> = None;

        // Process each successful item
        for (index, item) in items.iter().enumerate() {
            if let Ok(data) = &item.result {
                if set_storage(item.package.as_slice(), data).is_ok() {
                    processed_count += 1;

                    if let Ok(arr) = <&[u8; 32]>::try_from(item.package.as_slice()) {
                        last_successful_hash = Some(*arr);
                    }

                    // Debug store with index key
                    let mut indexed_key = [0u8; 32];
                    indexed_key[0..4].copy_from_slice(&le_u32(index as u32));
                    indexed_key[4..8].copy_from_slice(b"item");
                    let _ = set_storage(&indexed_key, data);
                }
            }
        }

        // Store the processed count under the availability key
        let availability_data = if processed_count > 0 {
            // Store "available" with count
            let mut avail_data = b"available:".to_vec();
            avail_data.extend_from_slice(&le_u32(processed_count));
            avail_data
        } else {
            b"not_available".to_vec()
        };

        if let Err(_) = set_storage(&KEY_IS_AVAIL_LAST, &availability_data) {
            return None;
        }

        // Also store a simple boolean flag for easy checking
        let simple_flag = if processed_count > 0 { &[1u8] } else { &[0u8] };
        let simple_key = b"is_available____________________"; // 32 bytes
        let _ = set_storage(simple_key, simple_flag);

        // Return the hash of the last successful item, if any
        last_successful_hash.map(|h| Hash::try_from(&h[..]).unwrap_or_else(|_| Hash::default()))
    }

    fn on_transfer(_slot: Slot, _id: ServiceId, _items: Vec<TransferRecord>) {
        // Log transfer events by storing them
        let transfer_count = _items.len() as u32;
        let transfer_key = b"transfer_count__________________"; // 32 bytes
        let _ = set_storage(transfer_key, &le_u32(transfer_count));
    }
}
