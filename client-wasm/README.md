# client-wasm

This crate exposes the repository's StarkCurve reconstruction proof to
WebAssembly. It deliberately reuses `poker-protocol-proofs`; it does not
contain a second verifier.

```bash
wasm-pack build client-wasm --target web --release
(cd client-wasm && wasm-pack test --node --release)

# Build a Node/V8 package and emit the paper's WASM benchmark grid.
(cd client-wasm && wasm-pack build --target nodejs --release)
node client-wasm/benchmark.mjs 7 paper/experiments/reconstruction_wasm.csv
```

The benchmark returns median prove/verify wall time and canonical Borsh sizes
for `n` cards and `k` owner-residual carriers. Its first package is also
decoded through `BrowserReconstructionV3Bundle` and re-verified, so each run
checks the browser-to-host wire boundary as well as proof acceptance.
