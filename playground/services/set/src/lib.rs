#![no_std]
extern crate alloc;

// use alloc::vec::Vec;
use jam_pvm_common::{
    accumulate::{set, set_storage},
    declare_service, ApiError, Service,
};
use jam_types::*;

pub struct SetService;
declare_service!(SetService);

#[inline(always)]
fn le_u64(x: &[u8]) -> u64 {
    let mut b = [0u8; 8];
    b.copy_from_slice(&x[..8]);
    u64::from_le_bytes(b)
}

impl Service for SetService {
    // Refine passes the payload through so accumulate() can see it.
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
                // payload = [k_len:u64][v_len:u64][k_bytes][v_bytes]
                if bytes.len() < 16 {
                    let _ = set_storage(
                        it.package.as_slice(),
                        b"ERR:payload_too_small" as &'static [u8],
                    );
                    continue;
                }

                let k_len = le_u64(&bytes[0..8]) as usize;
                let v_len = le_u64(&bytes[8..16]) as usize;
                let need = 16 + k_len + v_len;
                if bytes.len() < need {
                    let _ = set_storage(
                        it.package.as_slice(),
                        b"ERR:payload_truncated" as &'static [u8],
                    );
                    continue;
                }

                let key = bytes[16..16 + k_len].to_vec();
                let val = bytes[16 + k_len..need].to_vec();

                match set(key, val.clone()) {
                    Ok(()) => {
                        // Ack the value under the work-package-hash so the test can find it.
                        let _ = set_storage(it.package.as_slice(), &val);
                    }
                    Err(e) => {
                        // Force a single supertype for the match arms: &'static [u8]
                        let tag: &'static [u8] = match e {
                            ApiError::OutOfBounds => b"ERR:OutOfBounds",
                            ApiError::IndexUnknown => b"ERR:IndexUnknown",
                            ApiError::StorageFull => b"ERR:StorageFull",
                            ApiError::BadCore => b"ERR:BadCore",
                            ApiError::NoCash => b"ERR:NoCash",
                            ApiError::GasLimitTooLow => b"ERR:GasLimitTooLow",
                            ApiError::ActionInvalid => b"ERR:ActionInvalid",
                            _ => b"ERR:Unknown",
                        };
                        let _ = set_storage(it.package.as_slice(), tag);
                    }
                }
            }
        }
        None
    }

    fn on_transfer(_slot: Slot, _id: ServiceId, _items: alloc::vec::Vec<TransferRecord>) {}
}
