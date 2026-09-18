#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"
cargo test --locked -p poker-protocol-proofs reconstruction_shared_refinement_vector
(cd poker_protocol_lean && lake build PokerProtocolLean)
(cd poker_protocol_lean && bash scripts/count_sorries.sh)
node scripts/verify_refinement_vector.mjs
printf '[refinement] shared Rust--Lean semantic vector passed\n'
