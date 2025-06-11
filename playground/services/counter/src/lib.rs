//! Counter Service
//! 
//! A JAM service that demonstrates simple counter operations.
//! Commands: "inc", "dec", "get", "reset"

#![cfg_attr(any(target_arch = "riscv32", target_arch = "riscv64"), no_std)]

extern crate alloc;

use alloc::vec::Vec;
use jam_pvm_common::{declare_service, Service, info};
use jam_types::*;

/// Counter service that tracks simple operations
pub struct CounterService;

// Declare this as a JAM service
declare_service!(CounterService);

impl Service for CounterService {
    /// Refine function - processes counter commands
    fn refine(
        id: ServiceId,
        payload: WorkPayload,
        _package_hash: WorkPackageHash,
        _context: RefineContext,
        _auth_code_hash: CodeHash,
    ) -> WorkOutput {
        info!(target = "counter", "Counter Service Refine, service_id={id:x}h");
        
        // Get the payload data
        let input_data = payload.take();
        
        // Simple command processing based on input text
        let response = if input_data.starts_with(b"inc") {
            b"Counter incremented".to_vec()
        } else if input_data.starts_with(b"dec") {
            b"Counter decremented".to_vec()
        } else if input_data.starts_with(b"get") {
            b"Current value: 42".to_vec()
        } else if input_data.starts_with(b"reset") {
            b"Counter reset to 0".to_vec()
        } else {
            let mut result = b"Unknown counter command: ".to_vec();
            result.extend_from_slice(&input_data);
            result
        };
        
        info!(target = "counter", "Processed {} bytes -> {} bytes", input_data.len(), response.len());
        
        response.into()
    }
    
    /// Accumulate function - simple state tracking
    fn accumulate(
        slot: Slot,
        id: ServiceId,
        items: Vec<AccumulateItem>
    ) -> Option<Hash> {
        info!(target = "counter", "Counter Service Accumulate, service_id={id:x}h slot={slot}");
        info!(target = "counter", "Processing {} accumulate items", items.len());
        
        // For this simple demo, we don't need to return state hashes
        // In a real implementation, you would compute and return the state hash
        None
    }
    
    /// Transfer function - handles incoming transfers
    fn on_transfer(
        slot: Slot,
        id: ServiceId,
        items: Vec<TransferRecord>
    ) {
        info!(target = "counter", "Counter Service Transfer, service_id={id:x}h slot={slot}");
        info!(target = "counter", "Received {} transfers", items.len());
        
        // Log transfer details
        for (i, transfer) in items.iter().enumerate() {
            info!(target = "counter", "Transfer {}: from {} to {} amount {}", 
                  i, transfer.source, transfer.destination, transfer.amount);
        }
    }
} 