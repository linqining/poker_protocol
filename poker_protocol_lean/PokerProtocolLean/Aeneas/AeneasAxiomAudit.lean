import PokerProtocolLean.Aeneas.PKOwnershipRefinement

/-!
# Axiom audit for the Rust→Lean refinement deliverable

The commands below report the trusted Lean axioms used by the refinement
results that link the Aeneas-extracted Rust verifier
(`poker_protocol_aeneas.pk_ownership`, extracted from the production
`poker-protocol-proofs/src/pk_ownership.rs`) to the abstract Σ-protocol.

No protocol-specific *propositional* axiom is introduced: the curve
backend enters as the explicit hypothesis structure `BackendSpec`. The
reported axiom dependencies are:

* `propext`, `Classical.choice`, `Quot.sound` — the standard Lean/mathlib
  axioms used throughout this project;
* `poker_protocol_aeneas.rand_core.error.Error`,
  `Aeneas.Std.core.fmt.Formatter` — **opaque type declarations** emitted
  by Aeneas for Rust external types that the extracted trait declarations
  mention (rand-core's error type in `CurveScalar::random`'s bounds, and
  `core::fmt::Formatter` in the derived `Debug` impls). They carry no
  properties: they only inhabit type positions, and no theorem of this
  module assumes anything about their inhabitants.

The Aeneas-extracted model itself carries no propositional axiom: the
probabilistic prover with its untranslatable rejection-sampling loop is
gated out of the extraction crate (`skip-prover` feature), and the
extracted verifier, challenge, and types translate completely.
-/

#print axioms PokerProtocolLean.AeneasPKOwnershipRefinement.extracted_verify_sound
#print axioms PokerProtocolLean.AeneasPKOwnershipRefinement.extracted_verify_complete
#print axioms PokerProtocolLean.AeneasPKOwnershipRefinement.extracted_verify_iff_abstract
#print axioms PokerProtocolLean.AeneasPKOwnershipRefinement.extracted_verify_iff_sigma_verify
