#![no_std]

use jam_pvm_common::ApiError;

#[repr(u32)]
#[derive(Copy, Clone, Debug, Eq, PartialEq)]
pub enum PokeStatus {
    Ok = 0,
    Error = 1,
}

#[repr(u32)]
#[derive(Copy, Clone, Debug, Eq, PartialEq)]
pub enum PokeError {
    None = 0,
    Unknown = 1,
    OutOfBounds = 2,
    IndexUnknown = 3,
    StorageFull = 4,
    BadCore = 5,
    NoCash = 6,
    GasLimitTooLow = 7,
    ActionInvalid = 8,
}

impl From<PokeStatus> for u32 {
    #[inline]
    fn from(s: PokeStatus) -> u32 {
        s as u32
    }
}
impl From<PokeError> for u32 {
    #[inline]
    fn from(e: PokeError) -> u32 {
        e as u32
    }
}

impl From<ApiError> for PokeError {
    #[inline]
    fn from(e: ApiError) -> Self {
        match e {
            ApiError::OutOfBounds => PokeError::OutOfBounds,
            ApiError::IndexUnknown => PokeError::IndexUnknown,
            ApiError::StorageFull => PokeError::StorageFull,
            ApiError::BadCore => PokeError::BadCore,
            ApiError::NoCash => PokeError::NoCash,
            ApiError::GasLimitTooLow => PokeError::GasLimitTooLow,
            ApiError::ActionInvalid => PokeError::ActionInvalid,
            _ => PokeError::Unknown,
        }
    }
}
