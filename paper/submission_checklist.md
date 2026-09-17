# Pre-Word submission checklist

This checklist is the review gate agreed for the current pass: finish and
confirm the implementation, proofs, data, and metadata first; generate DOCX
artifacts only after the pending user-supplied fields are filled and the items
below are explicitly accepted.

| Item | Status | Authoritative evidence | User action |
| --- | --- | --- | --- |
| Rust reconstruction implementation and attack tests | Complete | `cargo test --workspace` passed on 2026-09-17; reconstruction tamper, foreign-card veto, zero-contribution veto, and owner-key swap tests pass | Confirm |
| Browser Borsh boundary | Complete | `BrowserReconstructionV3Bundle` Borsh roundtrip and epoch-tamper rejection test pass | Confirm |
| Native benchmark grid | Complete | `paper/experiments/reconstruction_stark.csv` (11 lines: 10 measurements plus header) | Confirm |
| WASM implementation and test | Complete | `wasm-pack test --node --release` passed on 2026-09-17 | Confirm |
| WASM benchmark grid | Complete | `paper/experiments/reconstruction_wasm.csv` (11 lines: 10 measurements plus header) | Confirm |
| Theorems 1-5 | Complete | Full proofs are in `poker_protocol/reconstruction_paper.md` and mirrored in the DOCX builder source | Confirm |
| Conditional UC simulator and hybrid proof | Complete | Theorem 4 includes simulator construction, honest/corrupted submissions, and H0-H4 hybrid sequence | Confirm |
| Lean reconstruction boundary | Complete | `lake build PokerProtocolLean` passed; `count_sorries.sh` reports zero | Confirm |
| Non-owner veto theorem | Complete | `ReconstructionVeto.veto_free_extraction` and `veto_error_bound_negligible` | Confirm |
| Related-work comparison | Complete | Quantitative `d,N,r` boundary comparison with dropout-tolerant TTP-free mental poker | Confirm |
| Bibliography | Complete | 14 entries with venue, volume/pages where available, and DOI where available | Confirm |
| Submission metadata | Pending author input | `paper/submission_metadata.json`; DOCX guard rejects empty `authors` for both EN and ZH builds | Supply authors/affiliations |
| Final pre-render regression | Ready after metadata | Re-run Rust, WASM, Lean, Python syntax, and diff checks after metadata is filled | Run before DOCX |
| English and Chinese DOCX | Intentionally deferred | No DOCX generated in this pass | Generate only after checklist confirmation |

Reproduce the non-DOCX verification with:

```bash
cargo test --workspace
(cd client-wasm && wasm-pack test --node --release)
(cd client-wasm && wasm-pack build --target web --release)
(cd poker_protocol_lean && lake build PokerProtocolLean)
(cd poker_protocol_lean && bash scripts/count_sorries.sh)
```

The metadata JSON must contain a non-empty `authors` array. Each string can
include the display name and affiliation, for example `"Given Family
(Department, Institution)"`; set `corresponding_author`, `funding`, and
`acknowledgements` to `null` when not applicable.
