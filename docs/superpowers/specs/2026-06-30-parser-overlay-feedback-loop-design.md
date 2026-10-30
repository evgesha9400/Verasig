# Design — "Teach the parser" feedback loop (parser overlay)

Date: 2026-06-30
Status: approved (brainstorm), pending implementation plan
Area: Template Mining (`apps/frontend/web/src/{domain,features}/template-mining`, `apps/backend`)

## Context

The parser-first Template Mining feature classifies every message of a feed into
five audit buckets (`applyAcceptedRules` in
`apps/frontend/web/src/domain/template-mining/rules.js`):

- **Parsed** — new-signal of an accepted template, confidence ≥ threshold.
- **Ambiguous** — accepted format but confidence below threshold.
- **Rejected** — update/result/commentary, or a reject-phrase hit.
- **Rare** — new-signal of a non-accepted format.
- **Misses** — partial evidence (instrument XOR direction, or prices + a trading label).

The classifier is fully deterministic (no LLM). Today its knowledge is hard-coded:
coin aliases/tickers in `instruments.js`, direction words/emoji in `directions.js`,
label vocab in `fields.js`, reject phrases in `rules.js`, and a derived per-template
confidence threshold (`deriveThreshold`). When a real signal is **missed** (a coin
or direction the detectors don't know) or **noise leaks into Parsed**, there is no
way for a user to correct it — and the review (`AuditReview.jsx`) is read-only.

This feature adds a feedback loop: a verdict on a review row becomes a **persistent,
account-level edit to the deterministic parser**, so corrections stick across runs
and across all of the user's feeds.

## Goal

Recover missed real signals and exclude noise by letting the reviewer teach the
parser, durably. Improvements raise precision/recall on every subsequent mine, for
every feed of that account.

## Non-goals (v1)

- No LLM / ML. All learning is explicit, deterministic overlay data.
- No intent-marker editing and no entry/stop/target label-vocabulary teaching
  (deferred — "Intent & label fixes" is a later phase).
- No per-feed overlay scoping — the overlay is account-level (applies to all feeds).
- No template-merge tooling beyond the existing accept flow.

## Decisions (from brainstorm)

- Feedback **durably teaches the parser** (not session-only).
- Overlay persists in the **backend, per account**.
- Interaction is **hybrid**: per-row suggested fixes + a manage/undo panel.
- v1 levers: **vocabulary** (coin alias + direction token), **reject phrases**,
  **per-template threshold**. (Rare recovery uses the existing accept flow.)

## Architecture

Data flow: `backend overlay  ⇄  page fetch  →  parser merge (mine + audit)  →
review  →  verdict  →  PUT overlay  →  re-mine`.

Three units, each independently testable:

### 1. Overlay store (backend, per account)

- New table `parser_overlay`: `user_id` (PK, FK → `user_account`), `data` (jsonb),
  `updated_at`. One row per account. Alembic migration `0012_parser_overlay`
  (down_revision `0011_generic_source`).
  - Note: the archived `lab` branch also has a `0012_*`; lineages are separate and
    that branch is archived. If it is ever revived, one of the two `0012`s is renamed.
- `data` shape (account-level; applies to every feed):

  ```json
  {
    "instrumentAliases": { "<ALIAS>": "<SYMBOL>" },
    "directionTokens":   { "<TOKEN>": "BUY" | "SELL" },
    "rejectPhrases":     ["<phrase>"],
    "templateThresholds":{ "tpl_<hash>": 0.0 }
  }
  ```

- API (auth like the rest, `require` current user):
  - `GET /parser-overlay` → `{ data }` (empty default if none).
  - `PUT /parser-overlay` with `{ data }` → replace and return it. The document is
    small, so whole-document replace is simpler than granular endpoints.
- Rationale for a JSON document over normalized tables: the overlay is a small,
  evolving, account-scoped settings blob read and written as a whole. A document
  avoids per-lever migration churn. Validation lives in a Pydantic schema.

### 2. Parser merge (frontend domain — stays pure)

The detectors currently read module-level constants. Add an **optional `overlay`
argument** threaded through the pipeline; absent → today's behavior (backwards
compatible). The domain never fetches the overlay — the page passes it in.

- `detectInstruments(text, overlay)` — merge `overlay.instrumentAliases` over the
  seeded alias map.
- `detectDirections(text, overlay)` — merge `overlay.directionTokens` (emoji/word →
  BUY/SELL) over the seeded matchers.
- `attemptExtractSignal(input, overlay)` and `mineTemplateGroups(messages, overlay)`
  — thread `overlay` to the detectors.
- `applyAcceptedRules(messages, rules, overlay)` — append `overlay.rejectPhrases`
  to each rule's `rejectIfContains`; if `overlay.templateThresholds[templateKey]`
  exists, it overrides `deriveThreshold` for that template.

`templateKey` is a hash of the normalized skeleton (stable across feeds), so a
threshold override is portable.

### 3. Feedback UI (frontend — in `AuditReview.jsx`) — hybrid

Per-row **suggested fix** (in the expanded row detail), driven by a diagnosis of
why the row sits in its bucket:

| Row bucket | Verdict | Diagnosis → suggested overlay edit |
|---|---|---|
| Miss (instrument found, direction missing) | "is a signal" | choose the unrecognized token in the message → map to BUY/SELL (`directionTokens`) |
| Miss (direction found, instrument missing) | "is a signal" | choose the token → map to a symbol (`instrumentAliases`) |
| Ambiguous | "is a signal" | set `templateThresholds[key]` just below this row's confidence |
| Parsed | "is noise" | add a distinctive phrase from the message → `rejectPhrases` |
| Rare | "is a signal" | accept the family (existing accept flow) |

One click → `PUT` overlay → re-mine → the row moves bucket. A **Manage panel**
(section or dialog) lists everything taught — aliases, direction tokens, reject
phrases, threshold overrides — each removable (undo); changes `PUT` and re-mine.

## Phasing

The feature is full-stack; build in two plans, each its own spec/plan/implement slice
if needed.

- **Phase 1 — Foundation + Manage.** Backend table + migration + API; frontend
  overlay fetch; parser-merge threading with domain unit tests; the Manage panel
  (view/add/remove, re-mine on change). Delivers durable manual teaching end-to-end.
- **Phase 2 — Guided per-row.** The diagnosis engine + per-row verdict→suggested-fix
  in `AuditReview`. Builds on Phase 1's overlay + merge.

This document covers both phases; the implementation plan starts with Phase 1.

## Testing

- **Domain** (Vitest): overlay-merge unit tests — adding an alias/direction token
  moves a Miss into Parsed; a reject phrase moves a Parsed row to Rejected; a lowered
  `templateThresholds[key]` moves an Ambiguous row to Parsed. No-overlay path
  unchanged (existing tests stay green).
- **Backend** (pytest): `GET`/`PUT /parser-overlay` round-trip; per-account scoping
  (one user cannot read/write another's overlay); empty default.
- **Frontend** (Vitest + RTL): Manage panel add/remove + re-mine; Phase 2 per-row
  verdict→suggestion.
- **End-to-end** (Playwright on the real feed): teach `🚀 = LONG` recovers a miss;
  add a reject phrase removes a noise row from Parsed; lower a threshold promotes an
  Ambiguous row. Run the full gate (frontend lint/format/test/build, backend lint/test).

## Reused code / touch points

- `apps/frontend/web/src/domain/template-mining/`: `instruments.js`, `directions.js`,
  `rules.js` (`applyAcceptedRules`, `deriveThreshold`, `REJECT_PHRASES`),
  `extract.js`, `mining.js`, `index.js` (barrel).
- `apps/frontend/web/src/features/template-mining/`: `AuditReview.jsx` (review surface),
  `TemplateMiningPage.jsx` (fetches + threads the overlay), a new manage panel.
- `apps/frontend/web/src/shared/api/pipelineApi.js` (overlay client, beside
  `listFeedHistory`).
- `apps/frontend/web/src/app/ProductApp.jsx` (wires the overlay fetch/PUT into the page).
- Backend: a feeds/accounts feature module for the overlay repository + routes +
  schema; Alembic migration; pytest fixtures mirror `tests/api/test_labels.py`.
