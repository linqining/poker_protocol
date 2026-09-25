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

## Preprint metadata

Author, affiliation, correspondence, funding, acknowledgement, and arXiv
metadata for the manuscript are centralized in
`paper/submission_metadata.json`. The DOCX builder intentionally refuses to
run while `authors` or required `arxiv` fields are empty. It emits the English
DOCX, a Chinese translation, and `paper/arxiv_submission_fields.txt` for the
arXiv submission form. The current preprint uses cs.CR as its primary subject
and arXiv.org perpetual, non-exclusive license 1.0 for the article.

`scripts/build_paper_latex.py` additionally emits a standalone
XeLaTeX source at
`paper/composable_privacy_preserving_deck_reconstruction.tex` from the current
English DOCX. The generated file contains the abstract, all 12 tables, four
figure references, declarations, appendix, and 49 bibliography entries in one
`.tex` file. Regenerate it with:

```sh
python3 scripts/build_paper_latex.py
```

The repository-local TinyTeX toolchain used for validation is kept under
`.repro/toolchains/tinytex` (not committed). Compile the generated source with:

```sh
cd paper
../.repro/toolchains/tinytex/bin/universal-darwin/xelatex \
  -interaction=nonstopmode -halt-on-error \
  -jobname=composable_privacy_preserving_deck_reconstruction_latex \
  composable_privacy_preserving_deck_reconstruction.tex
```

The checked local build produces
`paper/composable_privacy_preserving_deck_reconstruction_latex.pdf` (29 pages).
The current build log has no missing-character, unresolved-citation,
undefined-reference, overfull-hbox, or oversized-float warnings. A submission
source package must include the generated TeX file with `paper/figures/`.

The clean upload folder is `paper/arxiv_upload/`. Its root contains
`main.tex` and the only required asset directory, `figures/`; it intentionally
contains no PDF, log, auxiliary, DOCX, or repository-data files. The checked
ZIP mirror is `paper/arxiv_upload.zip`.

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
transcript domain and report the median, arithmetic mean, sample standard
deviation, and nearest-rank P95 over 30 warm-start samples. The committed
WASM grid is a Node/V8 host measurement. Separate committed JSON files record
30-sample HeadlessChrome and automated headed Chrome 153 page runs collected
through Chrome DevTools Protocol, plus one user-normal desktop Safari 18.3
run. A separate Chrome run samples renderer-JS-heap peak through CDP; Android,
iOS, browser-process RSS, and Safari/mobile memory are not implied.
See
`paper/experiments/benchmark_metadata.json` for versions, hashes, and limits.
`client-wasm/README.md` describes the browser harness and the automated CDP
runner.

The browser page also supports auditable mobile measurements. Serve it on a
LAN, open the printed URL in Android Chrome or iPhone Safari, and include
`run_state`, `device_model`, `os_version`, `operator`, `network_class`, and—for
cold runs—`cold_clearing_method` and `provenance` query fields. The result
records manual-provenance, page-load transfer/timing, initialization, and the
full ten-cell grid. Validate the saved JSON with:

```bash
node scripts/validate_mobile_benchmark.mjs \
  --input .repro/browser/browser_MOBILE.json \
  --device android-chrome \
  --label android-chrome-cold \
  --samples 30
```

Use `iphone-safari` for iPhone Safari. The validator enforces the committed
wire sizes, non-automation, device/environment metadata, and a nonempty
operator-declared network scope; it does not turn a self-reported result into a
committed paper measurement.

Two scoped Circom/Groth16 baselines are also committed. The original circuit
covers one slot-selector relation, while `circom_multislot_relation.circom`
covers the 52-slot, 13-carrier finite-domain `{0,-card}` and exact-coverage
semantics. Neither claims to implement curve ElGamal, cross-key group proofs,
Bayer-Groth shuffling, or authenticated protocol composition.

A stronger BN254 curve-level baseline instantiates the same reconstruction
relation with curve ElGamal, cross-key proofs, Bayer-Groth, slot OR proofs,
and exact coverage. A BN254 Borsh codec covers the measured primary-shape wire
package. The stable precompile ABI accepts the BN254 reconstruction route, and
native ABI/bundle verifiers roundtrip and verify encoded requests. The committed
result uses SHA3 Fiat–Shamir; it is not the production Stark/Poseidon browser
wire path or an on-chain verifier.

The Rust--Lean refinement fixture covers the complete deterministic
`ReconstructionStatement<StarkCurve>` Borsh v3 schema and one seeded
`ReconstructProof` instance: 1,041 statement bytes across eleven fields and
3,829 proof bytes across seven top-level plus thirty nested fields, with exact
prefixes and SHA-256 digests. Fresh proof bytes remain randomized rather than
canonical.

`poker_protocol::reconstruction_policy` provides a pure, testable deadline and
deposit accounting model. It emits settlement proposals after cryptographic
verification; it does not itself verify proofs or execute chain transactions.
`reconstruction_settlement` defines the adapter boundary and includes an
in-memory reference ledger that enforces exact escrow matching, compensation
conservation, idempotent retries, and same-epoch conflict rejection.
`SimulatedChainSettlementHost` additionally models transaction nonces, gas
admission, Stark-curve Schnorr signed-transaction admission, sender/public-key
binding with canonical lowercase sender encoding, identity-key rejection, tamper
rejection, nonzero deployment-digest binding to reject cross-adapter replay,
transaction-hash binding, canonical PSTX adapter-envelope roundtrip,
candidate-versus-committed state, confirmation depth, and pre-finality reorg
rollback; it is a test model, not a blockchain integration or public chain
standard.
Production deployment digests should be derived with
`settlement_deployment_digest_from_parts(chain_id, contract_address,
adapter_version)`, which domain-separates and length-prefixes each identity
part.
`validate_settlement_proposal` exposes the same arithmetic, ordering, missed
list, and conservation checks to chain adapters before escrow execution.
The canonical PSTX v1 known-answer vector is committed at
`paper/experiments/settlement_pstx_v1_kat.json`; `verify_pstx_kat.mjs` checks
its bytes, metadata, invariants, and agreement with the Rust source vector.

`scripts/run_network_benchmark.mjs` performs 30 cache-disabled loopback page
loads and records HTML/JavaScript/WASM transfer bytes, server-sent body bytes,
resource timing, module initialization, and one `n=52,k=13` proof per run. The
committed result is controlled local evidence, not proof-upload, LAN, or
Internet performance.

With `--upload`, the same runner generates the canonical 27,750-byte
statement/proof bundle, uploads it as binary HTTP/1.1 data, and requires the
server to decode and cryptographically verify it. The committed upload result
remains loopback-only; it does not measure cold TCP, TLS, LAN, or Internet
transport.

With `--service-worker`, the runner first installs a same-origin cache for the
benchmark HTML, JavaScript, and WASM, then performs 30 warm upload loads.
Static-resource transfer is zero in every committed run, while proof upload and
result submission bypass the cache and remain server-verified. This does not
measure cold service-worker installation, update invalidation, browser
HTTP-cache behavior, TLS, LAN, or Internet transport.

With `--cold-service-worker`, each run uses a unique page scope, worker-script
query, and Cache API name. The committed 30-run result fetches the page, worker,
HTML, JavaScript, and WASM from the server every time, caches 273,188 bytes, and
reports median/P95 total installation of 41.2/64.2 ms. It does not measure
update invalidation or browser HTTP-cache reuse.

With `--service-worker-update`, each run keeps URL, scope, and Cache API name
fixed while the server changes worker bytes from version 1 to version 2. The
committed 30-run result verifies both worker versions, two complete asset
installs, controller takeover, and median/P95 total update of 1,066.2/1,149.0 ms.
It still does not measure normal browser HTTP-cache reuse or remote transport.

With `--http-cache-reuse`, the server marks benchmark assets immutable, one seed
load populates the normal browser HTTP cache, and 30 measured loads reuse it
without a service worker. Static transfer is zero while proof upload remains
network-backed and server-verified. This does not test TLS, LAN, Internet, or
cross-browser cache policy.

A separate manual Safari 18.3 HTTP-cache run records 30 warm loads with zero
static transfer and server-verified proof uploads. It is desktop evidence only;
it does not cover SW update invalidation or remote transport.

With `--tls --upload`, the runner generates a temporary self-signed RSA-2048
certificate for `127.0.0.1`, serves the same benchmark over HTTPS, and instructs
Chrome to ignore the self-signed certificate error. The committed same-source
HTTP/TLS pair reports identical transfer byte totals and median/P95 upload wall
times of 544.3/706.9 ms and 549.5/771.0 ms. This is local TLS evidence, not
public PKI, LAN, or Internet performance.

For an external experiment, the same upload benchmark can now run against a
server started elsewhere with
`node client-wasm/browser_benchmark_server.mjs --host 0.0.0.0 --tls 1 ...`:

```bash
node scripts/run_network_benchmark.mjs --upload \
  --remote-server-url https://bench.example.invalid \
  --network-class internet \
  --require-valid-certificate \
  --runs 30 --label remote-internet-upload-30
```

The runner records the remote origin, the declared LAN/Internet class,
transport, browser certificate-validation mode, cache state, per-run code
download bytes, and the server-verified 27,750-byte upload.

With `--require-valid-certificate`, the runner independently validates the
server chain with the Node system trust store, verifies the hostname, and
records subject, issuer, validity dates, SANs, and SHA-256 fingerprint. This is
stronger than ignoring a browser warning, but the aggregate still deliberately
records `public_pki_claimed: false` because deployment identity and CA policy
must be stated by the controlled experiment. In default remote mode it records
`cold_tcp_isolated: false`; until a run from an explicitly controlled
deployment is committed, this remains harness support, not remote-path evidence.

For a controlled cold-connection experiment, add `--cold-browser-process`.
Each measured run then uses a new Chrome process and temporary profile, the
previous process must exit before the next run starts, and the aggregate records
`cold_tcp_isolated: true`. This isolates browser TCP state, but still does not
by itself prove a public-PKI deployment.

## License

BUSL-1.1 (see [LICENSE](LICENSE)).

The manuscript uses arXiv’s non-exclusive distribution license; BUSL-1.1
continues to govern the repository implementation.
