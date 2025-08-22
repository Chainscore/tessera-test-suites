#![no_std]
extern crate alloc;
use alloc::format;
use jam_pvm_common::{
    accumulate::{create_service, set_storage},
    declare_service, Service,
};
use jam_types::*;

pub struct CreateService;
declare_service!(CreateService);

#[inline(always)]
fn le_u64(x: &[u8]) -> u64 {
    let mut b = [0u8; 8];
    b.copy_from_slice(&x[..8]);
    u64::from_le_bytes(b)
}

impl Service for CreateService {
    // Refine just forwards the payload bytes to accumulate.
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
                // Expect: [code_hash:32][code_len:u64][min_item_gas:u64][min_memo_gas:u64]
                if bytes.len() < 56 {
                    let _ = set_storage(b"/last_error", b"ERR:BadPayload");
                    continue;
                }

                // code_hash
                let mut h = [0u8; 32];
                h.copy_from_slice(&bytes[0..32]);
                let code_hash = CodeHash::from(h);

                // code_len
                let code_len: usize = le_u64(&bytes[32..40]) as usize;

                // gas values (use Into to avoid guessing exact newtype)
                let min_item_gas = le_u64(&bytes[40..48]).into();
                let min_memo_gas = le_u64(&bytes[48..56]).into();

                match create_service(&code_hash, code_len, min_item_gas, min_memo_gas) {
                    Ok(new_id) => {
                        // store new_id (u32 LE) so tests can read it back from storage
                        let raw: u32 = new_id.into();
                        let ack = raw.to_le_bytes();
                        let _ = set_storage(b"/last_created", &ack);

                        // Also store success status for debugging
                        let _ = set_storage(b"/last_error", b"OK:Success");

                        // Build commit hash with service creation details
                        let mut msg = [0u8; 32];
                        msg[0..4].copy_from_slice(b"CRTE");
                        msg[4..8].copy_from_slice(&ack); // new service ID
                        msg[8..16].copy_from_slice(&(code_len as u64).to_le_bytes());
                        msg[16..24].copy_from_slice(&le_u64(&bytes[40..48]).to_le_bytes());
                        msg[24..32].copy_from_slice(&le_u64(&bytes[48..56]).to_le_bytes());

                        return Some(Hash::from(msg));
                    }
                    Err(e) => {
                        // persist short human-readable error
                        let s = format!("ERR:{:?}", e);
                        let _ = set_storage(b"/last_error", s.as_bytes());
                    }
                }
            }
        }
        None
    }

    fn on_transfer(_slot: Slot, _id: ServiceId, _items: alloc::vec::Vec<TransferRecord>) {}
}
