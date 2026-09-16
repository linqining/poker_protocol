//! Aggregate-key deck reconstruction proofs.
//!
//! Each player publishes one contribution per canonical slot, proves every
//! readable card's negative plaintext across keys, hides readable placement
//! with Bayer--Groth, and proves each slot is either zero or that slot's
//! negative card. Historical provenance of `user_readable_cards` is
//! authenticated by the outer state digest.

mod cross_key;
mod protocol;
pub(crate) mod slot_or;
#[cfg(test)]
mod tests;

pub use crate::error::VerificationError;
pub use cross_key::CrossKeyNegationProof;
pub use protocol::{
    apply_reconstruction_contributions, canonical_base_deck, ReconstructProof,
    ReconstructionStatement, RECONSTRUCTION_PROOF_LABEL, RECONSTRUCTION_PROOF_VERSION,
};
pub(crate) use slot_or::ContributionBranch;
pub use slot_or::SlotContributionOrProof;
