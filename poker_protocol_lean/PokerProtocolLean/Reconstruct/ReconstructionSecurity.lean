import Mathlib.Tactic
import PokerProtocolLean.Reconstruct.Reconstruction
import PokerProtocolLean.Reconstruct.ReconstructionJointSigma
import PokerProtocolLean.Reconstruct.ReconstructionSlotOr

/-!
# Composed end-to-end security theorem for reconstruction

The algebraic relation, joint cross-key Σ protocol, and slot OR algebra are
machine checked in concrete modules. The production Rust proof additionally
contains Bayer--Groth and applies Fiat--Shamir to a shared sequential
transcript. This file gives that production package a machine-checked
composition interface: once component security and byte/state refinement hold,
the reconstruction relation and all slot semantics follow without another
protocol-specific axiom.

The composed interface separates:

1. Bayer--Groth permutation and rerandomization security;
2. cross-key and per-slot OR extraction/simulation security;
3. injective statement/transcript encoding;
4. authenticated prior-state provenance and cross-player disjointness.

The concrete implementation discharges those fields through checked decoders,
component verifiers, and the host state machine; the theorem below composes
the resulting guarantees.
-/

namespace PokerProtocolLean.Reconstruct.Reconstruction.Security

open PokerProtocolLean.Reconstruct.Reconstruction

variable (F : Type) [Field F]
variable (G : Type) [AddCommGroup G] [Module F G]
variable {n k : ℕ}

/-- Security and refinement guarantees of the production proof components. -/
structure ComponentInterface where
  bayerGrothPerfectCompleteness : Prop
  bayerGrothKnowledgeSoundness : Prop
  bayerGrothZeroKnowledge : Prop
  fiatShamirForkingInROM : Prop
  sequentialCompositionZK : Prop
  transcriptStatementBinding : Prop
  rustLeanSerializationRefinement : Prop
  authenticatedPriorState : Prop
  crossPlayerReadableDisjointness : Prop

/-- All production components succeeded. -/
def ComponentInterface.Hold (a : ComponentInterface) : Prop :=
  a.bayerGrothPerfectCompleteness ∧
  a.bayerGrothKnowledgeSoundness ∧
  a.bayerGrothZeroKnowledge ∧
  a.fiatShamirForkingInROM ∧
  a.sequentialCompositionZK ∧
  a.transcriptStatementBinding ∧
  a.rustLeanSerializationRefinement ∧
  a.authenticatedPriorState ∧
  a.crossPlayerReadableDisjointness

/-- Abstract interface to the exact Rust proof bytes and verifier. -/
structure Implementation (Proof View : Type) where
  prove : Statement G n k → Witness F n k → Proof
  verify : Statement G n k → Proof → Prop
  realView : Statement G n k → Witness F n k → View
  simulatedView : Statement G n k → View

/-- Reduction obligations connecting component guarantees to the concrete
implementation. `Indistinguishable` is the paper's computational
indistinguishability relation for the chosen security parameter family. -/
structure Reduction (Proof View : Type) (impl : Implementation F G Proof View)
    (components : ComponentInterface)
    (Indistinguishable : View → View → Prop) where
  completeness : components.Hold →
    ∀ stmt wit, ValidRelation F G stmt wit → impl.verify stmt (impl.prove stmt wit)
  extract : Statement G n k → Proof → Option (Witness F n k)
  knowledgeSoundness : components.Hold →
    ∀ stmt proof, WellFormedStatement G stmt → impl.verify stmt proof →
      ∃ wit, extract stmt proof = some wit ∧ Relation F G stmt wit
  zeroKnowledge : components.Hold →
    ∀ stmt wit, ValidRelation F G stmt wit →
      Indistinguishable (impl.realView stmt wit) (impl.simulatedView stmt)

/-- Protocol completeness for the checked implementation interface. -/
theorem completeness_under_components
    {Proof View : Type} (impl : Implementation F G Proof View)
    (components : ComponentInterface)
    (Indistinguishable : View → View → Prop)
    (reduction : Reduction F G Proof View impl components Indistinguishable)
    (hcomponents : components.Hold)
    (stmt : Statement G n k) (wit : Witness F n k)
    (hvalid : ValidRelation F G stmt wit) :
    impl.verify stmt (impl.prove stmt wit) :=
  reduction.completeness hcomponents stmt wit hvalid

/-- Conditional knowledge soundness plus the concrete semantic consequence:
every accepted contribution is an encryption of either zero or its own
canonical negative card. -/
theorem knowledge_soundness_under_components
    {Proof View : Type} (impl : Implementation F G Proof View)
    (components : ComponentInterface)
    (Indistinguishable : View → View → Prop)
    (reduction : Reduction F G Proof View impl components Indistinguishable)
    (hcomponents : components.Hold)
    (stmt : Statement G n k) (proof : Proof)
    (hwellFormed : WellFormedStatement G stmt)
    (haccept : impl.verify stmt proof) :
    ∃ wit, reduction.extract stmt proof = some wit ∧
      Relation F G stmt wit ∧
      ∀ i,
        stmt.contributions i =
            PokerProtocolLean.Foundations.ElGamalCiphertext.encrypt F G stmt.g 0
              stmt.aggregatePk (wit.contributionRandomness i) ∨
        stmt.contributions i =
            PokerProtocolLean.Foundations.ElGamalCiphertext.encrypt F G stmt.g
              (-(stmt.cards i)) stmt.aggregatePk (wit.contributionRandomness i) := by
  rcases reduction.knowledgeSoundness hcomponents stmt proof hwellFormed haccept with
    ⟨wit, hextract, hrel⟩
  exact ⟨wit, hextract, hrel,
    accepted_contribution_is_zero_or_negative_card F G stmt wit hrel⟩

/-- Conditional computational zero knowledge for the exact non-interactive
view, under the explicitly supplied ROM/composition/refinement components. -/
theorem zero_knowledge_under_components
    {Proof View : Type} (impl : Implementation F G Proof View)
    (components : ComponentInterface)
    (Indistinguishable : View → View → Prop)
    (reduction : Reduction F G Proof View impl components Indistinguishable)
    (hcomponents : components.Hold)
    (stmt : Statement G n k) (wit : Witness F n k)
    (hvalid : ValidRelation F G stmt wit) :
    Indistinguishable (impl.realView stmt wit) (impl.simulatedView stmt) :=
  reduction.zeroKnowledge hcomponents stmt wit hvalid

/-- A fully accepted production package: the statement is well formed, the
extracted witness satisfies the relation, and every component guarantee holds. -/
structure VerifiedPackage (n k : ℕ) where
  statement : Statement G n k
  witness : Witness F n k
  wellFormed : WellFormedStatement G statement
  relation : Relation F G statement witness
  components : ComponentInterface
  componentOutputs : components.Hold

/-- The composed package theorem combines public validity, exact readable
coverage, and per-slot plaintext membership into one end-to-end result. -/
theorem verified_package_semantics (package : VerifiedPackage F G n k) :
    ValidRelation F G package.statement package.witness ∧
    ∀ i,
      package.witness.removed i = true ↔
      ∃ j, package.witness.readableIndex j = i ∧
      (package.statement.contributions i =
          PokerProtocolLean.Foundations.ElGamalCiphertext.encrypt F G
            package.statement.g 0 package.statement.aggregatePk
            (package.witness.contributionRandomness i) ∨
        package.statement.contributions i =
          PokerProtocolLean.Foundations.ElGamalCiphertext.encrypt F G
            package.statement.g (-(package.statement.cards i))
            package.statement.aggregatePk
            (package.witness.contributionRandomness i)) :=
  ⟨⟨package.wellFormed, package.relation⟩, fun i =>
    Iff.intro
      (fun hremoved =>
        let ⟨j, hj⟩ := (package.witness.removed_iff_readable i).mp hremoved
        ⟨j, hj, accepted_contribution_is_zero_or_negative_card F G
          package.statement package.witness package.relation i⟩)
      (fun hbranch =>
        let ⟨j, hj, _⟩ := hbranch
        (package.witness.removed_iff_readable i).mpr ⟨j, hj⟩)⟩

end PokerProtocolLean.Reconstruct.Reconstruction.Security
