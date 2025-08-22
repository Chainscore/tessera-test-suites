#![no_std]
extern crate alloc;

use alloc::format;
use jam_pvm_common::accumulate::{get_storage, set_storage};
use jam_pvm_common::{declare_service, ApiError, Service};
use jam_types::*;

pub struct KvProbe;
declare_service!(KvProbe);

#[inline(always)]
fn le_u64(x: &[u8]) -> u64 {
    let mut b = [0u8; 8];
    b.copy_from_slice(&x[..8]);
    u64::from_le_bytes(b)
}

// Payload ops:
//   0x01 SET: [0x01][k_len: u64][v_len: u64][k][v]
//   0x02 GET: [0x02][k_len: u64][k]
//   0x03 METRIC: [0x03][elapsed_us: u64]  -- value measured in the test and recorded here
impl Service for KvProbe {
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
        if items.is_empty() {
            let _ = set_storage(b"/probe/echo", b"EMPTY");
            return None;
        }

        for it in items {
            if let Ok(bytes) = it.result {
                if bytes.is_empty() {
                    let _ = set_storage(b"/probe/echo", b"ERR:empty");
                    continue;
                }
                match bytes[0] {
                    // -------- SET --------
                    0x01 => {
                        if bytes.len() < 1 + 16 {
                            let _ = set_storage(b"/probe/echo_set", b"ERR:too_small");
                            continue;
                        }
                        let k_len = le_u64(&bytes[1..9]) as usize;
                        let v_len = le_u64(&bytes[9..17]) as usize;
                        let need = 1 + 16 + k_len + v_len;
                        if bytes.len() < need {
                            let _ = set_storage(b"/probe/echo_set", b"ERR:truncated");
                            continue;
                        }
                        let key = &bytes[17..17 + k_len];
                        let val = &bytes[17 + k_len..need];

                        match set_storage(key, val) {
                            Ok(_) => {
                                // Round-trip read to PROVE it’s in the same state
                                match get_storage(key) {
                                    Some(back) if back.as_slice() == val => {
                                        let _ = set_storage(b"/probe/echo_set", b"OK");
                                        let _ = set_storage(b"/probe/roundtrip", &back);
                                    }
                                    Some(back) => {
                                        let _ = set_storage(b"/probe/echo_set", b"ERR:mismatch");
                                        let _ = set_storage(b"/probe/roundtrip", &back);
                                    }
                                    None => {
                                        let _ = set_storage(b"/probe/echo_set", b"ERR:not_found");
                                    }
                                }
                                // Also ack under the package hash for easy external checks
                                let _ = set_storage(it.package.as_slice(), val);
                            }
                            Err(e) => {
                                let tag: &'static [u8] = match e {
                                    ApiError::OutOfBounds => b"ERR:OutOfBounds",
                                    ApiError::IndexUnknown => b"ERR:IndexUnknown",
                                    ApiError::StorageFull => b"ERR:StorageFull",
                                    ApiError::BadCore => b"ERR:BadCore",
                                    ApiError::NoCash => b"ERR:NoCash",
                                    ApiError::GasLimitTooLow => b"ERR:Gas",
                                    ApiError::ActionInvalid => b"ERR:Invalid",
                                    _ => b"ERR:Unknown",
                                };
                                let _ = set_storage(b"/probe/echo_set", tag);
                            }
                        }
                    }

                    // -------- GET --------
                    0x02 => {
                        if bytes.len() < 1 + 8 {
                            let _ = set_storage(b"/probe/echo_get", b"ERR:too_small");
                            continue;
                        }
                        let k_len = le_u64(&bytes[1..9]) as usize;
                        let need = 1 + 8 + k_len;
                        if bytes.len() < need {
                            let _ = set_storage(b"/probe/echo_get", b"ERR:truncated");
                            continue;
                        }
                        let key = &bytes[9..9 + k_len];
                        match get_storage(key) {
                            Some(v) => {
                                let _ = set_storage(b"/probe/echo_get", b"OK");
                                let _ = set_storage(b"/probe/get_value", &v);
                            }
                            None => {
                                let _ = set_storage(b"/probe/echo_get", b"MISS");
                            }
                        }
                    }

                    // -------- METRIC (elapsed_us written by test) --------
                    0x03 => {
                        if bytes.len() < 1 + 8 {
                            let _ = set_storage(b"/metrics/echo", b"ERR:too_small");
                            continue;
                        }
                        let us = le_u64(&bytes[1..9]);
                        let _ = set_storage(b"/metrics/elapsed_us", &u64::to_le_bytes(us));
                        let _ = set_storage(b"/metrics/elapsed_str", format!("{}", us).as_bytes());
                        let _ = set_storage(b"/metrics/echo", b"TIMED");
                    }

                    _ => {
                        let _ = set_storage(b"/probe/echo", b"ERR:op");
                    }
                }
            }
        }
        None
    }

    fn on_transfer(_slot: Slot, _id: ServiceId, _items: alloc::vec::Vec<TransferRecord>) {}
}
