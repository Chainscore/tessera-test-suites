#![cfg_attr(any(target_arch = "riscv32", target_arch = "riscv64"), no_std)]
extern crate alloc;

use alloc::{format, vec, vec::Vec};
use jam_pvm_common::{declare_service, refine::peek_value, Service};
use jam_types::*;

/// PeekValue service: payload ABI
/// [handle: u64 LE][inner_addr: u64 LE][type_tag: u8]
///   type_tag = 1 => u8
///               2 => u16
///               4 => u32
///               8 => u64
///
/// Output:
///   On Ok: raw little-endian bytes of the value (1/2/4/8 bytes)
///   On Err: ASCII "ERR:<VariantName>"
pub struct PeekValueService;
declare_service!(PeekValueService);

#[inline(always)]
fn read_u64_le(x: &[u8]) -> u64 {
    let mut b = [0u8; 8];
    b.copy_from_slice(&x[..8]);
    u64::from_le_bytes(b)
}

impl Service for PeekValueService {
    fn refine(
        _id: ServiceId,
        payload: WorkPayload,
        _pkg: WorkPackageHash,
        _ctx: RefineContext,
        _auth: CodeHash,
    ) -> WorkOutput {
        let bytes = payload.take();
        if bytes.len() < 8 + 8 + 1 {
            return b"ERR:InvalidLen".to_vec().into();
        }

        let handle = read_u64_le(&bytes[0..8]);
        let addr = read_u64_le(&bytes[8..16]);
        let t = bytes[16];

        // Helper to turn ApiResult<T> into Vec<u8> or error-string
        let to_bytes = |res_u8: Result<u8, _>,
                        res_u16: Result<u16, _>,
                        res_u32: Result<u32, _>,
                        res_u64: Result<u64, _>,
                        tag: u8|
         -> Result<Vec<u8>, alloc::string::String> {
            match tag {
                1 => res_u8.map(|v| vec![v]).map_err(|e| format!("{:?}", e)),
                2 => res_u16
                    .map(|v| v.to_le_bytes().to_vec())
                    .map_err(|e| format!("{:?}", e)),
                4 => res_u32
                    .map(|v| v.to_le_bytes().to_vec())
                    .map_err(|e| format!("{:?}", e)),
                8 => res_u64
                    .map(|v| v.to_le_bytes().to_vec())
                    .map_err(|e| format!("{:?}", e)),
                _ => Err("BadType".into()),
            }
        };

        let res = to_bytes(
            peek_value::<u8>(handle, addr),
            peek_value::<u16>(handle, addr),
            peek_value::<u32>(handle, addr),
            peek_value::<u64>(handle, addr),
            t,
        );

        match res {
            Ok(out) => out.into(),
            Err(err) => {
                let msg = format!("ERR:{}", err);
                msg.into_bytes().into()
            }
        }
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
