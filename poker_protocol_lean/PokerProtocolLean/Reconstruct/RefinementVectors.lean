/-!
# Shared Rust--Lean reconstruction refinement vector

This module deliberately fixes only the semantic shape used by both test
suites. It is not a claim that Lean parses or verifies every Rust byte. The
Rust test `reconstruction_shared_refinement_vector` and the theorem below use
the same version, epoch, dimensions, and removal bitmap.
-/

namespace PokerProtocolLean.Reconstruct.RefinementVectors

def version : Nat := 3
def reconstructionEpoch : Nat := 11
def cardCount : Nat := 8
def residualCarrierCount : Nat := 2
def removedBitmap : List Bool := [false, true, false, false, true, false, false, false]

theorem vector_shape :
    version = 3 ∧ reconstructionEpoch = 11 ∧ cardCount = 8 ∧
      residualCarrierCount = 2 ∧ removedBitmap =
        [false, true, false, false, true, false, false, false] := by
  simp [version, reconstructionEpoch, cardCount, residualCarrierCount, removedBitmap]

end PokerProtocolLean.Reconstruct.RefinementVectors
