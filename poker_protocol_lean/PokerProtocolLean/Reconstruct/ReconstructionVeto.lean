import Mathlib.Tactic
import PokerProtocolLean.Foundations.Negligible
import PokerProtocolLean.Reconstruct.Reconstruction
import PokerProtocolLean.Reconstruct.ReconstructionSecurity

/-!
# Non-owner veto impossibility (paper Theorem 5)

Paper §6.5 defines `Veto(p, m)` as an accepted reconstruction package by
player `p` that removes card `m` although the authenticated residual-carrier
derivation for `p`'s epoch does not authorize `m`, and states

`Pr[Veto(p, m)] ≤ ε_KS + ε_state + ε_ser`.

This file machine-checks the three layers of that claim:

1. **Algebraic core** (`no_removable_witness_without_owner_carrier`): no
   witness satisfying the extracted reconstruction relation can mark a slot
   removed unless some statement carrier is an owner-key encryption of that
   slot's card.  The hypothesis "no such carrier exists" is exactly what the
   authenticated missing-key invariant provides for a non-owned card.
2. **Semantic corollary** (`unauthorized_slot_keeps_card`): an unauthorized
   slot's contribution is the zero branch, so homomorphic reconstruction
   preserves the canonical card under the aggregate key.
3. **Package level** (`veto_free_extraction`): under the component interface,
   every witness extracted from an *accepted* package is veto-free on
   unauthorized slots, so acceptance cannot certify a veto.
4. **Quantitative form** (`veto_error_bound_negligible`): the union bound
   ε_KS + ε_state + ε_ser is negligible whenever each error family is.

The bound genuinely does not apply when the authenticated missing-key
invariant or owner-key secrecy fails: `hnoCarrier` below is the invariant, and
it is supplied by `ComponentInterface.authenticatedPriorState` plus
`transcriptStatementBinding` in the concrete instantiation.
-/

namespace PokerProtocolLean.Reconstruct.Reconstruction.Veto

open PokerProtocolLean.Foundations
open scoped ENNReal

variable (F : Type) [Field F]
variable (G : Type) [AddCommGroup G] [Module F G]
variable {n k : ℕ}

/-- The authenticated missing-key invariant specialized to one slot: no
authenticated residual carrier of this owner encrypts slot `i`'s card under
the owner key.  For a card the prover does not own, the authenticated prior
state establishes exactly this. -/
def NoAuthorizedCarrier (stmt : Statement G n k) (i : Fin n) : Prop :=
  ∀ (j : Fin k) (r : F),
    stmt.residualCarriers j ≠
      ElGamalCiphertext.encrypt F G stmt.g (stmt.cards i) stmt.ownerPk r

/-- **Algebraic core of the veto theorem.**  If no statement carrier encrypts
slot `i`'s card under the owner key, then no witness satisfying the extracted
relation removes slot `i`: `removed i = true` would exhibit a carrier index
`j` with `residualCarrierIndex j = i`, and the relation's residual half at `j`
would produce precisely the forbidden owner-key encryption. -/
theorem no_removable_witness_without_owner_carrier
    (stmt : Statement G n k) (i : Fin n)
    (hnoCarrier : NoAuthorizedCarrier F G stmt i)
    (wit : Witness F n k) (hrel : Relation F G stmt wit) :
    wit.removed i = false := by
  cases h : wit.removed i with
  | false => rfl
  | true =>
    obtain ⟨j, hj⟩ := (wit.removed_iff_residual_carrier i).mp h
    rcases hrel with ⟨_, hresidual⟩
    have hcarrier := hresidual j
    rw [hj] at hcarrier
    exact absurd hcarrier (hnoCarrier j (wit.residualRandomness j))

/-- **Semantic corollary.**  Without an authorized carrier, slot `i`'s accepted
contribution is the zero branch, so adding it to the canonical aggregate-key
encryption of the card preserves the card (up to accumulated randomness).
This is the algebraic content of paper Theorem 3's `χ i = 0` case, now tied to
the veto hypothesis rather than to an honest prover. -/
theorem unauthorized_slot_keeps_card
    (stmt : Statement G n k) (wit : Witness F n k)
    (hrel : Relation F G stmt wit) (i : Fin n)
    (hnoCarrier : NoAuthorizedCarrier F G stmt i)
    (initialRandomness : F) :
    ciphertextAdd G
        (ElGamalCiphertext.encrypt F G stmt.g (stmt.cards i)
          stmt.aggregatePk initialRandomness)
        (stmt.contributions i) =
      ElGamalCiphertext.encrypt F G stmt.g (stmt.cards i)
        stmt.aggregatePk (initialRandomness + wit.contributionRandomness i) := by
  have h := corrected_slot_semantics F G stmt wit hrel i initialRandomness
  rw [no_removable_witness_without_owner_carrier F G stmt i hnoCarrier wit hrel] at h
  simpa using h

/-- **Package-level veto freedom.**  Under the component interface, every
witness extracted from an accepted package leaves unauthorized slots
unremoved, and each such slot's contribution is an encryption of zero.  An
accepted proof therefore cannot certify removal of a card outside the
prover's authenticated owner-residual set. -/
theorem veto_free_extraction
    {Proof View : Type}
    (impl : Security.Implementation F G Proof View)
    (components : Security.ComponentInterface)
    (Indistinguishable : View → View → Prop)
    (reduction : Security.Reduction F G Proof View impl components Indistinguishable)
    (hcomponents : components.Hold)
    (stmt : Statement G n k) (proof : Proof)
    (hwellFormed : WellFormedStatement G stmt)
    (haccept : impl.verify stmt proof)
    (i : Fin n)
    (hnoCarrier : NoAuthorizedCarrier F G stmt i)
    (wit : Witness F n k)
    (hextract : reduction.extract stmt proof = some wit) :
    wit.removed i = false ∧
    stmt.contributions i =
      ElGamalCiphertext.encrypt F G stmt.g 0 stmt.aggregatePk
        (wit.contributionRandomness i) := by
  have hextracted :=
    Security.knowledge_soundness_under_components F G impl components Indistinguishable
      reduction hcomponents stmt proof hwellFormed haccept
  obtain ⟨wit', hextract', hrel', -⟩ := hextracted
  rw [hextract] at hextract'
  have hw : wit = wit' := Option.some.inj hextract'
  subst hw
  have hremoved :=
    no_removable_witness_without_owner_carrier F G stmt i hnoCarrier wit hrel'
  refine ⟨hremoved, ?_⟩
  rcases hrel' with ⟨hcontribution, _⟩
  simpa [contributionMessage, hremoved] using hcontribution i

/-- **Quantitative form of the veto bound** (paper Theorem 5).  The union of
the knowledge-soundness, authenticated-state, and serialization error
families is negligible whenever each family is; this is the union bound
behind `Pr[Veto(p, m)] ≤ ε_KS + ε_state + ε_ser`. -/
theorem veto_error_bound_negligible
    (εKS εstate εser : ℕ → ℝ≥0∞)
    (hKS : PokerProtocolLean.Foundations.Negligible εKS)
    (hstate : PokerProtocolLean.Foundations.Negligible εstate)
    (hser : PokerProtocolLean.Foundations.Negligible εser) :
    PokerProtocolLean.Foundations.Negligible
      fun m => εKS m + εstate m + εser m :=
  PokerProtocolLean.Foundations.Negligible_add
    (PokerProtocolLean.Foundations.Negligible_add hKS hstate) hser

end PokerProtocolLean.Reconstruct.Reconstruction.Veto
