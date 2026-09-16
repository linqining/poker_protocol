# Reconstruction security appendix

Status: 2026-09-16

## Result

The reconstruction proof publishes one aggregate-key contribution per canonical
slot. For each slot it proves that the plaintext is either zero or the negative
of that slot's canonical card. Every negative branch is tied to an
authenticated owner-readable ciphertext by a shared cross-key Sigma proof, and
Bayer--Groth hides the readable-to-slot permutation.

The Lean entry point is `PokerProtocolLean.Reconstruct.ReconstructProof`.
It composes:

1. readable-card lineage (`ReadableCardProvenance`);
2. the extracted relation and slot semantics (`Reconstruction`);
3. the cross-key Sigma protocol (`ReconstructionJointSigma`);
4. the slot OR protocol (`ReconstructionSlotOr`);
5. production component guarantees and refinements (`ReconstructionSecurity`).

`ReconstructionSecurity.verified_package_semantics` is the composed theorem:
an accepted package yields public validity, exact readable coverage, and
per-slot membership in `{0, -card_i}`. No protocol-specific Lean axiom is
introduced.

## Public Statement

The Rust `ReconstructionStatement` binds:

- application context and prior-state digests;
- a monotonic reconstruction epoch;
- aggregate and owner public keys;
- canonical card points;
- owner-readable ciphertexts;
- canonical-slot contribution ciphertexts.

The host authenticates the readable vector and enforces cross-player
disjointness. Reconstruction proves the cryptographic relation; it cannot
derive historical state from a digest alone.

## Components

For readable `R = Enc_Q(m;r)` and negative contribution
`S = P(-m;v)`, the cross-key proof establishes knowledge of `(sk_Q,v)` in:

```text
Q = sk_Q*g
S.c1 = v*g
sk_Q*R.c1 + v*P = R.c2 + S.c2
``+

This binds the two plaintexts without knowing `DL(R.c1)`.

Each canonical slot uses a two-branch OR proof. The branch and mapping are
witness-only. Lean proves honest acceptance, two-fork extraction, exact
simulation, and the response translation used for perfect HVZK.

Bayer--Groth enters through the production interface: a verified permutation/rerandomization relation is
a permutation and rerandomizers proving that the canonical contributions are a
hidden re-encryption permutation of the negative and zero-padding vectors.

## Computational Boundary

The computational theorem still uses standard assumptions: ElGamal security,
Bayer--Groth completeness/soundness/zero-knowledge, Fiat--Shamir extraction
and simulation in the random-oracle model, canonical subgroup decoding, and
injective serialization/transcript refinement. These are security assumptions
of the implementation components, not unproved Lean lemmas. Once the checked
component guarantees hold, Lean proves the composed reconstruction
semantics.

## Rust--Lean Map

| Rust component | Lean result |
| --- | --- |
| readable lineage | `ReadableCardProvenance.authenticated_prior_hand_yields_user_readable_card` |
| slot semantics | `Reconstruction.corrected_slot_semantics` |
| exact readable coverage | `Reconstruction.removed_iff_has_readable_witness` |
| cross-key proof | `JointSigma.relation_iff_cross_key`, `sigma_complete`, `sigma_speciallySound`, `sigma_perfect_hvzk` |
| slot OR proof | `SlotOr.honest_accepts`, `specially_sound`, `perfect_hvzk_algebraic` |
| composed package | `Security.verified_package_semantics` |

Build and audit:

```bash
cd poker_protocol_lean
lake build PokerProtocolLean
bash scripts/count_sorries.sh
```
