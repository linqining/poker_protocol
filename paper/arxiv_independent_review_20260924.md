# Independent arXiv readiness review — 2026-09-24

## Verdict

The English PDF-only package is ready for an arXiv preprint submission after
the author confirms the remaining personal metadata fields. The manuscript is
in scope for `cs.CR`, states its protocol-layer boundary, separates ideal-hybrid
from concrete Fiat–Shamir claims, provides implementation and measurement
artifacts, and avoids unsupported mobile or remote-network claims.

This is not a claim of journal or conference acceptance. It is also not a
guarantee of arXiv moderation or endorsement; those are external account and
moderation processes.

## arXiv package audit

| Requirement | Current evidence | Result |
| --- | --- | --- |
| Selectable PDF | `paper/composable_privacy_preserving_deck_reconstruction.pdf` renders as 17 letter-size pages with extractable text | Pass |
| Title, author, subject, keywords | PDF metadata and `paper/arxiv_submission_fields.txt` agree | Pass |
| Abstract limits | Abstract is ASCII and 1,522 characters, below arXiv's 1,920-character limit | Pass |
| Categories | `cs.CR` primary; `cs.DC` and `cs.LO` cross-lists | Pass |
| Comments field | 18 pages, 4 figures, 11 tables, repository URL | Pass |
| License | arXiv.org perpetual, non-exclusive license 1.0 | Pass |
| Declarations | Code/data availability, separate code license, conflicts, funding, contribution, and AI-assisted workflow disclosure are present | Pass |
| Reproducibility | Committed CSV/JSON data, source hashes, browser/network baselines, refinement fixture, and reproduction scripts are present | Pass |
| Layout QA | Page-boundary scan, selectable-text extraction, figure alternative text, and PDF metadata checks pass | Pass |
| Author metadata | Affiliation, funding, and acknowledgements remain `null` | Author confirmation required |

## Closest-work positioning

Direct arXiv overlap is sparse: exact `mental poker` queries return primarily
foundational or adjacent work, while the closest full-protocol literature is
mostly on IACR ePrint or in formal proceedings. The useful comparison is
therefore protocol-layer rather than a like-for-like runtime benchmark.

| Work | Relationship to this project | Assessment |
| --- | --- | --- |
| Grigoriev and Shpilrain, “Secrecy without one-way functions,” arXiv:1301.5069 | Foundational mental-poker and secure-computation construction avoiding one-way functions | Different assumption target; this paper is a computational reconstruction layer with authenticated lineage, browser implementation, and Lean boundaries |
| ConScript, arXiv:1309.0958 | Browser participation in anonymity and verifiable-shuffle systems | Shares browser deployment interest, not Mental Poker dropout reconstruction |
| Coercion-resistant voting with FHE, arXiv:1901.02560 | Uses shuffles, ZK, and homomorphic operations in a voting threat model | Shares shuffle/ZK vocabulary; different functionality and post-quantum direction |
| Moderatorless Werewolf, arXiv:2606.00190 | Physical-card hidden-role protocol | Different game and execution medium; not a competitor to remote Mental Poker reconstruction |
| Wei and Wang, “A Fast Mental Poker Protocol,” ePrint 2009/439 | Efficient DDH-based Mental Poker baseline | This paper adds dropout reconstruction, exact carrier coverage, and a non-owner veto boundary rather than replacing a full fast dealing protocol |
| Bentov et al., “Instantaneous Decentralized Poker,” ePrint 2017/875 | Poker with penalties and cryptocurrency-backed execution | Stronger economic execution; this repository currently provides a pure settlement adapter rather than a production contract |
| David et al., “Kaleidoscope,” ePrint 2017/899 | Efficient poker with payment distribution and penalty enforcement | Full-game/economic scope; this paper is deliberately scoped to the reconstruction layer |
| Bultel and Lafourcade, secure trick-taking game protocols, ePrint 2019/375 | Enforces trick-taking rules such as following suit | Complementary rule-enforcement layer not implemented here |
| WebAssembly security literature, including arXiv:2401.05943 and arXiv:2109.01386 | Platform deployment and analysis context | This paper reports protocol measurements, but does not provide a systematic WASM side-channel or relational verification study |

## Remaining evidence gaps

1. **Mobile devices:** no Android Chrome or iPhone Safari run is committed.
2. **Remote paths:** same-source HTTP and self-signed TLS loopback upload paths are committed, but no public-PKI, LAN, Internet, or remote cold-TCP path is committed.
3. **Browser memory scope:** Chrome renderer-JS-heap peak is measured; browser-process RSS, native peak memory, Safari memory, and mobile memory are not.
4. **Service-worker and cache boundary:** isolated cold installation, same-URL byte-update invalidation, warm Cache Storage hits, immutable Chrome HTTP-cache reuse, and manual desktop Safari HTTP-cache reuse are measured over loopback, but cross-browser SW update behavior, TLS/LAN/Internet transport, and offline availability are not.
5. **Curve-level baseline scope:** a BN254 instantiation now covers curve ElGamal, cross-key, Bayer–Groth, slot OR, exact coverage, BN254 Borsh, a native host bundle verifier, and the stable native ABI route at n=52,k=13, but it is not the production Stark/Poseidon browser wire path and does not include an on-chain verifier.
6. **Chain settlement:** an explicit simulator now covers nonce replay, gas admission, candidate-state finality, and pre-finality reorg rollback, but signed transactions, mempool behavior, production gas accounting, host-consensus finality, and contract-level integration remain open.
7. **Concurrent UC NIZK:** the concrete Fiat–Shamir implementation is intentionally excluded from the concurrent UC realization claim.
8. **Adaptive corruption:** erasures or non-committing techniques remain future work.

The current manuscript is acceptable for arXiv because it states these limits
rather than extrapolating the committed measurements.
