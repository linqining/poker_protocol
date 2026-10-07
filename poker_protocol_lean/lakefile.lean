import Lake
open Lake DSL

package poker_protocol_lean where
  leanOptions := #[
    ⟨`pp.unicode, true⟩,
    ⟨`maxHeartbeats, 5120000⟩,
    ⟨`maxRecDepth, 1024⟩,
    ⟨`autoImplicit, false⟩,
    ⟨`relaxedAutoImplicit, false⟩
  ]

require mathlib from git
  "https://github.com/leanprover-community/mathlib4.git" @ "v4.32.0"

require VCVio from git
  "https://github.com/Verified-zkEVM/VCV-io.git" @ "v4.32.0"

-- Vendored Aeneas runtime library (see vendor/aeneas/lakefile.lean for
-- provenance). Used by the machine-checked Rust→Lean refinement layer
-- (PokerProtocolLean/Aeneas/).
require aeneas from "vendor/aeneas"

@[default_target]
lean_lib PokerProtocolLean where
  roots := #[`PokerProtocolLean]
