#![no_std]
extern crate alloc;

use alloc::{format, vec::Vec};
use jam_pvm_common::accumulate::{create_service, gas as gas_meter, get_storage, set_storage};
use jam_pvm_common::{declare_service, Service};
use jam_types::*;

pub struct StorageDemo;
declare_service!(StorageDemo);

#[inline(always)]
fn le_u64(x: &[u8]) -> u64 {
    let mut b = [0u8; 8];
    b.copy_from_slice(&x[..8]);
    u64::from_le_bytes(b)
}

#[inline(always)]
fn le_u32(x: &[u8]) -> u32 {
    let mut b = [0u8; 4];
    b.copy_from_slice(&x[..4]);
    u32::from_le_bytes(b)
}

impl Service for StorageDemo {
    // Refine is pass-through so accumulate sees the raw payload
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
        // Track processed operations (also proves accumulate ran)
        let mut operations_count: u32 = 0;
        if let Some(bytes) = get_storage(b"/operations/count") {
            if bytes.len() >= 4 {
                operations_count = le_u32(&bytes[0..4]);
            }
        }

        for (idx, it) in items.iter().enumerate() {
            if let Ok(bytes) = &it.result {
                operations_count = operations_count.wrapping_add(1);

                // record raw payload for debugging
                let op_key = format!("/operations/item_{}", idx);
                let _ = set_storage(op_key.as_bytes(), bytes);

                if bytes.is_empty() {
                    let _ = set_storage(b"/last_error", b"ERR:EmptyPayload");
                    continue;
                }

                match bytes[0] {
                    // 0x01: set_storage  payload = [0x01][key_len:u8][key][value...]
                    0x01 => {
                        if bytes.len() < 2 {
                            let _ = set_storage(b"/last_error", b"ERR:StorageOpTooShort");
                            continue;
                        }
                        let klen = bytes[1] as usize;
                        if bytes.len() < 2 + klen {
                            let _ = set_storage(b"/last_error", b"ERR:StorageOpBadKeyLen");
                            continue;
                        }
                        let key = &bytes[2..2 + klen];
                        let val = &bytes[2 + klen..];

                        match set_storage(key, val) {
                            Ok(prev) => {
                                let info = format!("OK:Set prev_len:{:?}", prev);
                                let _ = set_storage(b"/last_error", info.as_bytes());
                            }
                            Err(e) => {
                                let info = format!("ERR:set:{:?}", e);
                                let _ = set_storage(b"/last_error", info.as_bytes());
                            }
                        }
                    }

                    // 0x02: get_storage  payload = [0x02][key_len:u8][key]
                    0x02 => {
                        if bytes.len() < 2 {
                            let _ = set_storage(b"/last_error", b"ERR:ReadOpTooShort");
                            continue;
                        }
                        let klen = bytes[1] as usize;
                        if bytes.len() < 2 + klen {
                            let _ = set_storage(b"/last_error", b"ERR:ReadOpBadKeyLen");
                            continue;
                        }
                        let key = &bytes[2..2 + klen];
                        match get_storage(key) {
                            Some(v) => {
                                let _ = set_storage(b"/last_retrieved", &v);
                                let info = format!("OK:Get {} bytes", v.len());
                                let _ = set_storage(b"/last_error", info.as_bytes());
                            }
                            None => {
                                let _ = set_storage(b"/last_retrieved", b"");
                                let _ = set_storage(b"/last_error", b"OK:KeyNotFound");
                            }
                        }
                    }

                    // 0x10: create_service
                    // payload = [0x10][code_hash:32][code_len:u64][min_item_gas:u64][min_memo_gas:u64]
                    0x10 => {
                        if bytes.len() < 1 + 32 + 8 + 8 + 8 {
                            let _ = set_storage(b"/last_error", b"ERR:CreateServiceBadPayload");
                            continue;
                        }
                        let mut code_hash_bytes = [0u8; 32];
                        code_hash_bytes.copy_from_slice(&bytes[1..33]);
                        let ch = CodeHash::from(code_hash_bytes);
                        let code_len = le_u64(&bytes[33..41]) as usize;
                        let min_item_gas = le_u64(&bytes[41..49]).into();
                        let min_memo_gas = le_u64(&bytes[49..57]).into();

                        match create_service(&ch, code_len, min_item_gas, min_memo_gas) {
                            Ok(new_sid) => {
                                let raw: u32 = new_sid.into();
                                let _ = set_storage(b"/last_created_service", &raw.to_le_bytes());
                                // bump a counter for created services
                                let mut count = 0u32;
                                if let Some(b) = get_storage(b"/services_created_count") {
                                    if b.len() >= 4 {
                                        count = le_u32(&b[0..4]);
                                    }
                                }
                                count = count.wrapping_add(1);
                                let _ =
                                    set_storage(b"/services_created_count", &count.to_le_bytes());
                                let _ = set_storage(b"/last_error", b"OK:ServiceCreated");
                            }
                            Err(e) => {
                                let info = format!("ERR:create:{:?}", e);
                                let _ = set_storage(b"/last_error", info.as_bytes());
                            }
                        }
                    }

                    // 0xFF: status / gas() sanity
                    0xFF => {
                        let g0: u64 = gas_meter().into();
                        let _ = set_storage(b"/status_ops", &operations_count.to_le_bytes());
                        let g1: u64 = gas_meter().into();
                        let mut msg = [0u8; 16];
                        msg[0..8].copy_from_slice(&g0.to_le_bytes());
                        msg[8..16].copy_from_slice(&g1.to_le_bytes());
                        let _ = set_storage(b"/status_gas_probe", &msg);
                        let _ = set_storage(b"/last_error", b"OK:Status");
                    }

                    _ => {
                        let info = format!("ERR:UnknownOp:0x{:02X}", bytes[0]);
                        let _ = set_storage(b"/last_error", info.as_bytes());
                    }
                }
            }
        }

        // persist operation count
        let _ = set_storage(b"/operations/count", &operations_count.to_le_bytes());

        // Return a simple 32-byte commitment so Python can assert non-None
        if operations_count > 0 {
            let mut msg = [0u8; 32];
            msg[0..4].copy_from_slice(b"STOR");
            msg[4..8].copy_from_slice(&operations_count.to_le_bytes());
            // include created-services count if present
            let mut created = 0u32;
            if let Some(b) = get_storage(b"/services_created_count") {
                if b.len() >= 4 {
                    created = le_u32(&b[0..4]);
                }
            }
            msg[8..12].copy_from_slice(&created.to_le_bytes());
            // cheap filler
            let filler = operations_count.wrapping_mul(0x1234567);
            msg[12..16].copy_from_slice(&filler.to_le_bytes());
            return Some(Hash::from(msg));
        }

        None
    }

    fn on_transfer(_slot: Slot, _id: ServiceId, _items: alloc::vec::Vec<TransferRecord>) {}
}
