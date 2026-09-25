# client-wasm

This crate exposes the repository's StarkCurve reconstruction proof to
WebAssembly. It deliberately reuses `poker-protocol-proofs`; it does not
contain a second verifier.

```bash
wasm-pack build client-wasm --target web --release --out-dir pkg-web --out-name client_wasm
(cd client-wasm && wasm-pack test --node --release)

# Build a Node/V8 package and emit the paper's WASM benchmark grid.
(cd client-wasm && wasm-pack build --target nodejs --release)
mkdir -p .repro/results/manual
node client-wasm/benchmark.mjs 30 .repro/results/manual/reconstruction_wasm.csv
```

For a pinned clean environment and the full paper verification, run
`./scripts/install_repro_deps.sh` and `./scripts/reproduce_paper.sh` from the
repository root. The full script writes fresh measurements to `.repro/`
instead of replacing the committed reference CSV.

The benchmark returns median, mean, sample-standard-deviation, and P95
prove/verify wall time together with canonical Borsh sizes for `n` cards and
`k` owner-residual carriers. Its first package is also
decoded through `BrowserReconstructionV3Bundle` and re-verified, so each run
checks the browser-to-host wire boundary as well as proof acceptance.

The committed grid is a Node/V8 host measurement, not a mobile-device or
browser-page benchmark. Host/toolchain versions, the exact command, warm-up
policy, and known measurement limits are recorded in
`paper/experiments/benchmark_metadata.json`.

To collect a real browser-page run, first build the web target:

```bash
wasm-pack build client-wasm --target web --release --out-dir pkg-web --out-name client_wasm
node client-wasm/browser_benchmark_server.mjs --host 127.0.0.1 --port 4173
```

Open the printed URL in Chrome or Safari and use a distinct `label` query value
for each environment. Add `&autorun=1` for unattended local runs. Keep the
browser, version, profile, and host in the label because the JSON is a raw
environment record. For a phone
on the same network, start the server with
`--host 0.0.0.0`, open the LAN URL printed by the script, and use a label such
as `android-chrome` or `ios-safari`. The page records browser metadata, module
initialization time, outer call time, and the same ten-cell grid; the server
writes one JSON file per run under `.repro/browser/`. These files are collected
measurements and are not substituted for the committed Node/V8 baseline.

For mobile provenance, also pass `run_state=cold|warm`, `device_model`,
`os_version`, `operator`, `network_class=wifi|cellular|ethernet|usb-tethered`,
and URL-encode their values. For a cold run add `cold_clearing_method` and
`provenance`. The page records page-load transfer/timing and manual collection
metadata with the result. Validate it before treating it as an Android Chrome
or iPhone Safari measurement:

```bash
node scripts/validate_mobile_benchmark.mjs \
  --input .repro/browser/browser_android-chrome.json \
  --device android-chrome \
  --label android-chrome-cold
```

Use `iphone-safari` for iPhone. The validator requires a manual browser page,
non-WebDriver UA/device state, actual device metadata, a declared network scope,
the full ten-cell grid, and wire sizes equal to the committed baseline. A valid
result is still an external measurement record; it does not become committed
paper evidence until added deliberately with metadata and review.

For an automated HeadlessChrome run over Chrome DevTools Protocol:

```bash
node scripts/run_browser_benchmark.mjs --samples 30 \
  --label chrome-headless --output-dir .repro/browser
```

Add `--headed` for an automated headed run with an isolated temporary profile.

Add `--memory-sampling-ms 100` for a separate Chrome run that polls CDP
`Performance.getMetrics` and records sampled renderer-JS-heap peak. The page
adds a 20 ms yield between cells so polling can run. This perturbs scheduling,
so keep memory runs separate from timing baselines and do not describe the
result as browser-process RSS or Safari/mobile memory.

The committed browser examples are
`browser_chrome_headless_153_macos_20260924.json`,
`browser_chrome_headed_153_macos_20260924.json`, and
`browser_safari_desktop_macos_20260924.json`, plus the scoped memory file
`browser_chrome_headless_memory_153_macos_20260924.json`. The Safari file was
collected by manually opening the local page in the user's normal Safari 18.3
profile; it is not an iOS measurement.

For 30 cache-disabled loopback page-load measurements:

```bash
node scripts/run_network_benchmark.mjs --runs 30 \
  --label chrome-cache-disabled-loopback-30 --output-dir .repro/network
```

Add `--upload` and use the `chrome-loopback-upload-30` label to generate,
binary-upload, and server-verify one canonical `n=52,k=13` bundle per run.

Add `--service-worker` for a warm service-worker variant. The runner first
installs `service_worker_cache.js`, then performs the requested number of
controlled upload loads. The service worker caches only the benchmark HTML,
JavaScript, and WASM; `/proof-upload` and `/network-results` always go to the
server. This measures warm cache hits, not cold install/update behavior or a
remote network path.

Add `--cold-service-worker` to measure first installation in a fresh unique
scope and Cache API name for every run. The server must observe the cold page,
worker script, HTML, JavaScript, and WASM before the result is accepted. This
does not measure service-worker update invalidation or browser HTTP-cache reuse.

Add `--service-worker-update` to keep URL, scope, and cache fixed while changing
worker bytes from version 1 to version 2. The runner requires server evidence of
both worker versions, two complete static-asset installs, activation, and
controller takeover. Browser HTTP cache remains disabled, so this is not a
normal HTTP-cache-reuse measurement.

Add `--http-cache-reuse` to measure ordinary browser HTTP-cache reuse without a
service worker. The runner seeds the cache with one immutable load, then requires
30 measured loads to report zero static transfer. Proof uploads remain
network-backed and server-verified.

For Safari, start the server with `--cache-control
'public,max-age=31536000,immutable'`, open `http_cache_benchmark.html` once to
seed, then reload for measured runs. The page generates its own session and
label fallback. These are manual desktop Safari results, not SW update or
remote-network measurements.

Add `--tls --upload` for an HTTPS/TLS loopback variant. The runner generates a
temporary self-signed RSA-2048 certificate for `127.0.0.1`, starts the server
with HTTPS, and launches Chrome with certificate-error bypass. Keep this
result separate from public-PKI, LAN, and Internet claims.
