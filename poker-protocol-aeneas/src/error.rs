//! Re-export shim for the `#[path]`-included proof modules (see
//! `transcript_ext.rs`): the proof sources import `crate::error::…` as they
//! do in their home crate.
pub use poker_protocol_core::VerificationError;
