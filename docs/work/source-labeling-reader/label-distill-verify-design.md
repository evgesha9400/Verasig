# Label, Distill, Verify — Sampling & Gate Design

**Date:** 2026-06-15

**Status:** Review draft. Records decisions from the 2026-06-15 brainstorm.

**Relationship to other docs:**

- Extends `requirements.md` (the Label/Distill/Verify loop).
- **Diverges** from `label-sampling-recommendation.md` on several axes — see §11.
- Engine stance aligns with `label-sampling-recommendation.md` §"Local LLM Stance".
- Not yet implemented. Not yet promoted to an ADR.

## 1. Purpose

- Make distilled rules **robust to provider format drift across the whole history**.
- Replace the **oldest-first** label/verify deck with a **stratified temporal** sample.
- Replace the **fixed 5/6** gate with an **adaptive, precision-driven** gate.
- Record the decision to **keep deterministic rules** and reject per-message LLM.

## 2. Chosen direction (brainstorm decisions)

| Decision | Choice |
|---|---|
| Optimization goal | Robustness to format drift across history |
| Sampling shape | Stratified temporal — **equal candidate count**, 3 strata |
| Label-count gate | **Adaptive** to confidence (soft floor, not a fixed magic number) |
| Verify gate | **Stratified precision target** (replaces zero-tolerance) |
| Free labeling | **Recent-first infinite scroll** beyond the guided sample |
| History window | **1 year** default; 6-month / All options |
| Engine | **Keep deterministic rules + LLM offline**; reject Gemma-per-message |

## 3. Sampling design

### 3.1 Strata

- Take the channel's **candidate pool** within the selected window.
- Order by `posted_at, message_id`.
- Split into **3 equal-size strata by position**: early / middle / recent.
- Equal **candidate count** per stratum, not equal calendar span.
- Rationale: uneven posting volume must not starve any era of coverage.

### 3.2 Guided sample

- Draw a **quota per stratum** (default 15) at **random within the stratum**.
- **Interleave** strata round-robin into the deck.
- Rationale: a user who stops early still labels across all eras.

### 3.3 Raw unflagged audit (carried from `label-sampling-recommendation.md`)

- Also sample some **non-candidate raw messages** (default 10) into the deck.
- Purpose: discover **filter misses** and measure recall of a recall-first filter.
- Serves the drift goal directly; **open for review** (see §12), not yet a hard gate.

### 3.4 Free scroll

- After the guided sample, allow labeling more via **newest-first infinite scroll**.
- Keyset pagination by `posted_at, message_id`; no duplicates with the guided deck.

### 3.5 History window

- Default **1 year**; dropdown for **6 months** or **All**.
- Strata and quotas are computed **within the chosen window**.

## 4. Adaptive gate design

### 4.1 Distill floor

- Unlock distillation at a **soft floor of >=12 Signal labels** (raised from 5).
- Floor is **overall**, not per-stratum (consistent with the overall precision gate).

### 4.2 Verify gate

- Verify sample is **stratified** (default 5 per stratum) over **predicted-Signal**, unlabeled rows.
- Pass when **precision >= 90%** overall on the fresh sample.
- Minimum verdicts before a pass can be evaluated: **15** (brainstorm value; see §11/§12 — sibling doc argues 20).
- Replaces the current zero-tolerance "any wrong -> loop".

### 4.3 Loop on fail

- Wrong verdicts **flip into golden labels** (current behavior, retained).
- User labels more (guided top-up or free scroll), redistills, reverifies.

## 5. Engine decision (your Q4)

| Option | Decision |
|---|---|
| Deterministic rules + Claude distill/fallback | **Keep — production path** |
| Small LLM (Gemma) classifying every message in Lambda | **Reject** |
| FunctionGemma batch triage / fine-tuned Gemma | **Defer** until measured drift justifies |

- Reject reason 1: per-message LLM judgement breaks "every score explains itself / reconstructable proof" (`PRODUCT.md`).
- Reject reason 2: per-message Lambda inference is dominated by cold-start + model load (see `label-sampling-recommendation.md` §"Local LLM Stance").
- Promote to **ADR 0012** after review.

## 6. Data flow

```text
Backfill (window: 1y default / 6mo / All)
   |  candidates = distilled FilterRule | seed heuristic
   v
Candidate pool (within window, ordered posted_at, message_id)
   |  split into 3 EQUAL-COUNT strata
   v
[ early ] [ middle ] [ recent ]   quota q/stratum (default 15) + raw-audit (default 10)
   |  random within stratum, interleaved round-robin
   v
Guided deck (~45 candidate cards + raw-audit cards)  --user labels signal/noise-->
   |                                                       want more? recent-first
   |  distill floor reached? (>=12 signals)                infinite scroll
   v
Distill (Claude -> FilterRule + ParserRules)  <----------------------------------+
   v
Stratified verify sample (5/stratum, predicted=signal, unlabeled)
   |  user: correct / wrong
   v
precision >= 90% ?  -- no --> flip wrongs into labels --> (loop back to label)
   |  yes
   v
Extract -> ... (unchanged)
```

## 7. User stories

- As a user, I label a sample spanning the channel's whole history, not just its oldest messages.
- As a user, the sample is drawn evenly from early, middle, and recent periods.
- As a user, I can scroll newest-first to label more when I want extra coverage.
- As a user, I pick the history window (1 year default, 6 months, or all).
- As a user, I proceed when rules hit a measured precision target, not a fixed count.
- As a user, I am not trapped by a single rare misclassification.
- As an operator, I can measure filter misses from unflagged raw-message audits.

## 8. Backend changes

| File | Change |
|---|---|
| `features/sources/message_repository.py` | candidate count, per-stratum random pick, newest-first keyset scroll, raw-audit pick |
| `features/rules/labeling.py` | `labeling_sample` -> stratified + interleaved within window; scroll-cursor path; raw-audit rows |
| `features/rules/verification.py` | `_sample_rows` -> stratified; `decide_pass`/`apply_verdicts` -> precision threshold; raise `MIN_VERDICTS` |
| `features/rules/label_routes.py` | `/messages` gains `window` + `cursor` params |
| `features/rules/verify_routes.py`, `verify_schemas.py` | return `precision`, `threshold`, per-stratum breakdown |
| `config.py` | thresholds + window enum centralized |

## 9. Frontend changes

| File | Change |
|---|---|
| `features/pipeline/steps/LabelView.jsx` | window dropdown; per-card stratum tag; infinite-scroll loader; adaptive gate copy (drop hard "5") |
| `features/pipeline/steps/VerifyView.jsx` | precision meter vs target; remove zero-tolerance copy; stratum breakdown |
| web API client | pass `window`/`cursor`; read `precision`/`threshold` |

- UX references: `mockups/a-focus-deck.html`, `b-refined-ledger.html`, `c-reading-stream.html`.

## 10. Tunable defaults

| Param | Default | Note |
|---|---:|---|
| Strata | 3 | equal candidate count (early/mid/recent) |
| Quota / stratum | 15 | random within stratum |
| Raw-audit rows | 10 | non-candidate, filter-miss discovery |
| Deck order | interleaved | era coverage even if user stops early |
| History window | 1 year | 6mo / All toggle |
| Distill floor | >=12 signals | raised from 5 |
| Verify sample | 5 / stratum (~15) | predicted-signal, unlabeled |
| Min verdicts | 15 | raised from 6 (sibling doc argues 20) |
| Pass threshold | >=90% precision | overall, not per-stratum |

## 11. Divergence from `label-sampling-recommendation.md`

| Axis | Recommendation doc | This design | Reconcile |
|---|---|---|---|
| Strata weighting | Recency-weighted 50/30/20 | Equal candidate count | Pick one |
| Strata basis | Time strata | Candidate-count (position) strata | Pick one |
| Label-count gate | Fixed 30 (10/10/10) | Adaptive, soft floor >=12 signals | Pick one |
| Verify minimum | 20 min / 30 target | 15 | Lean to 20 (binomial bound) |
| Verify pass rule | 0 wrong | >=90% precision overall | Pick one |
| History range UX | No manual choice in V1 | Window dropdown 1yr/6mo/All | Pick one |
| Raw audit sample | Required (10) | Carried as recommended add (§3.3) | Adopt? |
| Gemma | Defer until drift justifies | Reject per-message; defer batch | Aligned |

## 12. Open questions for review

- Equal-count strata vs the recommendation's recency-weighted 50/30/20 — which better serves drift robustness vs future relevance?
- Precision >=90% gate vs zero-tolerance — trade explainability for not trapping users; which wins?
- Verify minimum: adopt the sibling doc's **20/30** (binomial-justified) over 15?
- Adopt the **raw unflagged audit sample** as a hard gate, or keep it advisory?
- Adaptive floor vs the sibling doc's fixed 30-label gate — or a hybrid (fixed class minimums + adaptive top-up)?
- Window dropdown vs "no manual ranges in V1" — does exposing the control help or distract?

## 13. Testing (TDD, written first)

- Sampler: equal-count boundaries; quota fill; sparse-stratum fallback; window filter; interleave order; excludes labeled; raw-audit excludes candidates.
- Scroll: newest-first keyset, no dupes vs guided deck.
- Adaptive gate: floor at 12; precision math (14/15 pass, 13/15 fail); flip-wrongs intact; loop on fail.
- Frontend: window reload; scroll append; precision meter; adaptive copy.

## 14. Out of scope (separate IDEAS items)

- Reply-context display next to replies (IDEAS line 8).
- Right-panel drawer -> top progress bar redesign (IDEAS line 9).
- Design-system kebab-case / folder-naming consistency (IDEAS line 10).

## 15. References

- `docs/work/source-labeling-reader/requirements.md`
- `docs/work/source-labeling-reader/label-sampling-recommendation.md`
- `docs/adr/0002-human-assisted-rule-distillation.md`
- `docs/adr/0005-distilled-filter-and-advisory-gate.md`
- `apps/backend/src/verasig/features/rules/labeling.py`
- `apps/backend/src/verasig/features/rules/verification.py`
- `apps/backend/src/verasig/features/sources/candidate_derivation.py`
