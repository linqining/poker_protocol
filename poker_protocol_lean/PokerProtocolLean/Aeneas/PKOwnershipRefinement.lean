import PokerProtocolLean.Aeneas.BackendSpec
import PokerProtocolLean.PKOwnership.PKOwnershipProof

/-!
# Machine-checked Rust→Lean refinement: `PKOwnershipProof::verify`

`poker-protocol-aeneas` compiles the production file
`poker-protocol-proofs/src/pk_ownership.rs` **verbatim** (via `#[path]`,
with the probabilistic rejection-sampling prover gated out), and
Charon/Aeneas extract it — with a machine-checked backward simulation
against the Rust MIR semantics — into
`poker_protocol_aeneas.pk_ownership` (see `PokerProtocolLean/Aeneas/Generated.lean`
and `scripts/extract_aeneas.sh`).

This module links the extracted verifier to the abstract Σ-protocol of
`PokerProtocolLean.PKOwnership` (the `n = 1` instance of
`PokerProtocolLean.GeneralizedSchnorr`, where completeness, special
soundness and perfect HVZK are already proved).

The link is a *refinement theorem*, not an axiom: the concrete curve
backend enters through an explicit interpretation record `BackendSpec`
whose fields are hypotheses (the algebraic specification any correct
`Curve` implementation must satisfy). Under such a backend:

* `extracted_verify_sound` — if the extracted Rust verifier accepts, then
  the extracted Fiat–Shamir `challenge` succeeded with some scalar `e` and
  the abstract Schnorr verification equation
  `response • g = commitment + e • pk` holds.
* `extracted_verify_complete` — conversely, if the abstract verification
  equation holds for a challenge produced by the extracted `challenge`
  (and the statement and commitment are non-identity), the extracted Rust
  verifier accepts.
* `extracted_verify_iff_sigma_verify` — the same equivalence phrased
  against the abstract verifier of `GeneralizedSchnorr.sigma`, so the
  already-proved special soundness of the abstract protocol applies to
  accepting transcripts of the shipped Rust code.

The remaining assumption boundary is exactly `BackendSpec` (the backend
algebra: totality, module laws, and equality reflection) plus the
Fiat–Shamir hash, which the abstract model treats as the challenge oracle.
-/

namespace PokerProtocolLean.AeneasPKOwnershipRefinement

open Aeneas Aeneas.Std Result poker_protocol_aeneas
open PokerProtocolLean.AeneasRefinement

/- All types live in `Type`: `SampleableType` and the extracted structures
are universe-0. -/
variable {F G P S Comp C : Type}
variable [Field F] [Fintype F] [DecidableEq F] [SampleableType F]
variable [AddCommGroup G] [Module F G] [Fintype G] [DecidableEq G]
  [SampleableType G]
variable (g : G)
variable (curve : poker_protocol_aeneas.poker_protocol_core.curve.Curve C P S Comp)

/-! ## Soundness of the extracted verifier

If the extracted Rust verifier accepts, every intermediate operation must
have succeeded (failure and divergence propagate through the `Result`
monad), and the final comparison witnesses the abstract equation. -/

/-- Acceptance by the extracted Rust verifier implies the extracted
Fiat–Shamir challenge succeeded and the abstract Schnorr verification
equation holds. -/
theorem extracted_verify_sound (spec : BackendSpec F G P S Comp C g curve)
    (prf : poker_protocol_aeneas.pk_ownership.PKOwnershipProof C P S Comp) (pk : P)
    (h : pk_ownership.PKOwnershipProof.verify curve prf pk = Result.ok true) :
    ∃ e : S, pk_ownership.challenge curve pk prf.commitment = Result.ok e ∧
      spec.ιS prf.response • g = spec.ιP prf.commitment + spec.ιS e • spec.ιP pk := by
  -- `is_identity public_key` must have returned `ok false`: otherwise the
  -- extracted verifier immediately rejects.
  obtain ⟨b, hb, hbs⟩ := spec.is_identity_ok pk
  cases b with
  | true =>
      have hv : pk_ownership.PKOwnershipProof.verify curve prf pk = Result.ok false := by
        simp [pk_ownership.PKOwnershipProof.verify, hb]
      rw [hv] at h
      exact absurd h (by simp)
  | false =>
  -- same for the commitment
  obtain ⟨b1, hb1, hbs1⟩ := spec.is_identity_ok prf.commitment
  cases b1 with
  | true =>
      have hv : pk_ownership.PKOwnershipProof.verify curve prf pk = Result.ok false := by
        simp [pk_ownership.PKOwnershipProof.verify, hb, hb1]
      rw [hv] at h
      exact absurd h (by simp)
  | false =>
  -- the Fiat–Shamir challenge must have succeeded with some `e`
  cases hme : (pk_ownership.challenge curve pk prf.commitment).match with
  | ok e =>
      have hc : pk_ownership.challenge curve pk prf.commitment = Result.ok e :=
        Result.match.isOk.mp hme
      -- realize the backend multiplications and additions
      obtain ⟨t1, ht1, ht1map⟩ := spec.mul_ok spec.base prf.response
      obtain ⟨t2, ht2, ht2map⟩ := spec.mul_ok pk e
      obtain ⟨t3, ht3, ht3map⟩ := spec.add_ok prf.commitment t2
      -- the whole computation reduces to the final equality test
      have hred : pk_ownership.PKOwnershipProof.verify curve prf pk =
          Result.ok (decide (spec.ιP t1 = spec.ιP t3)) := by
        simp [pk_ownership.PKOwnershipProof.verify, hb, hb1, hc, spec.base_g_ok,
          ht1, ht2, ht3, spec.eq_ok]
      rw [hred] at h
      have heq : spec.ιP t1 = spec.ιP t3 := by
        simpa using h
      refine ⟨e, hc, ?_⟩
      rw [ht1map, ht3map, ht2map, spec.base_map] at heq
      exact heq
  | vis eff k =>
      have hc : pk_ownership.challenge curve pk prf.commitment = Result.vis eff k :=
        Result.match.isVis.mp hme
      simp [pk_ownership.PKOwnershipProof.verify, hb, hb1, hc] at h
  | div =>
      have hc : pk_ownership.challenge curve pk prf.commitment = Result.div :=
        Result.match.isDiv.mp hme
      simp [pk_ownership.PKOwnershipProof.verify, hb, hb1, hc] at h

/-! ## Completeness of the extracted verifier -/

/-- If the abstract Schnorr verification equation holds for a challenge
produced by the extracted Fiat–Shamir `challenge`, and the statement and
commitment are non-identity, the extracted Rust verifier accepts. -/
theorem extracted_verify_complete (spec : BackendSpec F G P S Comp C g curve)
    (commitment : P) (response : S) (pk : P) (e : S)
    (hpk : spec.ιP pk ≠ 0) (hcom : spec.ιP commitment ≠ 0)
    (hchal : pk_ownership.challenge curve pk commitment = Result.ok e)
    (heq : spec.ιS response • g = spec.ιP commitment + spec.ιS e • spec.ιP pk) :
    pk_ownership.PKOwnershipProof.verify curve
      { commitment := commitment, response := response } pk = Result.ok true := by
  have hId := spec.is_identity_false hpk
  have hIdC := spec.is_identity_false hcom
  obtain ⟨t1, ht1, ht1map⟩ := spec.mul_ok spec.base response
  obtain ⟨t2, ht2, ht2map⟩ := spec.mul_ok pk e
  obtain ⟨t3, ht3, ht3map⟩ := spec.add_ok commitment t2
  have hred : pk_ownership.PKOwnershipProof.verify curve
      { commitment := commitment, response := response } pk =
      Result.ok (decide (spec.ιS response • g =
        spec.ιP commitment + spec.ιS e • spec.ιP pk)) := by
    simp [pk_ownership.PKOwnershipProof.verify, hId, hIdC, hchal, spec.base_g_ok,
      ht1, ht2, ht3, spec.eq_ok, ht1map, ht2map, ht3map, spec.base_map]
  rw [hred, heq]
  simp

/-! ## Combined equivalence -/

/-- The extracted Rust verifier accepts exactly when its Fiat–Shamir
challenge succeeds and the abstract verification equation holds
(for non-identity statement and commitment, which the Rust code
fail-closes on). -/
theorem extracted_verify_iff_abstract (spec : BackendSpec F G P S Comp C g curve)
    (prf : poker_protocol_aeneas.pk_ownership.PKOwnershipProof C P S Comp) (pk : P)
    (hpk : spec.ιP pk ≠ 0) (hcom : spec.ιP prf.commitment ≠ 0) :
    (pk_ownership.PKOwnershipProof.verify curve prf pk = Result.ok true ↔
      ∃ e : S, pk_ownership.challenge curve pk prf.commitment = Result.ok e ∧
        spec.ιS prf.response • g =
          spec.ιP prf.commitment + spec.ιS e • spec.ιP pk) := by
  constructor
  · exact extracted_verify_sound g curve spec prf pk
  · rintro ⟨e, hc, heq⟩
    exact extracted_verify_complete g curve spec prf.commitment prf.response pk e hpk hcom hc heq

/-- Rephrase: acceptance by the extracted Rust verifier is exactly
acceptance by the abstract `GeneralizedSchnorr.sigma` (n = 1) verifier,
with the challenge supplied by the extracted Fiat–Shamir transcript. -/
theorem extracted_verify_iff_sigma_verify (spec : BackendSpec F G P S Comp C g curve)
    (prf : poker_protocol_aeneas.pk_ownership.PKOwnershipProof C P S Comp) (pk : P)
    (hpk : spec.ιP pk ≠ 0) (hcom : spec.ιP prf.commitment ≠ 0) :
    (pk_ownership.PKOwnershipProof.verify curve prf pk = Result.ok true ↔
      ∃ e : S, pk_ownership.challenge curve pk prf.commitment = Result.ok e ∧
        (PokerProtocolLean.GeneralizedSchnorr.sigma F G 1).verify
            (PokerProtocolLean.PKOwnership.toStatement F G g ⟨spec.ιP pk⟩)
            (spec.ιP prf.commitment) (spec.ιS e)
            (fun _ => spec.ιS prf.response) = true) := by
  rw [extracted_verify_iff_abstract g curve spec prf pk hpk hcom]
  constructor
  · rintro ⟨e, hc, heq⟩
    refine ⟨e, hc, ?_⟩
    simp [PokerProtocolLean.GeneralizedSchnorr.sigma,
      PokerProtocolLean.GeneralizedSchnorr.dotSmul,
      PokerProtocolLean.PKOwnership.toStatement, heq]
  · rintro ⟨e, hc, hsig⟩
    refine ⟨e, hc, ?_⟩
    have : decide (spec.ιS prf.response • g =
        spec.ιP prf.commitment + spec.ιS e • spec.ιP pk) = true := by
      simpa [PokerProtocolLean.GeneralizedSchnorr.sigma,
        PokerProtocolLean.GeneralizedSchnorr.dotSmul,
        PokerProtocolLean.PKOwnership.toStatement] using hsig
    simpa using this

end PokerProtocolLean.AeneasPKOwnershipRefinement
