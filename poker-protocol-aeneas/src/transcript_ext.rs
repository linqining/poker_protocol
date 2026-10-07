//! Re-export shim for the `#[path]`-included proof modules.
//!
//! `dleq_proof.rs` imports the `CryptoTranscript` trait from
//! `crate::transcript_ext` as it does in its home crate
//! (`poker-protocol-proofs`); the trait itself is defined in and re-exported
//! from `poker-protocol-core`.
pub use poker_protocol_core::CryptoTranscript;
