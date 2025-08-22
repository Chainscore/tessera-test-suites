//! Minimal service that demonstrates `accumulate::lookup`.
//!
//! Behavior:
//!   - refine: echoes the payload unchanged (so you *can* pass a 32‑byte hash via payload).
//!   - accumulate:
//!       1) Writes `items.len()` under a fixed key (diagnostic).
//!       2) Chooses a `hash_to_lookup`:
//!            - If there is at least one item, it tries to take the first 32 bytes of that item’s result.
//!            - Else, it falls back to the service’s own code hash from `my_info()`.
//!       3) Calls `lookup(hash_to_lookup)`.
//!       4) Stores the lookup result under fixed keys so Python can read them.

#![cfg_attr(any(target_arch = "riscv32", target_arch = "riscv64"), no_std)]

extern crate alloc;

use alloc::vec::Vec;
use core::convert::TryFrom;
use jam_pvm_common::{
    accumulate::{lookup, my_info, set_storage},
    declare_service, Service,
};
use jam_types::*;

struct LookupDemo;
declare_service!(LookupDemo);

fn k32(label: &[u8]) -> [u8; 32] {
    let mut out = [0u8; 32];
    let n = core::cmp::min(32, label.len());
    out[..n].copy_from_slice(&label[..n]);
    out
}

fn write_diag_len(n: usize) {
    let len_key = k32(b"acc_items_len");
    let n_u32 = u32::try_from(n).unwrap_or(u32::MAX);
    let _ = set_storage(&len_key, &n_u32.to_le_bytes());
}

impl Service for LookupDemo {
    fn refine(
        _id: ServiceId,
        payload: WorkPayload,
        _pkg_hash: WorkPackageHash,
        _ctx: RefineContext,
        _auth_code_hash: CodeHash,
    ) -> WorkOutput {
        // Pass through so the caller *may* embed a 32-byte hash in the payload.
        payload.take().into()
    }

    fn accumulate(_slot: Slot, _id: ServiceId, mut items: Vec<AccumulateItem>) -> Option<Hash> {
        // (A) record items.len() so tests can see if items reached accumulate
        write_diag_len(items.len());

        // (B) Decide which hash we’ll lookup
        let mut hash_to_lookup: [u8; 32] = [0u8; 32];

        if let Some(first) = items.pop() {
            if let Ok(data) = first.result {
                // If caller passed a hash via refine result, expect 32 bytes.
                if data.len() >= 32 {
                    hash_to_lookup.copy_from_slice(&data[..32]);
                }
            }
        }

        if hash_to_lookup == [0u8; 32] {
            // Fallback: use our *code hash* so this works even if items are empty.
            // my_info() -> ServiceInfo, whose fields include the code hash.
            let info = my_info(); // docs: jam_pvm_common::accumulate::my_info
                                  // `info` encodes the service account metadata. The code hash field in jam_types is a 32‑byte array.
            hash_to_lookup.copy_from_slice(info.code_hash.as_slice());
        }

        // (C) Do the lookup in our preimage store
        let looked_up = lookup(&hash_to_lookup); // docs: jam_pvm_common::accumulate::lookup

        // (D) Store the outcome under fixed, deterministic keys so tests can assert:
        let key_used = k32(b"lookup_key"); // stores the 32‑byte key we looked up
        let key_found = k32(b"lookup_found"); // stores 1 if Some, 0 if None
        let key_blob = k32(b"lookup_blob"); // stores the preimage bytes if Some

        let _ = set_storage(&key_used, &hash_to_lookup);
        match looked_up {
            Some(bytes) => {
                let _ = set_storage(&key_found, &[1u8]);
                let _ = set_storage(&key_blob, &bytes);
            }
            None => {
                let _ = set_storage(&key_found, &[0u8]);
            }
        }

        None
    }

    fn on_transfer(_slot: Slot, _id: ServiceId, _items: Vec<TransferRecord>) {}
}
