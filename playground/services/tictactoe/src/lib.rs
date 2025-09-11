//! Tic taTac Toe Service - Ultra Minimal Version
//! 
//! The simplest possible JAM service that takes serialized tictactoe as payload, and fetches current state of game.
//! Whether si winner possible, if winner is already there, if board is invalid or other cases.

#![cfg_attr(any(target_arch = "riscv32", target_arch = "riscv64"), no_std)]

extern crate alloc;

use alloc::vec::Vec;
use core::str;
use jam_pvm_common::{declare_service, Service};
// use jam_pvm_common::accumulate::{get, set};
use jam_types::*;
// use jam_codec::{Encode, Decode};

/// Ultra minimal service
pub struct TicTacToeService;

// Declare this as a JAM service
declare_service!(TicTacToeService);

#[derive(Debug)]
enum GameState {
    Invalid,
    InProgress,
    Draw,
    Winner(u8), // 1 = X, 2 = O
}

impl GameState {
    fn to_message(&self) -> Vec<u8> {
        match self {
            GameState::Invalid => b"Invalid board".to_vec(),
            GameState::InProgress => b"In progress".to_vec(),
            GameState::Draw => b"Draw".to_vec(),
            GameState::Winner(1) => b"X wins".to_vec(),
            GameState::Winner(2) => b"O wins".to_vec(),
            _ => b"Unknown".to_vec(),
        }
    }
}

// #[derive(Debug, Encode, Decode, Default)]
// struct Stats {
//     x_wins: u64,
//     o_wins: u64,
//     draws: u64,
//     invalids: u64,
// }

//  Check the state of a tic-tac-toe board (9 bytes)
fn check_winner(board: &[u8]) -> GameState {
    if board.len() != 9 {
        return GameState::Invalid;
    }

    let x_count = board.iter().filter(|&&c| c == 1).count();
    let o_count = board.iter().filter(|&&c| c == 2).count();

    // validity check
    if o_count > x_count || x_count > o_count + 1 {
        return GameState::Invalid;
    }

    let win_conditions = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8], // rows
        [0, 3, 6], [1, 4, 7], [2, 5, 8], // cols
        [0, 4, 8], [2, 4, 6],            // diagonals
    ];

    let mut winner: Option<u8> = None;
    for line in &win_conditions {
        let [a, b, c] = *line;
        if board[a] != 0 && board[a] == board[b] && board[b] == board[c] {
            if let Some(prev) = winner {
                if prev != board[a] {
                    return GameState::Invalid; // both players can't win
                }
            }
            winner = Some(board[a]);
        }
    }

    if let Some(w) = winner {
        return GameState::Winner(w);
    }

    if board.iter().all(|&c| c != 0) {
        GameState::Draw
    } else {
        GameState::InProgress
    }
}

impl Service for TicTacToeService {
    /// Refine function
    fn refine(
        _id: ServiceId,
        _payload: WorkPayload,
        _package_hash: WorkPackageHash,
        _context: RefineContext,
        _auth_code_hash: CodeHash,
    ) -> WorkOutput {
        let input_data: Vec<u8> = _payload.take();

        let state = check_winner(&input_data);
        state.to_message().into()
    }
    
    /// Accumulate function
    fn accumulate(
        _slot: Slot,
        _id: ServiceId,
        items: Vec<AccumulateItem>
    ) -> Option<Hash> {
        let mut x_wins = 0u64;
        let mut o_wins = 0u64;
        let mut draws  = 0u64;
        let mut invalids = 0u64;

        for item in items {
            if let Ok(output) = item.result {
                let bytes: Vec<u8> = output.into();
                if let Ok(msg) = str::from_utf8(&bytes) {
                    match msg {
                        "X wins"        => x_wins += 1,
                        "O wins"        => o_wins += 1,
                        "Draw"          => draws  += 1,
                        "Invalid board" => invalids += 1,
                        _ => {}
                    }
                }
            }
        }

        let mut summary = Vec::new();
        summary.extend_from_slice(&x_wins.to_le_bytes());
        summary.extend_from_slice(&o_wins.to_le_bytes());
        summary.extend_from_slice(&draws.to_le_bytes());
        summary.extend_from_slice(&invalids.to_le_bytes());

//         Some(Hash::blake2b(&summary))
        return None
    }


    
    /// Transfer function - no-op
    fn on_transfer(
        _slot: Slot,
        _id: ServiceId,
        _items: Vec<TransferRecord>
    ) {
    }
} 
