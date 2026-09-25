# Independent arXiv and ePrint review — 2026-09-25

## Scope and evidence

This is a second independent review of the English manuscript after the
signed simulated-chain work. It uses the current repository, the existing
benchmark and reproducibility records, arXiv's public search API, and the
following IACR ePrint records checked directly on 2026-09-25:

* Beaver, **Extending Mental Poker**, ePrint 2025/1821.
* Wei and Wang, **A Fast Mental Poker Protocol**, ePrint 2009/439.
* Bentov, Kumaresan, and Miller, **Instantaneous Decentralized Poker**, ePrint
  2017/875.
* David, Dowsley, and Larangeira, **Kaleidoscope**, ePrint 2017/899.
* Bultel and Lafourcade, **Secure Trick-Taking Game Protocols**, ePrint
  2019/375.

The arXiv API query for all fields containing “mental poker” returned one
paper: Grigoriev and Shpilrain, arXiv:1301.5069. Adjacent arXiv work was also
considered where it shares verifiable shuffles, browser deployment, SNARK
benchmarks, or robust aggregation, but none implements the same authenticated
residual-carrier reconstruction functionality.

## Verdict

**arXiv PDF-only submission:** ready; the final regression and PDF rebuild
caused by this review round have passed. The paper has a clear contribution,
ASCII abstract, primary `cs.CR` category, repository and data links, license,
19-page preprint packaging, explicit limitations, and reproducible artifacts.
Final moderation remains external to this repository.

**IACR ePrint submission:** technically suitable in scope after author
confirmation. ePrint is not peer review and provides no acceptance guarantee.
The paper states that it is a reconstruction layer, not a complete poker
game, and should not compare raw timings directly with incompatible
full-game protocols.

**Peer-reviewed top-venue acceptance:** not yet established. The artifact
base is unusually complete for a preprint, but the remaining evidence and
formalization gaps below are likely to be raised in review.

## arXiv standard audit

| Standard item | Result |
| --- | --- |
| Selectable-text PDF | Current 19-page PDF passes; final rebuild performed after this round |
| Title, author, abstract, keywords | Present and internally consistent |
| Abstract | ASCII and below arXiv's 1,920-character limit |
| Primary and cross categories | `cs.CR`; `cs.DC` and `cs.LO` |
| Comments field | Must be regenerated if the rebuilt page, figure, or table count changes |
| License | arXiv non-exclusive license 1.0 recorded |
| Data and code availability | Repository, benchmark grids, schemas, hashes, and scripts present |
| Claims/limits separation | Node/V8, Chrome, desktop Safari, loopback transport, simulator, and Lean boundaries are separated |
| Author metadata | Affiliation and funding are intentionally null pending author confirmation |
| Signed settlement simulation | Implemented and tested, but clearly not a deployed chain adapter |

## Comparison with closest work

| Work | Closest overlap | This manuscript | Differentiator |
| --- | --- | --- | --- |
| Beaver, 2025/1821 | Mental Poker foundations, OT extension, two-player and physical-card settings | Multiplayer aggregate-key reconstruction after reveal-token dropout | Beaver is foundational and focuses on OT amplification/base OT; this paper proves and measures a state-bound per-slot reconstruction package |
| Wei and Wang, 2009/439 | DDH-based fast full Mental Poker dealing | Full proof components, implementation, and browser measurements | Different objective: this paper does not replace the dealing lifecycle and should not be ranked by incompatible full-game timings |
| Bentov et al., 2017/875 | Stateful contracts, penalties, cryptocurrency execution | Pure deadline policy, ledger, and signed simulated transaction host | Prior work is a stronger economic/chain design; this work remains explicitly not a deployed contract |
| Kaleidoscope, 2017/899 | Efficient poker with payouts and penalties | Deadline settlement proposal and escrow invariants | Prior work covers fuller economic lifecycle; this paper covers reconstruction authorization and exact carrier coverage |
| Bultel and Lafourcade, 2019/375 | Rule-compliant online card games | Proof that the next aggregate-key deck can be safely reconstructed | Rule enforcement and dropout reconstruction are complementary layers |
| Grigoriev and Shpilrain, arXiv:1301.5069 | Mental Poker without one-way functions | Computational curve assumptions, NIZKs, browser code | Different assumption target and deployment layer |

The fair conclusion is not that this paper is uniformly faster or more
complete than these systems. Its novel contribution is the residual-carrier
semantics and the measurable implementation of that reconstruction layer.

## Strengths

1. The protocol claim is precise: exact carrier coverage, hidden mapping,
   slot-local zero-or-negative membership, and authenticated owner-residual
   lineage.
2. The ideal-NIZK composition result is separated from the concrete
   Poseidon Fiat–Shamir implementation, avoiding an unsupported concurrent-UC
   claim.
3. Native grids, WASM end-to-end grids, native component profiling, scoped
   Circom/Groth16 baselines, and a same-relation BN254 baseline are committed.
4. Browser evidence now includes automated Chrome, desktop Safari, cache
   states, service-worker installation/update, and loopback HTTP/TLS upload
   experiments with explicit scopes.
5. Lean provides a zero-sorry semantic and schema-boundary check, not an
   overclaimed complete implementation refinement.
6. The settlement simulation now checks Schnorr authenticity, canonical
   sender/public-key binding, identity-key rejection, nonzero deployment-domain
   binding, tampering, transaction-hash binding, a versioned reference adapter
   envelope, nonce replay, gas admission, finality, and reorg rollback.

## QA completed after this review round

1. The full Rust workspace and WASM Node tests pass after the
   signed-settlement edits.
2. The DOCX/PDF were rebuilt with an explicit concrete-security parameter
   table; the PDF is now 19 pages and its key pages, metadata, selectable
   text, and date were checked.
3. The final checklist now records signed transactions as simulated and
   explicitly excludes production chain consensus.
4. Author affiliation and funding remain `null`; the author must still confirm
   that intentional state before upload.

## Detailed remaining weaknesses

1. **Mobile evidence is absent.** Android Chrome and iPhone Safari are not
   measured. Current browser results must remain desktop-scoped.
2. **Realistic network deployment is absent.** No public-PKI, LAN, Internet,
   or remote cold-TCP path is committed. Loopback HTTP/TLS controls transport
   but not production latency.
3. **Complete-game comparison remains qualitative.** Wei/Wang, Kaleidoscope,
   ROYALE, and Instantaneous Decentralized Poker solve broader game/economic
   lifecycles. The manuscript correctly avoids fake end-to-end timing, but a
   reviewer may still ask for a common operation-count or proof-size model.
4. **Concrete FS/UC separation is both a strength and a limitation.** The
   paper does not prove that the Poseidon transcript realizes concurrent UC
   NIZK. That is honest, but top-venue reviewers may ask for a FS-extraction
   proof under explicit assumptions or a standard-model alternative.
5. **Chain integration remains simulated.** The signed simulator, deployment
   digest, and versioned PSTX reference envelope are stronger than the prior
   digest model, but there is no deployed contract, real mempool, production
   gas accounting, consensus finality, or on-chain BN254 verifier.
6. **Assurance boundary is incomplete.** Lean does not verify group
   arithmetic, DDH, Bayer–Groth knowledge soundness, ROM/FS security, or every
   production serialization path. This is disclosed, but it is not a complete
   verified protocol implementation.
7. **Adversarial scope is narrower than some applications require.** Static
   corruption, authenticated state, and the current authorization policy are
   assumed. Adaptive corruption, threshold removal for jointly keyed
   residuals, and malicious-host availability policy remain future work.
8. **Platform side channels are not studied.** The paper measures time and
   scoped memory, but does not claim a systematic WebAssembly timing, cache,
   GC, or power side-channel analysis.
9. **Runtime variance and device diversity are limited.** One macOS host
   class dominates the native/browser evidence. Different architectures,
   CPU budgets, browser versions, and mobile network conditions are absent.
10. **PDF-only source is acceptable but less reusable.** arXiv permits PDF
    submission, yet LaTeX source would make equations and tables easier for
    reviewers and future revisions.

## Recommended priority

| Priority | Item | Why it matters |
| --- | --- | --- |
| P0 | Final rebuild and claim audit | Complete after the 19-page, 12-table rebuild and claim audit |
| P1 | Android Chrome and iPhone Safari | Mobile audit harness is ready for device runs; actual Android/iPhone evidence is still required before any mobile claim |
| P1 | LAN and Internet public-PKI paths | Measurement harness is ready, including optional cold-browser-process TCP isolation and system-store TLS certificate audit; it explicitly avoids public-PKI overclaim. Controlled deployed evidence is still missing |
| P1 | Structured comparison to full-game protocols | Addresses the likely “where is the complete poker game?” question without invented timing |
| P1 | Explicit concrete-security parameter table | Complete: Table V now separates curve/challenge parameters and theorem error bounds without assigning unsupported numeric advantages |
| P2 | Contract adapter and on-chain verifier | Closes the signed-simulator/deployment gap |
| P2 | Adaptive corruption or non-committing proofs | Broadens the security model |
| P2 | WASM side-channel study | Important for browser deployment but separable from correctness/soundness |

The manuscript is not blocked by invention of a new shuffle or SNARK
compiler: its contribution is the authenticated reconstruction semantics and
an unusually auditable implementation boundary. For arXiv/ePrint, the package
is credible when its limits remain explicit. For a high-bar peer-reviewed
venue, mobile, real-network, and complete-game positioning remain the largest
external evidence gaps.
