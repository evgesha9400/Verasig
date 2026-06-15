# Pipeline step → backend wiring

Wire the remaining verification-workflow steps to the real backend so each step
shows real data and round-trips without errors. Verified end-to-end against the
real, single added Telegram feed.

## Problem

The product shell is a prototype. Only **Backfill** talks to the backend; every
other pipeline step renders `web/src/domain/demo-data/seed.js` on simulated
timers. The Label step shows placeholder messages instead of the messages just
backfilled.

The backend already exposes the needed endpoints — the gap is purely frontend
wiring.

## Scope

| Step | Decision | Backend endpoints |
| --- | --- | --- |
| Backfill | already wired | `POST/…/backfill`, `…/progress`, `…/cancel` |
| **Label** | **wire now** | `GET …/messages`, `POST …/messages/{id}/label`, `GET …/labels` |
| **Distill** | **wire now** | `POST …/distill`, `…/distill/progress`, `GET …/rules` |
| **Verify** | **wire now** | `GET …/verify/samples`, `POST …/verify` |
| Exchange | **defer** — paid tier | `GET /exchanges`, `…/{id}/connect`, `…/{id}/disconnect` (unused for now) |
| Execution (risk) | **defer** — paid tier | `GET/PUT …/risk` (unused for now) |
| Backtest | **defer** — paid tier | `POST …/backtest`, `…/backtest/progress` (unused for now) |

Exchange, Execution + Backtest — the entire post-verify routing chain — become
advanced, higher-plan features. The wired core flow ends at a verified source. See
`docs/adr/0011-defer-post-verify-routing-to-paid-tier.md`.

## Decisions

- **No-backend fallback removed** for wired steps. They require an auth token and
  a real backfilled feed; the no-login seed demo no longer drives them.
- **Labels persist per swipe + reload.** Each swipe POSTs one idempotent upsert
  (the only label endpoint there is); counts and the distill gate read from the
  backend. Chosen over end-of-session batching because it is durable/resumable,
  needs no new backend endpoint, and keeps the distill gate backed by real DB
  counts. Volume is trivial (≤ the `limit`, human-paced).
- **Incremental delivery.** One step per commit, each verified against the real
  feed before the next.

## Approach

Mirror the existing `BackfillView` contract: `ProductApp` passes API-bound
handler closures (over `authToken` + `chatId`) into each step view; the view
calls them and renders real data. This keeps the props-driven test seam and
matches the one step already wired.

Rejected:
- Views importing the API client directly — breaks the test seam.
- Centralizing all fetches in `useWorkflowState` — couples unrelated steps, bloats
  the hook.

## Components

### New — `web/src/shared/api/pipelineApi.js`

A generic SSE helper plus per-step request functions.

- `streamJobProgress(token, progressUrl, handlers)` — generalizes
  `streamBackfillProgress`'s `EventSource` wiring (`progress` / `done` / `error`).
- Label: `listMessages(token, chatId, limit?)`, `recordLabel(token, chatId, msgId, label)`, `getLabelCounts(token, chatId)`.
- Distill: `startDistill(token, chatId)`, `streamDistillProgress(token, chatId, handlers)`, `getRules(token, chatId)`.
- Verify: `getVerifySamples(token, chatId)`, `submitVerify(token, chatId, verdicts)`.

`streamJobProgress` is used by Distill only (Backtest is deferred).

### Contracts (verified against route + schema files)

- **Message** (`GET …/messages` → `{messages:[…]}`, `GET …/verify/samples` →
  `{attempt, samples:[…]}`): `{id, time, date, author, text, media, replyTo:{author,text}|null}`;
  samples add `predicted: "signal"|"noise"`. `media` is `"image"|"doc"|null`.
  Only messages that have a candidate `RawSignalEventRow` and are not yet labelled
  are returned.
- **Label counts** (`GET …/labels`): `{signalCount, noiseCount, modifierCount, total}`.
- **Label write** (`POST …/messages/{id}/label`): body `{label:"signal"|"noise"|"modifier"}` → `204`.
- **Rule** (`GET …/rules` → `{rules:[…]}`): `{id, label, detail, match}`; `match` is
  already a **0–100** percentage (the demo used 0–1 — fix the display).
- **Distill phases** (SSE `progress.phase`): exactly the five strings the demo
  already lists, so the existing step animation maps 1:1.
- **Verify submit** (`POST …/verify`): body `{verdicts:[{messageId, verdict:"correct"|"wrong"}]}`
  → `{passed:boolean, misclassified:[messageId]}`. Minimum 6 verdicts.
- **Auth:** bearer header for normal calls; `?token=` query param for SSE (matches backfill).

## Per-step behaviour

### Label (`LabelView`)
- Props become `chatId` + handler closures (`onListMessages`, `onRecordLabel`,
  `onGetCounts`) + `onDistill`. Drops the `MESSAGES`/`labels`/counts props.
- On mount: load messages (deck) and counts (rail) in parallel; show loading and
  empty (`No messages to label`) states.
- Swipe: optimistic local label + count bump, then `recordLabel`. On failure,
  revert that card and surface an error toast.
- `canDistill` = backend `signalCount >= 5`.
- `useWorkflowState` loses `labelsByChat`/`signalCount`/`noiseCount`/`setLabel`;
  `verifyAttempt` (deck remount key for the loop) stays.

### Distill (`DistillView`)
- Props: `chatId`, `onStartDistill`, `onStreamProgress`, `onGetRules`,
  `onComplete`, `onError`. Drops `DISTILLED_RULES`.
- On mount: `startDistill`, stream phases → drive the existing step list; on
  `done`, `getRules` → render real rules with `Math.round(match)`%.
- SSE race (progress 404 after eviction — distill has no durable replay): on
  stream error, fall back to `getRules`; render if present, else show the error.

### Verify (`VerifyView`)
- Props: `chatId`, `onGetSamples`, `onSubmit`, plus existing `onPass/onStop/onLoop`.
  Drops `MESSAGES`/`VERIFY_MISCLASSIFIED`.
- On mount: `getSamples` → deck items carry the backend `predicted`; `attempt`
  from backend.
- On finish: `submitVerify` with every verdict → use `{passed}`; passed → pass
  screen, else → loop screen (`onLoop`). The backend, not the client, decides.
- Pass screen: the primary action keeps the source verified (`onStop`); the
  exchange/backtest option points at the deferred placeholder, not a wired step.

### Exchange + Execution + Backtest (deferred)
- `ProductApp` renders a shared upsell placeholder for the `exchange`, `risk`,
  `backtest`, and `backtest-result` screens.
- The existing `ExchangeView` / `ExecutionView` / `BacktestView` files are retained
  unchanged for the future paid-tier build; they are simply not mounted in the flow.
- The wired core flow therefore ends at a verified source. When backtest is built,
  its drawdown/latency cards stay marked "sample" until the backend computes them.

## Error handling

- Reuse `fireToast` for transient failures (e.g. a failed label write → revert the
  card).
- Distill job failures arrive as SSE `error` events → message in the view.
- Loading and empty states on every fetch-on-mount view.

## Testing

TDD per step. Vitest tests pass mocked handler closures (the same seam
`BackfillView.test.jsx` uses) and assert real-data rendering, persistence calls,
and error/empty states. Backend behaviour is already covered by pytest.

End-to-end: run the stack (`make dev` / `make up`), log in, open the real feed,
walk Label → Distill → Verify, and confirm no console or network errors.

## Out of scope

- Exchange, Execution + Backtest backend wiring (deferred — see ADR 0011).
- New backend endpoints or migrations.
- Changes to Signals / Sources, which keep using seed data where they already do.
