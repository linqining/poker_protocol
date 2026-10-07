#!/usr/bin/env bash
# Re-extract the Rust sigma-protocol logic to Lean via Charon + Aeneas and
# install the generated model into the Lean project.
#
# Pipeline (see poker_protocol_lean/PokerProtocolLean/Aeneas/ and
# docs in PokerProtocolLean/Aeneas/PKOwnershipRefinement.lean):
#
#   1. `charon cargo --preset=aeneas -- --features skip-prover,skip-tracing` on the `poker-protocol-aeneas`
#      extraction crate. That crate compiles the production source file
#      poker-protocol-proofs/src/pk_ownership.rs VERBATIM via #[path]
#      (its default `skip-prover` feature gates out the probabilistic
#      rejection-sampling prover, which Aeneas cannot translate).
#      Charon emits poker_protocol_aeneas.llbc at the workspace root.
#   2. `aeneas -backend lean` translates the LLBC to pure Lean
#      (each definition comes with a machine-checked backward-simulation
#      proof against the Rust MIR semantics).
#   3. A small, auditable post-patch renames two duplicate structure
#      fields that this Aeneas version emits for `CurvePoint` (the Clone
#      and Debug supertrait clauses of Self and Self::Compressed collide;
#      nothing references the colliding names).
#   4. The result is installed as
#      poker_protocol_lean/PokerProtocolLean/Aeneas/Generated.lean.
#
# Requirements:
#   - Charon/Aeneas binaries: set AENEAS_HOME (default ~/tools/aeneas-lab/aeneas),
#     from Aeneas release nightly-2026.10.07-aa66752 (arm64 macOS build tested).
#     The release bundles charon/charon-driver/aeneas; keep them together.
#   - The Rust toolchain pinned in poker-protocol-aeneas/rust-toolchain.toml
#     (nightly-2026-08-18 with rustc-dev, rust-src, llvm-tools), installed
#     via rustup. Charon only works with its pinned rustc.
#   - rustup/cargo on PATH.
#
# After regenerating, run `lake build PokerProtocolLean` and
# `bash scripts/count_sorries.sh` inside poker_protocol_lean/.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AENEAS_HOME="${AENEAS_HOME:-$HOME/tools/aeneas-lab/aeneas}"
CRATE="$ROOT/poker-protocol-aeneas"
OUT_DIR="$(mktemp -d)"
# Charon builds a MIR-rich sysroot through the miri machinery; isolate HOME
# so a stale ~/.oracle miri std-cache (built by another nightly) cannot
# poison the build, and isolate the target dir so the pinned extraction
# toolchain does not thrash the shared workspace target/.
CHARON_HOME="$(mktemp -d)"

export PATH="$HOME/.cargo/bin:$AENEAS_HOME:$PATH"
export RUSTUP_HOME="${RUSTUP_HOME:-$HOME/.rustup}"
export CARGO_HOME="${CARGO_HOME:-$HOME/.cargo}"
export DYLD_LIBRARY_PATH="$AENEAS_HOME/libs:${DYLD_LIBRARY_PATH:-}"

echo "==> [1/4] Charon: extract LLBC (preset=aeneas)"
cd "$CRATE"
touch src/lib.rs  # force the charon-driver to re-run on a cached target
HOME="$CHARON_HOME" CARGO_TARGET_DIR="$CRATE/target" \
  charon cargo --preset=aeneas -- --features skip-prover,skip-tracing

LLBC="$ROOT/poker_protocol_aeneas.llbc"
if [ ! -f "$LLBC" ]; then
  echo "FAIL: charon produced no $LLBC" >&2
  exit 1
fi

echo "==> [2/4] Aeneas: translate to Lean"
( cd "$ROOT" && aeneas -backend lean -dest "$OUT_DIR" "$LLBC" )

GEN="$OUT_DIR/PokerProtocolAeneas.lean"
if [ ! -f "$GEN" ]; then
  echo "FAIL: aeneas produced no $GEN" >&2
  exit 1
fi
if grep -q "sorry" "$GEN"; then
  echo "FAIL: generated model contains 'sorry' (extraction was partial)" >&2
  exit 1
fi

echo "==> [3/4] Post-patch: rename duplicate CurvePoint supertrait fields"
# Pick a *working* python3: on multi-arch macOS hosts an x86_64-only
# python3 may sit first on PATH ("Bad CPU type"), so prefer /usr/bin.
PYBIN="${PYTHON:-}"
if [ -z "$PYBIN" ]; then
  for cand in /usr/bin/python3 python3; do
    if "$cand" -c 'pass' >/dev/null 2>&1; then PYBIN="$cand"; break; fi
  done
fi
if [ -z "$PYBIN" ]; then
  echo "FAIL: no working python3 found (set PYTHON=/path/to/python3)" >&2
  exit 1
fi
"$PYBIN" - "$GEN" <<'PY'
import sys
p = sys.argv[1]
s = open(p).read()
# This Aeneas version emits two supertrait-clause fields with colliding
# names inside CurvePoint (Clone/Debug for Self and Self::Compressed).
# Nothing references the Self_Compressed ones; rename them so the
# structure elaborates.
s2 = s.replace(
    "  corecloneCloneInst : core.clone.Clone Self_Compressed",
    "  corecloneCloneCompressedInst : core.clone.Clone Self_Compressed")
s2 = s2.replace(
    "  corefmtDebugInst : core.fmt.Debug Self_Compressed",
    "  corefmtDebugCompressedInst : core.fmt.Debug Self_Compressed")
if s2 == s:
    print("NOTE: duplicate-field patch did not apply; "
          "check whether upstream Aeneas fixed it (then drop this patch).",
          file=sys.stderr)
open(p, "w").write(s2)
PY

echo "==> [4/4] Install generated model"
DEST="$ROOT/poker_protocol_lean/PokerProtocolLean/Aeneas/Generated.lean"
cp "$GEN" "$DEST"
echo "Installed: $DEST"
echo
echo "Next: cd poker_protocol_lean && lake build PokerProtocolLean && bash scripts/count_sorries.sh"
