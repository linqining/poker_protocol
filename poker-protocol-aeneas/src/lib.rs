//! Charon/Aeneas extraction target for the poker protocol proof suite.
//!
//! This crate exists so that Charon can translate the production
//! sigma-protocol logic without pulling in infrastructure that is out of
//! scope for translation (rayon, merlin transcripts, lazy_static label
//! caches, WASM bindings). The modules below compile the *same source
//! files* as the production crates via `#[path]` includes — there are no
//! copies, so the extracted Lean model cannot drift from the implementation.
//!
//! The `skip-prover` default feature hides the probabilistic provers whose
//! rejection-sampling loops are not translatable; the deterministic
//! verification path (the security-critical direction) is extracted whole.
//!
//! See `scripts/extract_aeneas.sh` for the extraction pipeline and
//! `poker_protocol_lean/PokerProtocolLean/Aeneas/` for the machine-checked
//! refinement statements that consume the generated model.

// The `#[path]` include compiles the production module in this crate; with
// `skip-prover` enabled its RNG imports and error type are expected to go
// unused, and the prover entry points it defines are unreachable here.
#![allow(dead_code, unused_imports)]

#[path = "../../poker-protocol-proofs/src/pk_ownership.rs"]
pub mod pk_ownership;

mod transcript_ext;
mod error;

// Shims so that #[path]-included modules can keep their in-crate paths:
// reconstruction/protocol.rs refers to its siblings via `super::`.
pub(crate) use crate::cross_key::CrossKeyNegationProof;
pub(crate) use crate::slot_or::SlotContributionOrProof;
pub(crate) use crate::slot_or::ContributionBranch;


#[path = "../../poker-protocol-proofs/src/dleq_proof.rs"]
pub mod dleq_proof;

#[path = "../../poker-protocol-proofs/src/reveal_token_proof.rs"]
pub mod reveal_token_proof;

#[path = "../../poker-protocol-proofs/src/remask_proof.rs"]
pub mod remask_proof;

#[path = "../../poker-protocol-proofs/src/leave_proof.rs"]
pub mod leave_proof;

#[path = "../../poker-protocol-proofs/src/reconstruction/cross_key.rs"]
pub mod cross_key;

#[path = "../../poker-protocol-proofs/src/reconstruction/slot_or.rs"]
pub mod slot_or;

#[path = "../../poker-protocol-proofs/src/reconstruction/protocol.rs"]
pub mod protocol;

// BG enters as an EXTERNAL dependency (not #[path]-included): its types
// and proof entry points become opaque external declarations in the
// extracted model (the rand_core precedent), so the reconstruction
// protocol module below can reference them. Rationale: every loop inside
// BayerGrothShuffleProof::verify trips an upstream Aeneas generic
// loop-body signature bug (same root cause as generalized_schnorr), so
// full transparent BG extraction is blocked on the tool; the equation
// checks stay behind that documented boundary.

