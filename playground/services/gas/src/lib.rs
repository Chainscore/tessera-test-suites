#![no_std]
extern crate alloc;

use jam_pvm_common::{declare_service, refine::gas, Service};
use jam_types::*;

pub struct GasService;
declare_service!(GasService);

impl Service for GasService {
    fn refine(
        _id: ServiceId,
        _payload: WorkPayload,
        _package_hash: WorkPackageHash,
        _ctx: RefineContext,
        _auth_code_hash: CodeHash,
    ) -> WorkOutput {
        // One gas() call only
        let remaining: u64 = gas();

        // Return as 8 bytes (LE)
        remaining.to_le_bytes().to_vec().into()
    }

    fn accumulate(
        _slot: Slot,
        _id: ServiceId,
        _items: alloc::vec::Vec<AccumulateItem>,
    ) -> Option<Hash> {
        None
    }

    fn on_transfer(_slot: Slot, _id: ServiceId, _items: alloc::vec::Vec<TransferRecord>) {}
}
