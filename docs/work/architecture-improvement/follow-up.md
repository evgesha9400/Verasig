# Architecture improvement follow-up

- Date: 2026-07-21
- Integration branch: `develop`
- Final integration commit before documentation reconciliation: `8bc2072`
- Review scopes: frontend, then backend

## Cycle record

| Order | Scope / phase | Implemented strong finding | Commits |
|---:|---|---|---|
| 1 | Frontend review and implementation | Made mining mutations server-authoritative: Confirm is awaited before navigation, parser teaching invalidates stale mining state, failures remain retryable, and duplicate commands are gated. | `93ea9d6`; formatting-only follow-up `0861265`; merge `6d7bf72` |
| 2 | Backend review and cross-surface implementation | Replaced the unrevisioned latest-result cache with immutable mining inputs, stale-review rejection, feed-lock serialization, atomic signal/status/evidence confirmation, and confirmed-miss score evidence. | backend `ef32db0`; frontend contract `947017a`; ADR/domain docs `d07a289`; merge `8bc2072` |
| 3 | Artifact reconciliation | Reconciled live code, active ADRs, canonical docs, dated artifacts, and product deferrals. | This follow-up commit |
| 4 | Fresh final frontend review | `NO_STRONG_RECOMMENDATIONS` after reviewing the final current UI flow. | Evidence below |
| 5 | Fresh final backend review | `NO_STRONG_RECOMMENDATIONS` after reviewing the final current persistence and transaction flow. | Evidence below |

## Final review evidence

- Frontend: the current workflow awaits Confirm and the exact feed refresh; `reviewId` flows through Audit and Confirm; stale reviews produce an explicit re-mine path; no client miner or translator remains.
- Backend: MiningReview input hashes ordered messages, overlay, and capture generation; Confirm locks the feed, rejects stale input, and atomically commits the replacement projection, confirmed miss evidence, and `VERIFIED` status.
- Corroborated result: both fresh scope reviewers returned `NO_STRONG_RECOMMENDATIONS`; no reconciled artifact retained an unimplemented strong finding.

## Artifact reconciliation

| Classification | Artifacts / outcome |
|---|---|
| Implemented / active | [ADR 0013](../../adr/0013-mining-wizard-replaces-label-distill-verify-frontend.md) wizard outcome; [ADR 0016](../../adr/0016-remove-legacy-loop-and-regex-rule-pipeline.md) miner-only Confirm; [ADR 0017](../../adr/0017-signal-schema-collapse-and-absence-based-misses.md) single `signal` projection and absence-based misses; [ADR 0018](../../adr/0018-revisioned-mining-review.md) immutable review input; parser-overlay Phase 1 store and Manage flow. |
| Subsumed / obsolete | The former IDEAS translator item, the [dated translator spec](../../superpowers/specs/2026-07-03-mining-confirm-frontend-translator.md), and client-side parser-overlay paths are superseded by the server miner and revisioned review contract. |
| Historical | ADRs [0010](../../adr/0010-refine-codebase-structure-without-new-application-layer.md), [0011](../../adr/0011-defer-post-verify-routing-to-paid-tier.md), [0013](../../adr/0013-mining-wizard-replaces-label-distill-verify-frontend.md), [0015](../../adr/0015-mining-confirm-persists-rules-and-rederives.md), and [0016](../../adr/0016-remove-legacy-loop-and-regex-rule-pipeline.md) retain their decision-time bodies. Dated observer spec/plan/test-plan and parser-overlay plans/specs remain historical records. |
| Product-deferred | Guided per-row parser teaching; reply context; wizard top-bar and cancel-delete actions; paid-tier execution strip; local-small-model research. |
| Stale-fixed | `CONTEXT.md`, `CONVENTIONS.md`, project structure, core features, and observer data contracts now describe the live miner, MiningReview, Signal projection, and capture behavior. The ignored local `IDEAS.md` was audited for obsolete translator guidance but left untouched as protected local work. |

## Residual non-strong suggestions

| Scope | Suggestion | Trigger | Why deferred |
|---|---|---|---|
| Frontend | Add explicit parser-overlay load/error gating. | Observed GET failures or material whole-document overwrite risk. | No demonstrated failure or data-loss path. |
| Frontend | Disable Confirm after the stale banner appears. | Repeated stale-confirm clicks become a measured usability problem. | Current stale response and re-mine path are correct. |
| Frontend | Split large workflow components. | A concrete ownership, testability, or change-coupling problem. | File size alone does not pass the deletion test. |
| Frontend | Add translator, client miner, shared-contract library, or paid screens. | A product requirement or measured payload drift. | These surfaces are absent by design or product-deferred. |
| Backend | Bound mine-time memory more aggressively. | Measured large-feed memory pressure. | No current performance evidence. |
| Backend | Move Confirm to an asynchronous job. | Confirm p95 exceeds ADR 0015's approximately 10-second threshold. | Synchronous atomicity is simpler at current latency. |
| Backend | Expand job coordination. | Multi-process or multi-instance deployment. | The current deployment does not require distributed coordination. |
| Backend | Preserve and extend stale-review tests. | Any change to capture, overlay, or message mutation semantics. | This is a change guard, not a current refactor. |

## Validation

- Backend suite: 702 passed.
- Migration suite: 11 passed.
- Frontend suite: 371 passed.
- Playwright: 2 passed; 1 feed-dependent spec skipped because the authenticated account had no feeds.
- Graphify final-state result before this docs-only reconciliation: 3,707 nodes, 7,950 edges, 426 communities.
- Graphify warning: `btcusdt_known_r.json` and `bybit_linear_btcusdt_response.json` produced zero nodes; both are data fixtures, not missing code nodes, and a later update can retry them.
- `graphify-out/` is ignored and remains unstaged.
- Root `AGENTS.md` was preserved as protected untracked work.
- Ignored local `IDEAS.md` was not added, committed, or copied from the isolated worktree.
- No push or deployment was performed.
