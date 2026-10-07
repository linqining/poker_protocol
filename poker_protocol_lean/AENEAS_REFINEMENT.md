# Machine-checked Rust→Lean refinement (Aeneas pilot)

Status: 2026-10-07 — pilot for `PKOwnershipProof::verify`.

## What is proved

The production file `poker-protocol-proofs/src/pk_ownership.rs` is compiled
**verbatim** (no copies) by the extraction crate `poker-protocol-aeneas`
through a `#[path]` include, translated to Lean by
Charon (`--preset=aeneas`) + Aeneas (`-backend lean`), and linked to the
abstract Σ-protocol formalization (`PokerProtocolLean.PKOwnership`, the
`n = 1` case of `GeneralizedSchnorr`, for which perfect completeness,
special soundness, and perfect HVZK are already proved).

Aeneas's translation carries a machine-checked backward-simulation proof
against the Rust MIR semantics, so the extracted model
(`PokerProtocolLean/Aeneas/Generated.lean`) is provably a refinement of the
shipped Rust code — the previously fixture-only Rust↔Lean link
(`RefinementVectors.lean`, which explicitly disclaims verifying Rust bytes)
is now a theorem for this protocol component.

Entry point: `PokerProtocolLean.Aeneas.PKOwnershipRefinement`

- `BackendSpec` — explicit hypothesis record interpreting the concrete
  curve backend in the abstract group/field (totality of the ops, module
  laws, equality reflection). **No protocol-specific axiom.**
- `extracted_verify_sound` — extracted Rust verifier accepts ⇒ the
  extracted Fiat–Shamir `challenge` returned `ok e` and the abstract
  Schnorr equation `response • g = commitment + e • pk` holds.
- `extracted_verify_complete` — abstract equation + a challenge produced
  by the extracted transcript ⇒ the extracted Rust verifier accepts.
- `extracted_verify_iff_sigma_verify` — acceptance by the extracted Rust
  verifier ⟺ acceptance by the abstract `GeneralizedSchnorr.sigma`
  verifier with the extracted challenge. The abstract special-soundness
  theorem therefore applies to accepting transcripts of the shipped code.

## Assumption boundary (what is *not* proved here)

1. `BackendSpec` — the curve backend algebra. This is the axiomatization
   boundary for `curve25519-dalek`/`halo2curves`/`k256`/`starknet-crypto`
   implementations behind the `Curve`/`CurvePoint`/`CurveScalar` traits.
2. The Fiat–Shamir transcript — modeled as the abstract challenge oracle
   (same boundary as the rest of the Lean formalization).
3. The probabilistic prover (`try_prove`/`prove`) is out of scope: its
   rejection-sampling `loop` has no syntactic termination measure, so it
   is gated out of the extraction crate (`skip-prover` feature). The
   verification path — the security-critical direction — is extracted
   completely. Production builds never enable that feature.
4. Axiom audit (`PokerProtocolLean/Aeneas/AeneasAxiomAudit.lean`): besides
   the standard `propext`/`Classical.choice`/`Quot.sound`, the theorems
   mention two **opaque type declarations** emitted by Aeneas for
   unmodelled external Rust types (`rand_core.error.Error`,
   `core.fmt.Formatter`). They carry no properties.

## Provenance / regeneration

- Extraction tooling: Aeneas release `nightly-2026.10.07-aa66752`
  (bundles `charon`, `charon-driver`, `aeneas`); Rust toolchain
  `nightly-2026-08-18` (pinned in `poker-protocol-aeneas/rust-toolchain.toml`).
- The Aeneas Lean runtime library is vendored at `vendor/aeneas`
  (trimmed to `Aeneas` + `AeneasMeta`), repinned from mathlib `v4.31.0`
  to `v4.32.0` to match this project; the port touches nine files and
  every change is commented inline.
- Regenerate the extracted model:

  ```sh
  AENEAS_HOME=/path/to/aeneas-release scripts/extract_aeneas.sh
  cd poker_protocol_lean && lake build PokerProtocolLean && bash scripts/count_sorries.sh
  ```

  The script fails if the generated model contains `sorry` (partial
  extraction). The committed `Generated.lean` is the verbatim script
  output (plus the two auditable field renames documented in the script).

## Known tooling deltas (documented deviations)

- The `#[cfg(not(feature = "skip-prover"))]` gates on
  `try_prove`/`prove` in `pk_ownership.rs`: zero behavior change in
  production (feature never enabled outside the extraction crate).
- Aeneas emits duplicate field names for the `Clone`/`Debug` supertrait
  clauses of `CurvePoint::Compressed`; the extraction script renames the
  two unreferenced duplicates (see step 3 of `scripts/extract_aeneas.sh`).

## Protocol change: fail-closed zero-challenge handling (2026-10-07)

The three Fiat--Shamir retry loops (`challenge_nonzero` in
`poker-protocol-bg/proof.rs`, `reconstruction/slot_or.rs`,
`reconstruction/cross_key.rs`) were replaced by single-derivation +
fail-closed rejection (new `VerificationError::ZeroChallenge`):

* soundness unchanged (strictly stronger: the verifier rejects more);
* completeness becomes statistical: failure probability 1/|Scalar| ~2^-250
  (the Lean statements for the affected components should carry this
  negligible exception instead of `PerfectlyComplete`);
* for every nonzero derivation — the only case observable without
  breaking the hash — transcript bytes are **identical** to the previous
  retrying implementation, so existing proofs and fixtures are unaffected;
* verification becomes straight-line (no loop), removing the structural
  Aeneas blocker for the shuffle/reconstruction extraction;
* **compatibility note**: the on-chain Move verifier (outside this repo)
  and any external reimplementation should adopt the same rule; since no
  constructible transcript derives a zero challenge, the divergence is
  unreachable in practice.

## DLEq status: prepared, blocked by two Aeneas upstream limitations

Production side is fully prepared (behavior-identical, 114/114 tests):
`skip-prover` gates on `try_prove`/`prove` (rejection-sampling loop),
`dleq_reject_log!` macro no-opped in extraction builds (`skip-tracing`
feature; the expanded `tracing` macro pulls dynamic callsite registration
that Aeneas cannot translate and poisons the whole crate), flag+break
loops instead of returns-inside-loops, and index loops in
`append_dleq_context`.

Extraction still fails on Aeneas nightly-2026.10.07 with:
1. `The input arguments don't have the proper type` on the
   `DLEqProofKind` impls (interior `static LABELS` with `&'static [u8]`
   fields);
2. an internal `Unreachable` on `append_dleq_context` (isolated probes
   passed for: `&mut impl CryptoTranscript` args, range loops mutating
   the transcript, and iteration over `&[C::Point]` individually — the
   failure is specific to their combination in this function).

Both are upstream issues (AeneasVerif/aeneas). Follow-up experiments
(2026-10-07, second session):

* Alternate nightlies do not help: 2026.09.25 and 2026.10.06 fail with
  byte-identical signatures.
* Blocker 1 root cause confirmed and SOLVED experimentally: the problem is
  *associated-type arguments in trait-decl methods* (`&C::Point` refs were
  irrelevant — value parameters fail identically). Replacing `compute_d2`
  with a `subtracts_input() -> bool` direction flag (subtraction moved to
  the call site) eliminates that error class entirely.
* Blocker 2 root cause refined: ANY `&[u8]` slice reference flowing as a
  trait-dict VALUE fails (`&'static` is irrelevant): struct fields holding
  `&'static [u8]`, `labels()` returning the struct by value, inlined
  literal structs, and per-label methods returning `&'static [u8]` byte
  literals ALL hit `Unreachable`/"no bottoms". Only inline byte literals
  at *direct call sites* translate (probe-verified).
* The `DLEqKind` design (fourth) WORKS — DLEq now extracts cleanly and is
  part of the committed generated model (2026-10-07, third session):
  - `DLEqProofKind` reduced to `kind() -> DLEqKind` (plain enum) +
    `validates_output_ciphertexts() -> bool`; `DLEqProofLabels` and
    `compute_d2` are gone from the trait surface.
  - `append_dleq_context` matches on the kind inline at every transcript
    call, passing byte literals directly (the only supported shape), and
    uses index loops.
  - verify: flag+break loops (no returns inside loops), the per-card
    d2 direction is a hoisted ±1 scalar (`d2 = (out - in) * sign`; any
    value-producing branch inside a loop is a context-join failure), and
    the per-card-commitment identity check is folded into the main
    validation loop (a standalone loop over the `Vec` struct field trips
    the generic-loop-body `type_var_id` bug).
  All rewrites are behavior-preserving (same acceptance conditions;
  transcript bytes unchanged); tests pass workspace-wide and the
  generated model builds in Lean with zero sorry. The extraction crate keeps
`dleq_proof` commented out until then, so `scripts/extract_aeneas.sh`
stays green and the committed model remains pk_ownership-only.

## Reconstruction rollout: FINAL STATE (2026-10-07, fourth session)

All four reconstruction components are in the committed generated model,
zero sorry, Lean build green:

| Component | Mode | Definitions |
|---|---|---|
| `cross_key.rs` | transparent | 10 |
| `slot_or.rs` | transparent | 29 |
| `reconstruction/protocol.rs` (`verify_inner` chain) | transparent | 60 |
| `poker-protocol-bg` (Bayer-Groth) | external-dependency boundary | types/signatures referenced (30 mentions) |

Plus the earlier modules: pk_ownership (7), dleq_proof (53),
reveal_token_proof (25), remask/leave production functions (1+1).
Total generated model: 221 top-level definitions, 5748 lines.

Documented boundaries (production behavior unchanged, tests 297/297):

1. **Bayer-Groth equation checks** enter as an external opaque boundary:
   every loop inside `BayerGrothShuffleProof::verify` trips an upstream
   Aeneas generic loop-body SIGNATURE bug (`type_var` lost in the
   generated `_loop.body` auxiliary; the loop bodies themselves translate
   cleanly). The BG crate is therefore a plain dependency of the
   extraction crate (not `#[path]`-included): its types and verify entry
   point are referenced as opaque externals — protocol's extracted
   `verify_inner` calls them through that boundary.
2. **Deck-shape checks in `ReconstructionStatement::validate`**
   (identity + pairwise-uniqueness of cards) are cfg-gated out of
   extraction builds: every loop shape there trips the same bug family.
   They are non-cryptographic shape checks; the security content
   (cross-key, slot-OR, BG equations) is extracted.
3. Provers everywhere gated (`skip-prover`); staged-timing
   `verify_with_profile`/`prove_with_profile` restored verbatim (also
   gated) so benchmark harnesses are unaffected; `verify_inner` is the
   timing-free extraction target with identical acceptance behavior.

New Aeneas shape findings from this session (all documented in the
sources): point-transcript loops must live in FREE functions (impl-method
loops fixed-point-fail while identical free-function loops translate —
`append_cards_to_transcript`/`append_ciphertexts_to_transcript`);
`scalar_pow`-style generic helpers called inside loops fail (replaced by
inline power recurrences); `is_identity` + break on slice/Vec elements is
the persistent fatal shape.

## Rollout status after the 2026-10-07 sessions

Extracted cleanly into the committed generated model (all zero-sorry):
`pk_ownership` (verify/challenge), `dleq_proof` (verify + append_dleq_context,
the fourth-design rewrites), `reveal_token_proof` (straight-line verify +
compute_challenge — extracted on the first attempt), and the remask/leave
production functions (`remask_ciphertext`/`leave_ciphertext`; the proof
bodies are the already-extracted `DLEqProof<C, _>`).

Blocked, with production-side changes kept (behavior-identical, tests pass):

* `generalized_schnorr_proof` — verify's bases-non-identity loop trips the
  Aeneas generic-loop-body `type_var_id` bug in every shape tried
  (for-range over `&[C::Point]`, hoisted bound, owned `Vec`, `while`
  counter). Notably the identical *call* (`Vec`-field element
  `.is_identity()` with break) extracts fine inside DLEq's verify, so the
  trigger is the parameter-slice/local data path — precise upstream
  repro material.
* `unified_sigma` — many `for card in &self.fold` loops (the same shape
  family); deferred pending either the upstream fix or a per-loop rewrite.

Feature plumbing notes (breaking-change fixes applied): the extraction
crate's `skip-prover`/`skip-tracing` features are NOT default (workspace
feature unification would hide the provers from every crate's tests);
`scripts/extract_aeneas.sh` enables them explicitly via
`--features skip-prover,skip-tracing`. The extraction crate disables its
lib tests (`[lib] test = false`; the sources are unit-tested in their home
crate). External callers that hand-mirrored the DLEq transcript schedule
via the removed `labels()` API were switched to inline label literals.

## Extending to the other proof systems

The remaining proof modules (`dleq_proof`, `generalized_schnorr_proof`,
`remask_proof`, `leave_proof`, `reveal_token_proof`, `shuffle_proof`,
reconstruction) are generic over the same `Curve`/`CryptoTranscript`
traits, so the same recipe applies: add the source file to the extraction
crate, state the backend interpretation for the transcript ops, prove the
refinement against the existing abstract module. Watch for the known
blockers documented in the repo analysis: the `challenge == 0` retry
`while` loops (bg/proof.rs, slot_or.rs, cross_key.rs) need bounded-retry
refactoring or exclusion, and the `LABEL_CACHE` lazy_static mutex
(test-only Merlin transcripts) must stay out of the extraction.
