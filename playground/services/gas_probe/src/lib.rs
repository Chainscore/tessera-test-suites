#![no_std]
extern crate alloc;
use jam_pvm_common::accumulate::{gas as gas_meter, set_storage};
use jam_pvm_common::{declare_service, Service};
use jam_types::*;

pub struct GasProbe;
declare_service!(GasProbe);

#[inline(always)]
fn le_u64(x: &[u8]) -> u64 {
    let mut b = [0u8; 8];
    b.copy_from_slice(&x[..8]);
    u64::from_le_bytes(b)
}

impl Service for GasProbe {
    // Pass the payload through so accumulate() can see it.
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
            let _ = set_storage(b"/gas/echo", b"EMPTY");
            return None;
        }

        for it in items {
            if let Ok(bytes) = it.result {
                if bytes.len() < 1 {
                    continue;
                }
                // op 0x10 = measure gas; payload = [0x10][iters: u64 LE]
                if bytes[0] != 0x10 || bytes.len() < 1 + 8 {
                    continue;
                }
                let mut iters = le_u64(&bytes[1..9]);
                if iters > 200_000 {
                    iters = 200_000;
                } // safety bound

                let g0: u64 = gas_meter().into();
                // Deterministic work to burn gas
                let mut acc: u64 = 0;
                let mut i: u64 = 0;
                while i < iters {
                    acc = acc.wrapping_add(i ^ acc.rotate_left(5));
                    i += 1;
                }
                let g1: u64 = gas_meter().into();
                let delta = g0.saturating_sub(g1);

                // Optional breadcrumb (not used by test)
                let _ = set_storage(b"/gas/echo", b"OK");

                // Build 32-byte message: b"GASP" + g0 + g1 + delta (all LE)
                let mut msg = [0u8; 32];
                msg[0..4].copy_from_slice(b"GASP");
                msg[4..12].copy_from_slice(&g0.to_le_bytes());
                msg[12..20].copy_from_slice(&g1.to_le_bytes());
                msg[20..28].copy_from_slice(&delta.to_le_bytes());
                msg[28..32].copy_from_slice(&acc.to_le_bytes());

                // Return commitment as Some(Hash)
                // Try one of these alternatives based on your Hash implementation:

                // Option 1: If Hash has a from method
                return Some(Hash::from(msg));

                // Option 2: If Hash is a direct wrapper (uncomment if above fails)
                // return Some(Hash(msg));

                // Option 3: If there's a specific hash constructor (uncomment if above fails)
                // return Some(Hash::new(msg));
            }
        }
        None
    }

    fn on_transfer(_slot: Slot, _id: ServiceId, _items: alloc::vec::Vec<TransferRecord>) {}
}
