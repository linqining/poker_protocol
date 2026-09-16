# Reconstruction soundness

This document is the implementation-facing summary of
`reconstruction_paper.md` and `poker_protocol_lean/SECURITY_RECONSTRUCTION.md`.

## Protocol relation

For canonical cards `cards[i]`, each player publishes one contribution under
the common aggregate key:

```text
contribution[i] = Enc_PKagg(0; v_i)
               OR Enc_PKagg(-cards[i]; v_i).
```

The proof package contains:

1. a cross-key proof for every authenticated residual carrier;
2. a Bayer--Groth proof hiding the residual-carrier-to-slot permutation;
3. one OR proof per canonical slot;
4. a statement-bound context, epoch, prior-state digest, keys and ciphertexts.

The host authenticates the exact residual-carrier vector and enforces cross-player
disjointness. Reconstruction cannot infer those historical state facts from a
digest alone.

## Extraction and semantics

Under component soundness and byte/state refinement, an accepted package
extracts:

- a branch for every canonical slot;
- the contribution randomness for that branch;
- an injective residual-carrier-to-slot mapping;
- exact coverage between negative branches and residual carriers.

Adding verified contributions to the canonical base deck makes a held card
decrypt to identity and leaves every unheld card unchanged. Missing
submissions are no-ops and affect liveness only.

## Implementation and tests

The Rust implementation lives in
`poker-protocol-proofs/src/reconstruction/protocol.rs`; component proofs are
in `cross_key.rs` and `slot_or.rs`. ABI encoding is in `poker-protocol-abi`,
and native dispatch is in `poker_protocol/src/precompile.rs`.

Relevant tests cover honest reconstruction, plaintext semantics, all-cards
removal, statement/proof tampering, context/epoch/state binding, cross-slot
rejection, and randomized proofs without mapping fields.
