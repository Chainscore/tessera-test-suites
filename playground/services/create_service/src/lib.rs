//! Minimal “create service” demo.
//! - refine: echoes payload
//! - accumulate: parses (code_hash, code_len, min_item_gas, min_memo_gas) from the first item,
//!               calls `accumulate::create_service(..)`,
//!               and writes the new ServiceId to storage under a fixed key.

#![cfg_attr(any(target_arch = "riscv32", target_arch = "riscv64"), no_std)]

extern crate alloc;

use alloc::vec::Vec;
use core::convert::TryInto;
use jam_pvm_common::{
    accumulate::{create_service, set_storage},
    declare_service, Service,
};
use jam_types::*; // CodeHash, ServiceId, Hash, (Gas is a type alias here)

struct CreateSvc;
declare_service!(CreateSvc);

#[inline]
fn key32(label: &[u8]) -> [u8; 32] {
    let mut out = [0u8; 32];
    let n = core::cmp::min(32, label.len());
    out[..n].copy_from_slice(&label[..n]);
    out
}

impl Service for CreateSvc {
    fn refine(
        _id: ServiceId,
        payload: WorkPayload,
        _pkg: WorkPackageHash,
        _ctx: RefineContext,
        _auth: CodeHash,
    ) -> WorkOutput {
        // Echo the payload; the test will place params in here.
        payload.take().into()
    }

    fn accumulate(_slot: Slot, _id: ServiceId, items: Vec<AccumulateItem>) -> Option<Hash> {
        let ok_key = key32(b"create_ok");
        let id_key = key32(b"created_service_id");

        // Need one item carrying our params
        let first = if let Some(it) = items.into_iter().next() {
            it
        } else {
            let _ = set_storage(&ok_key, &[0u8]);
            return None;
        };

        // Bytes layout:
        // 0..32  : code_hash (32 bytes)
        // 32..36 : code_len  (u32 LE)
        // 36..44 : min_item_gas (u64 LE)
        // 44..52 : min_memo_gas (u64 LE)
        let bytes = match first.result {
            Ok(b) => b,
            Err(_) => {
                let _ = set_storage(&ok_key, &[0u8]);
                return None;
            }
        };
        if bytes.len() < 52 {
            let _ = set_storage(&ok_key, &[0u8]);
            return None;
        }

        // code_hash
        let mut ch = [0u8; 32];
        ch.copy_from_slice(&bytes[0..32]);
        // Use the 32-byte -> CodeHash ctor your jam_types exposes. `padded` is common.
        let code_hash = CodeHash::padded(&ch);

        // code_len
        let code_len = u32::from_le_bytes(bytes[32..36].try_into().unwrap()) as usize;

        // gas values — just use u64 (Gas is a type alias in your build)
        let min_item_gas: u64 = u64::from_le_bytes(bytes[36..44].try_into().unwrap());
        let min_memo_gas: u64 = u64::from_le_bytes(bytes[44..52].try_into().unwrap());
        // (If you prefer explicit annotation: `let min_item_gas: jam_types::Gas = ...;`)

        match create_service(&code_hash, code_len, min_item_gas, min_memo_gas) {
            Ok(new_id) => {
                // success flag
                let _ = set_storage(&ok_key, &[1u8]);
                // store child id in LE u32 for easy reads in tests
                let id_le = (u32::from(new_id)).to_le_bytes();
                let _ = set_storage(&id_key, &id_le);
            }
            Err(_e) => {
                let _ = set_storage(&ok_key, &[0u8]);
            }
        }

        None
    }

    fn on_transfer(_slot: Slot, _id: ServiceId, _items: Vec<TransferRecord>) {}
}
