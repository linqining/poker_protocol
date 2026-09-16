# poker_protocol_lean

Lean 4 + Mathlib + VCV-io formalization of the Rust proof systems.

## Reconstruction

The reconstruction entry point is `PokerProtocolLean.Reconstruct.ReconstructProof`.
It composes:

- authenticated readable-card lineage;
- the extracted slot relation and aggregate semantics;
- the shared cross-key Sigma protocol;
- the two-branch slot OR protocol;
- the production component/refinement interface and `verified_package_semantics`.

The Lean build contains no protocol-specific axiom. Component security and
implementation refinements enter as explicit verified interfaces; once their
component guarantees hold, the composed theorem derives public validity,
exact readable coverage, and per-slot plaintext membership.

```bash
lake build PokerProtocolLean
bash scripts/count_sorries.sh
```

The axiom audit is `PokerProtocolLean/Reconstruct/ReconstructionAxiomAudit.lean`.
