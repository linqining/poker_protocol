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
DOCX builder intentionally refuses to run while `authors` is empty, so
generate Word artifacts only after this file has been completed and reviewed.

## Usage

```toml
[dependencies]
poker_protocol = { git = "ssh://git@github.com/linqining/poker_protocol.git", features = ["borsh", "ristretto-air"] }
poker-protocol-core = { git = "ssh://git@github.com/linqining/poker_protocol.git" }
```

## License

BUSL-1.1 (see [LICENSE](LICENSE)).
