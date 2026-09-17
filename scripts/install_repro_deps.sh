#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RUST_TOOLCHAIN="$(sed -n 's/^channel = "\([^"]*\)"/\1/p' "$REPO_ROOT/rust-toolchain.toml")"
LEAN_TOOLCHAIN="$(tr -d '[:space:]' < "$REPO_ROOT/poker_protocol_lean/lean-toolchain")"
NODE_VERSION="24.4.1"
WASM_PACK_VERSION="0.15.0"
TOOLS_DIR="${REPRO_TOOLS_DIR:-$REPO_ROOT/.repro/toolchains}"
MODE="install"

[ -n "$RUST_TOOLCHAIN" ] || { printf 'error: rust-toolchain.toml has no channel\n' >&2; exit 1; }
[ -n "$LEAN_TOOLCHAIN" ] || { printf 'error: poker_protocol_lean/lean-toolchain is empty\n' >&2; exit 1; }

usage() {
  cat <<'EOF'
Usage: scripts/install_repro_deps.sh [--check]

Without arguments, install missing pinned dependencies in user-writable
locations. --check only verifies the environment and changes nothing.

Environment:
  REPRO_TOOLS_DIR  Local toolchain directory (default: .repro/toolchains)
  CARGO_HOME       rustup/cargo home (default: $HOME/.cargo)
  RUSTUP_HOME      rustup state directory (default: $HOME/.rustup)
  ELAN_HOME        elan home (default: $HOME/.elan)
EOF
}

case "${1:-}" in
  "") ;;
  --check) MODE="check" ;;
  -h|--help) usage; exit 0 ;;
  *) usage >&2; exit 2 ;;
esac

info() {
  printf '[repro-deps] %s\n' "$*"
}

die() {
  printf '[repro-deps] error: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "$2"
}

command_version_is() {
  command -v "$1" >/dev/null 2>&1 && [ "$("$1" --version 2>/dev/null | head -n 1)" = "$2" ]
}

sha256_file() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  elif command -v openssl >/dev/null 2>&1; then
    openssl dgst -sha256 "$1" | awk '{print $NF}'
  else
    die "need shasum, sha256sum, or openssl to verify downloads"
  fi
}

load_user_paths() {
  local cargo_home="${CARGO_HOME:-$HOME/.cargo}"
  local elan_home="${ELAN_HOME:-$HOME/.elan}"
  export PATH="$cargo_home/bin:$elan_home/bin:$PATH"
}

install_rustup() {
  command -v curl >/dev/null 2>&1 || die "curl is required to install rustup"
  local temp_dir
  temp_dir="$(mktemp -d)"
  trap 'rm -rf "$temp_dir"' EXIT
  curl --proto '=https' --tlsv1.2 -fsSL https://sh.rustup.rs -o "$temp_dir/rustup-init.sh"
  sh "$temp_dir/rustup-init.sh" -y --profile minimal --default-toolchain none
  trap - EXIT
  rm -rf "$temp_dir"
  load_user_paths
}

node_platform() {
  local os arch
  os="$(uname -s)"
  arch="$(uname -m)"
  case "$os" in
    Darwin) os="darwin" ;;
    Linux) os="linux" ;;
    *) die "unsupported operating system for pinned Node: $os" ;;
  esac
  case "$arch" in
    arm64|aarch64) arch="arm64" ;;
    x86_64|amd64) arch="x64" ;;
    *) die "unsupported CPU architecture for pinned Node: $arch" ;;
  esac
  printf '%s-%s\n' "$os" "$arch"
}

local_node_dir() {
  printf '%s/node-v%s-%s\n' "$TOOLS_DIR" "$NODE_VERSION" "$(node_platform)"
}

activate_pinned_node() {
  local local_dir
  local_dir="$(local_node_dir)"
  if [ -x "$local_dir/bin/node" ]; then
    export PATH="$local_dir/bin:$PATH"
  fi
}

install_pinned_node() {
  command -v curl >/dev/null 2>&1 || die "curl is required to install Node.js"
  command -v tar >/dev/null 2>&1 || die "tar is required to install Node.js"

  local platform archive base_url temp_dir expected actual extracted_dir final_dir
  platform="$(node_platform)"
  archive="node-v${NODE_VERSION}-${platform}.tar.gz"
  base_url="https://nodejs.org/dist/v${NODE_VERSION}"
  final_dir="$(local_node_dir)"
  temp_dir="$(mktemp -d)"
  trap 'rm -rf "$temp_dir"' EXIT

  info "downloading pinned Node.js v$NODE_VERSION ($platform)"
  curl --proto '=https' --tlsv1.2 -fsSL "$base_url/SHASUMS256.txt" -o "$temp_dir/SHASUMS256.txt"
  curl --proto '=https' --tlsv1.2 -fsSL "$base_url/$archive" -o "$temp_dir/$archive"
  expected="$(awk -v name="$archive" '$2 == name {print $1}' "$temp_dir/SHASUMS256.txt")"
  [ -n "$expected" ] || die "Node.js checksum entry not found for $archive"
  actual="$(sha256_file "$temp_dir/$archive")"
  [ "$actual" = "$expected" ] || die "Node.js checksum mismatch for $archive"

  mkdir -p "$TOOLS_DIR"
  tar -xzf "$temp_dir/$archive" -C "$temp_dir"
  extracted_dir="$temp_dir/node-v${NODE_VERSION}-${platform}"
  [ -x "$extracted_dir/bin/node" ] || die "downloaded Node.js archive is incomplete"
  rm -rf "$final_dir"
  mv "$extracted_dir" "$final_dir"
  trap - EXIT
  rm -rf "$temp_dir"
  activate_pinned_node
}

install_elan() {
  command -v curl >/dev/null 2>&1 || die "curl is required to install elan"
  local temp_dir
  temp_dir="$(mktemp -d)"
  trap 'rm -rf "$temp_dir"' EXIT
  curl --proto '=https' --tlsv1.2 -fsSL \
    https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh \
    -o "$temp_dir/elan-init.sh"
  sh "$temp_dir/elan-init.sh" -y --default-toolchain none
  trap - EXIT
  rm -rf "$temp_dir"
  load_user_paths
}

load_user_paths
activate_pinned_node

require_command git "git is required (macOS: install Xcode Command Line Tools; Linux: install git)"
require_command cc "a C linker is required (macOS: run xcode-select --install; Linux: install build-essential)"

if [ "$MODE" = "install" ]; then
  require_command curl "curl is required for user-space toolchain installation"
  require_command tar "tar is required for user-space toolchain installation"
  if ! command -v rustup >/dev/null 2>&1; then
    info "installing rustup in the user account"
    install_rustup
  fi
  if ! rustup toolchain list | grep -F "$RUST_TOOLCHAIN" >/dev/null 2>&1; then
    info "installing Rust toolchain $RUST_TOOLCHAIN"
    rustup toolchain install "$RUST_TOOLCHAIN" --profile minimal --component rustfmt --component clippy
  fi
  for component in rustfmt clippy; do
    if ! rustup component list --installed --toolchain "$RUST_TOOLCHAIN" | \
      grep -E "^${component}(-|$)" >/dev/null 2>&1; then
      info "installing Rust component $component for $RUST_TOOLCHAIN"
      rustup component add "$component" --toolchain "$RUST_TOOLCHAIN"
    fi
  done
  if ! rustup target list --installed --toolchain "$RUST_TOOLCHAIN" | \
    grep -Fx wasm32-unknown-unknown >/dev/null 2>&1; then
    info "installing wasm32-unknown-unknown for $RUST_TOOLCHAIN"
    rustup target add wasm32-unknown-unknown --toolchain "$RUST_TOOLCHAIN"
  fi

  if ! command_version_is wasm-pack "wasm-pack $WASM_PACK_VERSION"; then
    info "installing wasm-pack $WASM_PACK_VERSION"
    cargo "+$RUST_TOOLCHAIN" install wasm-pack --version "$WASM_PACK_VERSION" --locked
  fi

  if ! command_version_is node "v$NODE_VERSION"; then
    install_pinned_node
  fi

  if ! command -v elan >/dev/null 2>&1; then
    info "installing elan in the user account"
    install_elan
  fi
  if ! elan toolchain list | grep -F "$LEAN_TOOLCHAIN" >/dev/null 2>&1; then
    info "installing Lean toolchain $LEAN_TOOLCHAIN"
    elan toolchain install "$LEAN_TOOLCHAIN"
  fi
fi

command -v rustup >/dev/null 2>&1 || die "rustup is missing; run this script without --check"
rustup toolchain list | grep -F "$RUST_TOOLCHAIN" >/dev/null 2>&1 || \
  die "Rust $RUST_TOOLCHAIN is missing; run this script without --check"
for component in rustfmt clippy; do
  rustup component list --installed --toolchain "$RUST_TOOLCHAIN" | \
    grep -E "^${component}(-|$)" >/dev/null 2>&1 || \
    die "Rust component $component is missing; run this script without --check"
done
rustup target list --installed --toolchain "$RUST_TOOLCHAIN" | \
  grep -Fx wasm32-unknown-unknown >/dev/null 2>&1 || \
  die "wasm32-unknown-unknown is missing for $RUST_TOOLCHAIN; run this script without --check"
command_version_is wasm-pack "wasm-pack $WASM_PACK_VERSION" || \
  die "wasm-pack $WASM_PACK_VERSION is required; run this script without --check"
command_version_is node "v$NODE_VERSION" || \
  die "Node.js v$NODE_VERSION is required; run this script without --check"
command -v elan >/dev/null 2>&1 || die "elan is missing; run this script without --check"
elan toolchain list | grep -F "$LEAN_TOOLCHAIN" >/dev/null 2>&1 || \
  die "Lean $LEAN_TOOLCHAIN is missing; run this script without --check"

info "Rust: $(rustup run "$RUST_TOOLCHAIN" rustc --version)"
info "Cargo: $(rustup run "$RUST_TOOLCHAIN" cargo --version)"
info "WASM target: wasm32-unknown-unknown"
info "$(wasm-pack --version)"
info "Node.js: $(node --version)"
info "$(elan run "$LEAN_TOOLCHAIN" lean --version | head -n 1)"
info "$(elan run "$LEAN_TOOLCHAIN" lake --version | head -n 1)"
info "dependency check passed"
