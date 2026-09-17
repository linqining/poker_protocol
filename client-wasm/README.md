# client-wasm

This crate exposes the repository's StarkCurve reconstruction proof to
WebAssembly. It deliberately reuses `poker-protocol-proofs`; it does not
contain a second verifier.

```bash
wasm-pack build client-wasm --target web --release
(cd client-wasm && wasm-pack test --node --release)

# Build a Node/V8 package and emit the paper's WASM benchmark grid.
(cd client-wasm && wasm-pack build --target nodejs --release)
mkdir -p .repro/results/manual
node client-wasm/benchmark.mjs 7 .repro/results/manual/reconstruction_wasm.csv
```

For a pinned clean environment and the full paper verification, run
`./scripts/install_repro_deps.sh` and `./scripts/reproduce_paper.sh` from the
repository root. The full script writes fresh measurements to `.repro/`
instead of replacing the committed reference CSV.

The benchmark returns median prove/verify wall time and canonical Borsh sizes
for `n` cards and `k` owner-residual carriers. Its first package is also
decoded through `BrowserReconstructionV3Bundle` and re-verified, so each run
checks the browser-to-host wire boundary as well as proof acceptance.

The committed grid is a Node/V8 host measurement, not a mobile-device or
browser-page benchmark. Host/toolchain versions, the exact command, warm-up
policy, and known measurement limits are recorded in
`paper/experiments/benchmark_metadata.json`.
