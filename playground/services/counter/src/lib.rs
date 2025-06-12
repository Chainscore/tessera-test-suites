//! Counter Service - Minimal Version
//! 
//! A simple JAM service with minimal operations to avoid runtime errors.

#![cfg_attr(any(target_arch = "riscv32", target_arch = "riscv64"), no_std)]

extern crate alloc;

use alloc::vec::Vec;
use jam_pvm_common::{declare_service, Service};
use jam_types::*;

/// Counter service - minimal implementation
pub struct CounterService;

// Declare this as a JAM service
declare_service!(CounterService);

impl Service for CounterService {
    /// Refine function - minimal command processing
    fn refine(
        _id: ServiceId,
        payload: WorkPayload,
        _package_hash: WorkPackageHash,
        _context: RefineContext,
        _auth_code_hash: CodeHash,
    ) -> WorkOutput {
        // Get the payload data
        let input_data = payload.take();
        
        // Very simple fixed responses to avoid complex operations
        let response = if input_data.len() >= 3 {
            match &input_data[0..3] {
                b"inc" => b"Incremented".to_vec(),
                b"dec" => b"Decremented".to_vec(),
                b"get" => b"Value: 42".to_vec(),
                _ => b"Unknown".to_vec(),
            }
        } else {
            b"Empty".to_vec()
        };
        
        response.into()
    }
    
    /// Accumulate function - no-op
    fn accumulate(
        _slot: Slot,
        _id: ServiceId,
        _items: Vec<AccumulateItem>
    ) -> Option<Hash> {
        None
    }
    
    /// Transfer function - no-op
    fn on_transfer(
        _slot: Slot,
        _id: ServiceId,
        _items: Vec<TransferRecord>
    ) {
        // No operations
    }
} 