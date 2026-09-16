import PokerProtocolLean.Reconstruct.ReconstructProof

/-!
# Reconstruction sanity checks
-/

namespace PokerProtocolLean.Sanity.ReconstructSanity

open PokerProtocolLean.Foundations

variable (F : Type) [Field F]
variable (G : Type) [AddCommGroup G] [Module F G]

/-- The joint cross-key relation is complete for opposite plaintexts. -/
example (g ownerPk aggregatePk m : G)
    (ownerSk readableRandomness contributionRandomness : F)
    (hpk : ownerPk = ownerSk • g) :
    PokerProtocolLean.Reconstruct.Reconstruction.CrossKeyNegationRelation F G
      g ownerPk aggregatePk
      (ElGamalCiphertext.encrypt F G g m ownerPk readableRandomness)
      (ElGamalCiphertext.encrypt F G g (-m) aggregatePk contributionRandomness)
      ownerSk contributionRandomness :=
  PokerProtocolLean.Reconstruct.Reconstruction.cross_key_negation_complete F G
    g ownerPk aggregatePk m ownerSk readableRandomness contributionRandomness hpk

end PokerProtocolLean.Sanity.ReconstructSanity
