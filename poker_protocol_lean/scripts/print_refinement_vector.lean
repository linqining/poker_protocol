import PokerProtocolLean.Reconstruct.RefinementVectors

open PokerProtocolLean.Reconstruct.RefinementVectors

def bitmapString : String :=
  String.join (removedBitmap.map fun removed => if removed then "1" else "0")

def main : IO Unit :=
  IO.println s!"{version}\t{reconstructionEpoch}\t{cardCount}\t{residualCarrierCount}\t{bitmapString}"
