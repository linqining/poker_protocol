# TIFS submission readiness checklist

This checklist separates technical-complete artifacts from author-supplied
submission metadata. The current English and Chinese DOCX drafts already
exist; they should be regenerated after metadata is finalized and before an
IEEE submission.

| Item | Status | Authoritative evidence | User action |
| --- | --- | --- | --- |
| Rust reconstruction implementation and attack tests | Complete | Focused `poker-protocol-proofs` reconstruction tests passed on 2026-09-20; tamper, foreign-card veto, cross-slot plaintext, and owner-key swap cases pass | Confirm |
| Browser Borsh boundary | Complete | `BrowserReconstructionV3Bundle` Borsh roundtrip and epoch-tamper rejection test pass | Confirm |
| Native benchmark grid | Complete | `paper/experiments/reconstruction_stark.csv` contains 10 grid points, 30 samples per point, median, mean, sample SD, P95, sizes, and peak allocations | Confirm |
| WASM implementation and test | Complete | `wasm-pack test --node --release` passed on 2026-09-18 | Confirm |
| WASM benchmark grid | Complete | `paper/experiments/reconstruction_wasm.csv` contains 10 Node/V8 grid points, 30 samples per point, median, mean, sample SD, and P95 | Confirm |
| Benchmark environment record | Complete | `paper/experiments/benchmark_metadata.json` records host, toolchain, target, commands, warm-up, aggregation, and hashes for both native and WASM grids | Confirm |
| Theorems 1-5 | Complete at the stated model boundary | Proof arguments and concrete/ideal claim separation are in `build_paper_docx.py` and the generated English DOCX | Confirm |
| Ideal-NIZK hybrid simulator and composition proof | Complete | Theorem 4 defines the simulator and hybrids in `F_NIZK^R_RECON`; it explicitly excludes a concrete Fiat-Shamir-to-UC realization claim | Confirm |
| Lean reconstruction boundary | Complete | `lake build PokerProtocolLean` passed on 2026-09-20 (3477 jobs); `count_sorries.sh` reports zero | Confirm |
| Non-owner veto theorem | Complete | `ReconstructionVeto.veto_free_extraction` and `veto_error_bound_negligible` | Confirm |
| Related-work comparison | Complete | Quantitative `d,N,r` boundary comparison with dropout-tolerant TTP-free mental poker | Confirm |
| Bibliography | Complete | 40 entries covering Mental Poker, shuffles, NIZK/Fiat-Shamir boundaries, formal verification, secure aggregation, TIFS precedents, and WebAssembly/SNARK deployment | Confirm |
| Submission metadata | Author identity complete; affiliation remains null | `paper/submission_metadata.json` contains Qining Lin, corresponding-author email, ORCID, contribution, manuscript type, and conflict-of-interest statement; affiliation, funding, and acknowledgements are null | Add an affiliation only if applicable; otherwise confirm null values before submission |
| Final pre-render regression | Passed with current metadata | Focused Rust tests, Lean build, zero-sorry audit, baseline and generated-grid validation, Python/Node syntax, DOCX package integrity, and diff checks passed on 2026-09-20 | Re-run after further manuscript, benchmark, or metadata changes |
| English and Chinese DOCX | Rendered and visually checked | English renders to 13 letter-size pages in two columns; Chinese renders to 12 pages with complete extractable text | Transfer the English content to the official IEEE template before submission |

Reproduce the non-DOCX verification with:

```bash
./scripts/install_repro_deps.sh
./scripts/reproduce_paper.sh
```

The installer is user-space only and pins the recorded Rust, Lean, Node.js,
`wasm-pack`, Circom 2.2.3, and snarkjs 0.7.5 versions. The reproduction runner preserves the committed
paper CSV files, verifies their recorded hashes, emits fresh measurements
under `.repro/results/`, and validates the new parameter grids and canonical
proof/statement sizes. Each run also records the host, tool versions, Git
state, and result hashes in `run_metadata.json`. Use
`./scripts/install_repro_deps.sh --check` when only an environment audit is
desired.

The metadata JSON must contain a non-empty `authors` array. Each string can
include the display name and affiliation, for example `"Given Family
(Department, Institution)"`; set `corresponding_author`, `funding`, and
`acknowledgements` to `null` when not applicable.

The WASM measurements are explicitly Node/V8 host measurements. They should
not be described as Android/iOS or browser-device measurements unless those
experiments are run and their environment records are added separately.

## Outstanding evidence and submission work

| Priority | Item | Current status | Completion criterion |
| --- | --- | --- | --- |
| P0 | Author metadata | Corresponding-author identity complete; affiliation remains null | Confirm that no affiliation, funding, or acknowledgements should be listed; do not invent missing fields |
| P0 | IEEE TIFS packaging | Draft two-column package complete; official template transfer remains | `paper/composable_privacy_preserving_deck_reconstruction.docx` renders as a 13-page two-column English manuscript with numbered/captioned tables and figures; final IEEE Word/LaTeX template transfer and affiliation confirmation remain |
| P0 | Equation objects | Pending final IEEE template transfer | Current DOCX uses centered, readable equation paragraphs; convert them to native OMML or template-native equations during final Word/LaTeX packaging and re-run visual QA |
| P0 | Claim discipline | Complete for current data | Node/V8 results remain explicitly separated from browser/mobile-device claims |
| P1 | Browser and mobile measurements | Missing | Desktop Chrome and Safari plus at least one Android Chrome and one iPhone Safari device report warm/cold latency, P50/P95 or spread, browser peak memory where available, and environment metadata |
| P1 | Measured baseline | Complete, explicitly scoped | `paper/experiments/circom_slot_baseline.json` reports Circom 2.2.3/snarkjs 0.7.5/BN128, 2 constraints, proof bytes, witness/prove/verify times, setup assumptions, and unsupported semantics for the single-slot relation |
| P1 | Component profiling | Complete for native path | `reconstruction_components.csv` reports native residual/setup, cross-key, Bayer--Groth, slot OR, serialization, and verification stages; WASM remains an end-to-end Node/V8 measurement because the wasm32 standard library does not expose `std::time::Instant` for this internal profiler |
| P1 | Security-theorem tightening | Complete at the claimed boundary | The composition theorem is explicitly limited to the session-bound `F_NIZK^R_RECON` hybrid; the concrete cumulative Poseidon Fiat-Shamir implementation is evaluated separately and is not claimed to realize concurrent UC NIZK |
| P1 | Formal `F_RECON` interface | Complete | The manuscript specifies `INIT`, `SUBMIT`, `STATUS`, `DEADLINE`, duplicate/replay behavior, leakage, static corruption, deadline handling, and cross-epoch `sid` binding |
| P1 | Network experiment | Missing | Report package upload plus verification latency over at least one controlled LAN and one Internet path, without conflating network latency with proof verification |
| P1 | Rust-to-Lean refinement | Partial, executable semantic boundary | `paper/experiments/reconstruction_refinement_vector.json`, Rust shared-vector test, Lean `RefinementVectors.vector_shape`, Borsh round-trip tests, mutation cases, and `scripts/check_refinement_vectors.sh`; this remains a semantic boundary, not full Rust byte-level refinement |
| P2 | Continuous verification | Pinned install and end-to-end local reproduction scripts complete; CI is missing | CI should invoke `scripts/reproduce_paper.sh` or equivalent Rust, WASM, Lean, and zero-sorry jobs on the pinned toolchains |
