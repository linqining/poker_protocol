import PokerProtocolLean.Reconstruct.RefinementVectors

open PokerProtocolLean.Reconstruct.RefinementVectors

def bitmapString : String :=
  String.join (removedBitmap.map fun removed => if removed then "1" else "0")

def main : IO Unit :=
  do
    IO.println s!"{version}\t{reconstructionEpoch}\t{cardCount}\t{residualCarrierCount}\t{bitmapString}"
    IO.println s!"{statementSchemaVersion}\t{statementByteLength}\t{statementFieldCount}\t{statementPrefixLength}\t{statementPrefixHex}\t{statementSha256}"
    IO.println s!"{proofSchemaVersion}\t{proofByteLength}\t{proofFieldCount}\t{proofNestedFieldCount}\t{proofPrefixLength}\t{proofPrefixHex}\t{proofSha256}"
