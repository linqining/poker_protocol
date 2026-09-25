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

/-!
Full-field `ReconstructionStatement<StarkCurve>` Borsh v3 schema shape. The
committed JSON fixture carries the corresponding deterministic bytes; Rust
regenerates and serializes those bytes, while this module fixes the same field
order, offsets, lengths, prefix, and SHA-256 digest for cross-language review.
-/
def statementSchemaVersion : Nat := 4
def statementByteLength : Nat := 1041
def statementFieldCount : Nat := 11
def statementPrefixLength : Nat := 141
def statementPrefixHex : String :=
  "0307070707070707070707070707070707070707070707070707070707070707070b0000000000000009090909090909090909090909090909090909090909090909090909090909090746db56abc4d9fab4832ee42e92e96bbbf8cf4c9fd063b8515bda90d1e8aa5d849313ef8f55a662f012bb91becb8d07da05d3af8a9e958cb7a0b6129a750e8d08000000"
def statementSha256 : String :=
  "068838873c85c14bd6236a4a944a7e3802930f2ed50e3a6e7cd8de725bc9e323"

def statementFieldSchema : List (String × Nat × Nat) := [
  ("version", 0, 1),
  ("context_digest", 1, 32),
  ("reconstruction_epoch", 33, 8),
  ("prior_state_digest", 41, 32),
  ("aggregate_pk", 73, 32),
  ("owner_pk", 105, 32),
  ("card_count", 137, 4),
  ("cards", 141, 256),
  ("residual_carrier_count", 397, 4),
  ("residual_carriers", 401, 128),
  ("contributions", 529, 512)
]

/-!
Frozen schema for one deterministically generated randomized proof instance.
The bytes are not a canonical proof encoding: the fixture fixes the output of
one seeded ChaCha20 run and Fiat--Shamir transcript. Rust regenerates and
verifies these exact bytes; this module fixes the top-level wire schema,
prefix, and SHA-256 for cross-language review.
-/
def proofSchemaVersion : Nat := 1
def proofByteLength : Nat := 3829
def proofFieldCount : Nat := 7
def proofNestedFieldCount : Nat := 30
def proofPrefixLength : Nat := 5
def proofPrefixHex : String := "0302000000"
def proofSha256 : String :=
  "58f604b72c304954a978d6a8d61ed6f7844ae8dd5b9a627f264c61aaf69d43f1"

def proofFieldSchema : List (String × Nat × Nat) := [
  ("version", 0, 1),
  ("negative_contribution_count", 1, 4),
  ("negative_contributions", 5, 128),
  ("cross_key_proofs", 133, 320),
  ("contribution_shuffle_proof", 453, 1324),
  ("slot_membership_proof_count", 1777, 4),
  ("slot_membership_proofs", 1781, 2048)
]

theorem vector_shape :
    version = 3 ∧ reconstructionEpoch = 11 ∧ cardCount = 8 ∧
      residualCarrierCount = 2 ∧ removedBitmap =
        [false, true, false, false, true, false, false, false] := by
  simp [version, reconstructionEpoch, cardCount, residualCarrierCount, removedBitmap]

theorem statement_schema_shape :
    statementSchemaVersion = 4 ∧ statementByteLength = 1041 ∧
      statementFieldCount = 11 ∧ statementPrefixLength = 141 ∧
      statementFieldSchema =
        [("version", 0, 1), ("context_digest", 1, 32),
         ("reconstruction_epoch", 33, 8), ("prior_state_digest", 41, 32),
         ("aggregate_pk", 73, 32), ("owner_pk", 105, 32),
         ("card_count", 137, 4), ("cards", 141, 256),
         ("residual_carrier_count", 397, 4),
         ("residual_carriers", 401, 128), ("contributions", 529, 512)] := by
  simp [statementSchemaVersion, statementByteLength, statementFieldCount,
    statementPrefixLength, statementFieldSchema]

theorem proof_schema_shape :
    proofSchemaVersion = 1 ∧ proofByteLength = 3829 ∧
      proofFieldCount = 7 ∧ proofNestedFieldCount = 30 ∧
      proofPrefixLength = 5 ∧ proofPrefixHex = "0302000000" ∧
      proofSha256 =
        "58f604b72c304954a978d6a8d61ed6f7844ae8dd5b9a627f264c61aaf69d43f1" ∧
      proofFieldSchema =
        [("version", 0, 1), ("negative_contribution_count", 1, 4),
         ("negative_contributions", 5, 128), ("cross_key_proofs", 133, 320),
         ("contribution_shuffle_proof", 453, 1324),
         ("slot_membership_proof_count", 1777, 4),
         ("slot_membership_proofs", 1781, 2048)] := by
  simp [proofSchemaVersion, proofByteLength, proofFieldCount,
    proofNestedFieldCount, proofPrefixLength, proofPrefixHex, proofSha256,
    proofFieldSchema]

end PokerProtocolLean.Reconstruct.RefinementVectors
