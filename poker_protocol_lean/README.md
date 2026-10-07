# poker_protocol_lean

Lean 4 + Mathlib + VCV-io formalization of the Rust proof systems.

## Reconstruction

The reconstruction entry point is `PokerProtocolLean.Reconstruct.ReconstructProof`.
It composes:

- authenticated residual-carrier lineage;
- the extracted slot relation and aggregate semantics;
- the shared cross-key Sigma protocol;
- the two-branch slot OR protocol;
- the production component/refinement interface and `verified_package_semantics`.

The Lean build contains no protocol-specific axiom. Component security and
implementation refinements enter as explicit verified interfaces; once their
component guarantees hold, the composed theorem derives public validity,
exact residual_carrier coverage, and per-slot plaintext membership.

```bash
lake build PokerProtocolLean
bash scripts/count_sorries.sh
```

The axiom audit is `PokerProtocolLean/Reconstruct/ReconstructionAxiomAudit.lean`.

## Rust→Lean refinement (Aeneas)

`PokerProtocolLean.Aeneas.PKOwnershipRefinement` links the Charon/Aeneas
extraction of the *production* Rust `PKOwnershipProof::verify`
(`poker-protocol-aeneas` compiles `poker-protocol-proofs/src/pk_ownership.rs`
verbatim) to the abstract Σ-protocol above: under an explicit
`BackendSpec` interpretation of the curve backend, acceptance by the
extracted Rust verifier is equivalent to acceptance by the abstract
`GeneralizedSchnorr.sigma` verifier with the extracted Fiat–Shamir
challenge. Assumption boundary, provenance and regeneration:
`AENEAS_REFINEMENT.md`; axiom audit:
`PokerProtocolLean/Aeneas/AeneasAxiomAudit.lean`.
