//! Hello Service - Ultra Minimal Version
//!
//! The simplest possible JAM service that just returns empty responses.

#![cfg_attr(any(target_arch = "riscv32", target_arch = "riscv64"), no_std)]

extern crate alloc;

use alloc::vec::Vec;
use jam_pvm_common::{declare_service, Service};
use jam_types::*;

/// Ultra minimal service - returns empty responses
pub struct HelloService;

// Declare this as a JAM service
declare_service!(HelloService);

impl Service for HelloService {
    /// Refine function - returns empty response
    fn refine(
        _id: ServiceId,
        _payload: WorkPayload,
        _package_hash: WorkPackageHash,
        _context: RefineContext,
        _auth_code_hash: CodeHash,
    ) -> WorkOutput {
        let input_data: Vec<u8> = _payload.take();
        let mut message = b"Hello, ".to_vec();
        message.extend(input_data);
        message.extend_from_slice(b"! Welcome to JAM!");
        message.into()
    }
    /// Accumulate function - no-op
    fn accumulate(_slot: Slot, _id: ServiceId, _items: Vec<AccumulateItem>) -> Option<Hash> {
        None
    }

    /// Transfer function - no-op
    fn on_transfer(_slot: Slot, _id: ServiceId, _items: Vec<TransferRecord>) {}
}
