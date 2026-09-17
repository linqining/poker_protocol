#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SAMPLES=7
INSTALL_DEPS=false
OUTPUT_DIR=""

usage() {
  cat <<'EOF'
Usage: scripts/reproduce_paper.sh [options]

Options:
  --install           Install missing pinned dependencies before running
  --output-dir DIR    Write new CSV files to DIR
                      (default: .repro/results/<UTC timestamp>)
  --samples N         WASM samples per grid cell (default: 7)
  -h, --help          Show this help

The script never overwrites the committed paper benchmark CSV files.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --install) INSTALL_DEPS=true; shift ;;
    --output-dir)
      [ "$#" -ge 2 ] || { usage >&2; exit 2; }
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --samples)
      [ "$#" -ge 2 ] || { usage >&2; exit 2; }
      SAMPLES="$2"
      shift 2
      ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
done

case "$SAMPLES" in
  ''|*[!0-9]*) printf 'error: --samples must be a positive integer\n' >&2; exit 2 ;;
esac
[ "$SAMPLES" -gt 0 ] || { printf 'error: --samples must be a positive integer\n' >&2; exit 2; }

if [ -z "$OUTPUT_DIR" ]; then
  OUTPUT_DIR="$REPO_ROOT/.repro/results/$(date -u +%Y%m%dT%H%M%SZ)"
elif [ "${OUTPUT_DIR#/}" = "$OUTPUT_DIR" ]; then
  OUTPUT_DIR="$REPO_ROOT/$OUTPUT_DIR"
fi

mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd -P)"
COMMITTED_RESULTS_DIR="$(cd "$REPO_ROOT/paper/experiments" && pwd -P)"
[ "$OUTPUT_DIR" != "$COMMITTED_RESULTS_DIR" ] || {
  printf 'error: --output-dir must not overwrite committed paper baselines\n' >&2
  exit 2
}

if [ "$INSTALL_DEPS" = true ]; then
  "$SCRIPT_DIR/install_repro_deps.sh"
else
  "$SCRIPT_DIR/install_repro_deps.sh" --check
fi

case "$(uname -s)-$(uname -m)" in
  Darwin-arm64) NODE_PLATFORM="darwin-arm64" ;;
  Darwin-x86_64) NODE_PLATFORM="darwin-x64" ;;
  Linux-arm64|Linux-aarch64) NODE_PLATFORM="linux-arm64" ;;
  Linux-x86_64|Linux-amd64) NODE_PLATFORM="linux-x64" ;;
  *) NODE_PLATFORM="unsupported" ;;
esac
TOOLS_DIR="${REPRO_TOOLS_DIR:-$REPO_ROOT/.repro/toolchains}"
LOCAL_NODE_DIR="$TOOLS_DIR/node-v24.4.1-$NODE_PLATFORM"
if [ -x "$LOCAL_NODE_DIR/bin/node" ]; then
  export PATH="$LOCAL_NODE_DIR/bin:$PATH"
fi
export PATH="${CARGO_HOME:-$HOME/.cargo}/bin:${ELAN_HOME:-$HOME/.elan}/bin:$PATH"

NATIVE_CSV="$OUTPUT_DIR/reconstruction_stark.csv"
COMPONENT_CSV="$OUTPUT_DIR/reconstruction_components.csv"
WASM_CSV="$OUTPUT_DIR/reconstruction_wasm.csv"

cd "$REPO_ROOT"
node scripts/verify_reproduction.mjs --committed

printf '[reproduce] running Rust workspace tests\n'
cargo test --workspace --locked

printf '[reproduce] measuring native reconstruction benchmark\n'
cargo run --locked -p poker-protocol-proofs --release --features borsh \
  --example reconstruction_benchmark -- "$NATIVE_CSV" "$COMPONENT_CSV"

printf '[reproduce] running WASM Node tests and release build\n'
(cd client-wasm && wasm-pack test --node --release)
(cd client-wasm && wasm-pack build --target web --release)
(cd client-wasm && wasm-pack build --target nodejs --release)

printf '[reproduce] measuring Node/V8 WASM benchmark\n'
node client-wasm/benchmark.mjs "$SAMPLES" "$WASM_CSV"

printf '[reproduce] building Lean model and checking for placeholders\n'
(cd poker_protocol_lean && lake build PokerProtocolLean)
(cd poker_protocol_lean && bash scripts/count_sorries.sh)

node scripts/verify_reproduction.mjs \
  --generated "$NATIVE_CSV" "$WASM_CSV" --samples "$SAMPLES" \
  --metadata "$OUTPUT_DIR/run_metadata.json"

printf '[reproduce] complete; new measurements are in %s\n' "$OUTPUT_DIR"
