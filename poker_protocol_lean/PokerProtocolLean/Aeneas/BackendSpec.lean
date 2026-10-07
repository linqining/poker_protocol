import PokerProtocolLean.Aeneas.Generated
import PokerProtocolLean.PKOwnership.PKOwnershipProof

/-!
# Shared backend interpretation for Rust→Lean refinements

`BackendSpec` is the explicit hypothesis record shared by every
module-specific refinement proof (see `PKOwnershipRefinement.lean`): it
interprets a concrete extracted curve backend
(`poker_protocol_aeneas.poker_protocol_core.curve.Curve C P S Comp`)
in an abstract group `G` and field `F` with generator `g`. Every field is
a hypothesis — the algebraic specification any correct `Curve`
implementation must satisfy. No protocol-specific axiom is introduced.
-/

namespace PokerProtocolLean.AeneasRefinement

open Aeneas Aeneas.Std Result poker_protocol_aeneas

variable {F G P S Comp C : Type}
variable [Field F] [Fintype F] [DecidableEq F] [SampleableType F]
variable [AddCommGroup G] [Module F G] [Fintype G] [DecidableEq G]
  [SampleableType G]
variable (g : G)
variable (curve : poker_protocol_aeneas.poker_protocol_core.curve.Curve C P S Comp)

/-! ## The backend interpretation

Every field is a hypothesis about the *concrete* curve implementation
behind the extracted generic code; no protocol-specific axiom is
introduced. `ιP`/`ιS` interpret Rust points/scalars in the abstract
group/field. Operations are total (they return `ok`; failure and
divergence are impossible) and satisfy the module/field laws the abstract
model assumes. -/

/-- Interpretation hypotheses linking a concrete extracted curve backend
to the abstract group `G` and field `F` with generator `g`. -/
structure BackendSpec (F : Type) [Field F] [Fintype F] [DecidableEq F]
    [SampleableType F] (G : Type) [AddCommGroup G] [Module F G] [Fintype G]
    [DecidableEq G] [SampleableType G] (P S Comp C : Type) (g : G)
    (curve : poker_protocol_aeneas.poker_protocol_core.curve.Curve C P S Comp) where
  /-- Interpretation of Rust points in the abstract group. -/
  ιP : P → G
  /-- Interpretation of Rust scalars in the abstract field. -/
  ιS : S → F
  /-- The Rust base point (its computation succeeds by `base_g_ok`). -/
  base : P
  base_g_ok : curve.base_g = Result.ok base
  base_map : ιP base = g
  /-- `is_identity` decides abstract zero and always succeeds. -/
  is_identity_ok : ∀ p : P, ∃ b : Bool,
    curve.CurvePointInst.is_identity p = Result.ok b ∧ (b = true ↔ ιP p = 0)
  /-- Scalar multiplication refines the module action and always succeeds. -/
  mul_ok : ∀ p : P, ∀ s : S, ∃ q : P,
    curve.CurvePointInst.coreopsarithMulInst.mul p s = Result.ok q ∧
      ιP q = ιS s • ιP p
  /-- Point addition refines the group operation and always succeeds. -/
  add_ok : ∀ p q : P, ∃ r : P,
    curve.CurvePointInst.coreopsarithAddInst.add p q = Result.ok r ∧
      ιP r = ιP p + ιP q
  /-- Point equality decides abstract equality. -/
  eq_ok : ∀ p q : P,
    curve.CurvePointInst.corecmpPartialEqInst.eq p q =
      Result.ok (decide (ιP p = ιP q))

namespace BackendSpec

variable {g curve}

/-- For an abstractly non-identity point, the extracted `is_identity`
returns `ok false`. -/
theorem is_identity_false (spec : BackendSpec F G P S Comp C g curve) {p : P} (hp : spec.ιP p ≠ 0) :
    curve.CurvePointInst.is_identity p = Result.ok false := by
  obtain ⟨b, hb, hbs⟩ := spec.is_identity_ok p
  cases b with
  | true => exact absurd (hbs.mp rfl) hp
  | false => exact hb

end BackendSpec

end PokerProtocolLean.AeneasRefinement
