# TIFS submission readiness checklist

This checklist separates technical-complete artifacts from author-supplied
submission metadata. The current English and Chinese DOCX drafts already
exist; they should be regenerated after metadata is finalized and before an
IEEE submission.

| Item | Status | Authoritative evidence | User action |
| --- | --- | --- | --- |
| Rust reconstruction implementation and attack tests | Complete | `cargo test --workspace` passed on 2026-09-18; reconstruction tamper, foreign-card veto, zero-contribution veto, and owner-key swap tests pass | Confirm |
| Browser Borsh boundary | Complete | `BrowserReconstructionV3Bundle` Borsh roundtrip and epoch-tamper rejection test pass | Confirm |
| Native benchmark grid | Complete | `paper/experiments/reconstruction_stark.csv` (11 lines: 10 measurements plus header) | Confirm |
| WASM implementation and test | Complete | `wasm-pack test --node --release` passed on 2026-09-18 | Confirm |
| WASM benchmark grid | Complete | `paper/experiments/reconstruction_wasm.csv` (11 lines: 10 measurements plus header) | Confirm |
| Benchmark environment record | Complete | `paper/experiments/benchmark_metadata.json` records host, toolchain, target, commands, warm-up, aggregation, and hashes for both native and WASM grids | Confirm |
| Theorems 1-5 | Complete | Full proofs are in `poker_protocol/reconstruction_paper.md` and mirrored in the DOCX builder source | Confirm |
| Conditional UC simulator and hybrid proof | Complete | Theorem 4 includes simulator construction, honest/corrupted submissions, and H0-H4 hybrid sequence | Confirm |
| Lean reconstruction boundary | Complete | `lake build PokerProtocolLean` passed; `count_sorries.sh` reports zero | Confirm |
| Non-owner veto theorem | Complete | `ReconstructionVeto.veto_free_extraction` and `veto_error_bound_negligible` | Confirm |
| Related-work comparison | Complete | Quantitative `d,N,r` boundary comparison with dropout-tolerant TTP-free mental poker | Confirm |
| Bibliography | Complete | 14 entries with venue, volume/pages where available, and DOI where available | Confirm |
| Submission metadata | Author identity complete; affiliation remains null | `paper/submission_metadata.json` contains Qining Lin, corresponding-author email, ORCID, contribution, manuscript type, and conflict-of-interest statement; affiliation, funding, and acknowledgements are null | Add an affiliation only if applicable; otherwise confirm null values before submission |
| Final pre-render regression | Passed with current metadata | Rust, WASM, Lean, zero-sorry, baseline-hash, generated-grid, syntax, and diff checks passed on 2026-09-18 | Re-run only after further manuscript or metadata changes |
| English and Chinese DOCX | Regenerated with current metadata | The English draft renders to 13 pages in two columns; the Chinese draft contains complete extractable text and renders to 12 pages | Rerender after any further metadata or template changes |

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
| P1 | Browser and mobile measurements | Missing | Desktop Chrome plus at least one Android Chrome and one iPhone Safari device report warm/cold latency, P50/P95 or spread, and environment metadata |
| P1 | Measured baseline | Complete, explicitly scoped | `paper/experiments/circom_slot_baseline.json` reports Circom 2.2.3/snarkjs 0.7.5/BN128, 2 constraints, proof bytes, witness/prove/verify times, setup assumptions, and unsupported semantics for the single-slot relation |
| P1 | Component profiling | Complete for native path | `reconstruction_components.csv` reports native residual/setup, cross-key, Bayer--Groth, slot OR, serialization, and verification stages; WASM remains an end-to-end Node/V8 measurement because the wasm32 standard library does not expose `std::time::Instant` for this internal profiler |
| P1 | Security-theorem tightening | Partial | The paper either supplies a concrete concurrently composable NIZK instantiation/reduction or narrows the UC claim to the exact hybrid assumption without suggesting end-to-end formal verification |
| P1 | Rust-to-Lean refinement | Partial, executable semantic boundary | `paper/experiments/reconstruction_refinement_vector.json`, Rust shared-vector test, Lean `RefinementVectors.vector_shape`, Borsh round-trip tests, mutation cases, and `scripts/check_refinement_vectors.sh`; this remains a semantic boundary, not full Rust byte-level refinement |
| P2 | Continuous verification | Pinned install and end-to-end local reproduction scripts complete; CI is missing | CI should invoke `scripts/reproduce_paper.sh` or equivalent Rust, WASM, Lean, and zero-sorry jobs on the pinned toolchains |
