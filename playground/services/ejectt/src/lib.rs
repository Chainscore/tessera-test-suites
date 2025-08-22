#![no_std]
extern crate alloc;

use alloc::format;
use jam_pvm_common::accumulate::{eject, set_storage};
use jam_pvm_common::{declare_service, Service};
use jam_types::*;

pub struct Ejector;
declare_service!(Ejector);

impl Service for Ejector {
    // refine: pass-through
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
        let mut ran = false;

        for it in items {
            let Ok(bytes) = it.result else { continue };
            if bytes.len() < 1 {
                continue;
            }

            match bytes[0] {
                // [0xE0][target_id: u32 LE][code_hash: 32]
                0xE0 => {
                    ran = true;
                    if bytes.len() < 1 + 4 + 32 {
                        let _ = set_storage(b"/eject_last", b"ERR:payload_short");
                        continue;
                    }
                    let tid = u32::from_le_bytes(bytes[1..5].try_into().unwrap());
                    let target = ServiceId::from(tid);

                    let mut ch_arr = [0u8; 32];
                    ch_arr.copy_from_slice(&bytes[5..37]);
                    let ch = CodeHash::from(ch_arr);

                    match eject(target, &ch) {
                        Ok(()) => {
                            let _ = set_storage(b"/eject_last", b"OK");
                        }
                        Err(e) => {
                            let _ = set_storage(b"/eject_last", format!("ERR:{:?}", e).as_bytes());
                        }
                    }
                }
                _ => { /* ignore */ }
            }
        }

        // simple non-zero commitment if we ran any op
        if ran {
            let mut msg = [0u8; 32];
            msg[0..5].copy_from_slice(b"EJEC\0");
            return Some(Hash::from(msg));
        }
        None
    }

    fn on_transfer(_slot: Slot, _id: ServiceId, _items: alloc::vec::Vec<TransferRecord>) {}
}
