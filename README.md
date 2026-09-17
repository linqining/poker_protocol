# poker_protocol

Standalone crates for the mental-poker protocol, extracted from
[poker_texas_air](https://github.com/linqining/poker_texas_air).

## Layout

| Path | Crate | Description |
| --- | --- | --- |
| `poker-protocol-abi/` | `poker-protocol-abi` | Stable byte ABI for poker proof precompiles and circuit adapters |
| `poker-protocol-core/` | `poker-protocol-core` | Shared cryptographic primitives and native curve backends |
| `poker-protocol-bg/` | `poker-protocol-bg` | Curve-generic Bayer-Groth shuffle argument |
| `poker-protocol-proofs/` | `poker-protocol-proofs` | Complete proof suite for the mental-poker protocol |
| `poker_protocol/` | `poker_protocol` | Protocol request-construction API (Stark curve / Ristretto-AIR epochs) |
| `client-wasm/` | `client-wasm` | WebAssembly bridge and benchmark for browser-side reconstruction proof verification |
| `poker_protocol_lean/` | `PokerProtocolLean` | Lean 4 formalization of the protocol's proofs (Schnorr, Chaum-Pedersen, DLEQ, shuffle, reconstruction) |

The six Rust crates form a Cargo workspace (`cargo check --workspace`); the
Lean project builds independently with Lake (`lake build` in
`poker_protocol_lean/`).

## Submission metadata

Author, affiliation, correspondence, funding, and acknowledgement information
for the manuscript are centralized in `paper/submission_metadata.json`. The
DOCX builder intentionally refuses to run while `authors` is empty. The
current draft names the author but still requires affiliation, corresponding
author contact, ORCID, and final funding/acknowledgement decisions before
submission.

## Usage

```toml
[dependencies]
poker_protocol = { git = "ssh://git@github.com/linqining/poker_protocol.git", features = ["borsh", "ristretto-air"] }
poker-protocol-core = { git = "ssh://git@github.com/linqining/poker_protocol.git" }
```

## Reproduction

The reconstruction experiment grids and their host/toolchain records are in
`paper/experiments/`. Install the pinned user-space dependencies and run the
complete verification from the repository root:

```bash
./scripts/install_repro_deps.sh
./scripts/reproduce_paper.sh
```

The installer supports macOS and Linux on arm64 or x86-64. It installs the
Rust and Lean toolchains through rustup/elan, pins `wasm-pack`, and uses the
recorded Node.js release. It does not use `sudo`; when the system Node.js does
not match, it installs a checksum-verified copy under `.repro/toolchains/`.
Use `./scripts/install_repro_deps.sh --check` for a read-only environment
check, or `./scripts/reproduce_paper.sh --install` to combine both steps.

New timing grids are written under `.repro/results/`, not over the committed
paper baselines. The reproduction script first checks the committed CSV and
source hashes against `benchmark_metadata.json`, then runs Rust tests, native
and WASM measurements, Node tests, web and Node release builds, the Lean
build, the zero-placeholder audit, and structural validation of the new
grids. Each output directory also receives `run_metadata.json` with the host,
tool versions, Git state, and result hashes. Use `--output-dir DIR` to select
an output directory.

The native and WASM benchmarks use the production `RECONSTRUCT_POSEIDON`
transcript domain and report warm-start medians over seven samples. The
committed WASM grid is a Node/V8 host measurement; browser-page and mobile
device performance are not implied. See
`paper/experiments/benchmark_metadata.json` for versions, hashes, and limits.

## License

BUSL-1.1 (see [LICENSE](LICENSE)).
