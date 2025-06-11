//! Hello Service
//! 
//! A simple JAM service that greets users and demonstrates basic functionality.

#![cfg_attr(any(target_arch = "riscv32", target_arch = "riscv64"), no_std)]

extern crate alloc;

use alloc::vec::Vec;
use jam_pvm_common::{declare_service, Service, info};
use jam_types::*;

/// Simple greeting service
pub struct HelloService;

// Declare this as a JAM service
declare_service!(HelloService);

impl Service for HelloService {
    /// Refine function - processes work payload
    /// Prepends "Hello from JAM! " to the input
    fn refine(
        id: ServiceId,
        payload: WorkPayload,
        _package_hash: WorkPackageHash,
        _context: RefineContext,
        _auth_code_hash: CodeHash,
    ) -> WorkOutput {
        info!(target = "hello", "Hello Service Refine, service_id={id:x}h");
        
        // Get the payload data
        let input_data = payload.take();
        
        // Create greeting response
        let greeting = b"Hello from JAM! ";
        let mut result = Vec::with_capacity(greeting.len() + input_data.len());
        result.extend_from_slice(greeting);
        result.extend_from_slice(&input_data);
        
        info!(target = "hello", "Processed {} bytes -> {} bytes", input_data.len(), result.len());
        
        result.into()
    }
    
    /// Accumulate function - integrates refined results into state
    fn accumulate(
        slot: Slot,
        id: ServiceId,
        items: Vec<AccumulateItem>
    ) -> Option<Hash> {
        info!(target = "hello", "Hello Service Accumulate, service_id={id:x}h slot={slot}");
        info!(target = "hello", "Processing {} accumulate items", items.len());
        
        // Log each item for debugging
        for (i, item) in items.iter().enumerate() {
            info!(target = "hello", "Item {}: {} bytes", i, item.payload.len());
        }
        
        // Return None - no state changes needed for this simple service
        None
    }
    
    /// Transfer function - handles incoming transfers
    fn on_transfer(
        slot: Slot,
        id: ServiceId,
        items: Vec<TransferRecord>
    ) {
        info!(target = "hello", "Hello Service Transfer, service_id={id:x}h slot={slot}");
        info!(target = "hello", "Received {} transfers", items.len());
        
        // Log transfer details
        for (i, transfer) in items.iter().enumerate() {
            info!(target = "hello", "Transfer {}: from {} to {} amount {}", 
                  i, transfer.source, transfer.destination, transfer.amount);
        }
    }
} 