# Verasig Backend Rewrite — Refined Requirements

Single big-bang refactor: CLI-only backend → multi-tenant FastAPI HTTP API matching the
frontend's simulated protocol (`apps/frontend/web`). Domain logic is kept; delivery,
auth, and tenancy are replaced.

- Companion: [implementation-plan.md](implementation-plan.md)
- Canonical vocabulary: [docs/context/CONTEXT.md](../../../../docs/context/CONTEXT.md) — use it exactly.

---

## 1. Scope

### Keep (unchanged domain)

| Area | Modules |
|---|---|
| Signal extraction | `services/extraction/*` (deterministic parser + LLM fallback seam) |
| Distillation | `services/distillation/*` (rule distiller + evaluation) |
| Lifecycle folding | `services/lifecycle/*` (pure fold, patch classifier) |
| Scoring | `services/scoring/*` (scorecard, hygiene, simulator, policies) |
| Deletion evidence | `services/deletion/*` (diff, rescan) |
| Ingestion | `services/ingestion/*` (backfill, candidate filter/derivation; `live.py` kept, not API-exposed) |
| Capture schema | `telegram_channel`, `raw_telegram_message`, `raw_signal_event` + projections (append-only / recomputable pattern, ADR 0001/0006) |
| Stack | Python 3.12, SQLAlchemy 2.0 (sync), Alembic, PostgreSQL 16, UV, Telethon, httpx |
| Tests | Domain unit tests, testcontainers Postgres fixtures, `tests/fakes.py` |

### Replace

| From | To |
|---|---|
| Typer CLI (`cli.py`) | FastAPI routers (`api/`) |
| No auth | JWT (HS256) per user |
| Global file `StringSession` | Per-user encrypted `StringSession` in DB |
| `subprocess claude` runner | Anthropic Python SDK runner (same injectable `runner` seam) |
| No job system | In-process async jobs + SSE progress streams |

### Drop

| Item | Disposition |
|---|---|
| `verasig candidates / lifecycle / sweep / stats / deletions / whoami` | Folded into API projections (internal calls) |
| `verasig rescan` | Auto-triggered after every backfill completion |
| `verasig login` | Replaced by per-user `/telegram/connect` + `/verify` |
| `cli.py` + CLI integration tests | Deleted; unique coverage rewritten as API tests |

### Defer (explicitly out of v1)

- Stripe billing (plan changes are direct writes, no payment)
- Outbound email (mailer is a logging stub; email-change confirm tokens surfaced in logs)
- Password-reset completion (request endpoint only in v1 — no token, no consumer endpoint)
- Live ingestion API exposure (`services/ingestion/live.py` stays internal)
- Desk-tier public API keys ("API access" plan row)
- 2FA-protected Telegram accounts (`SessionPasswordNeededError` → clean error)

---

## 2. User stories

| # | As a | I want | So that |
|---|---|---|---|
| U1 | visitor | to register and log in with email/password | my feeds and labels are private to me |
| U2 | user | to link my own Telegram account (api id/hash, phone, code) | the backend reads channels as me, isolated from other tenants |
| U3 | user | to add a channel by @tag and backfill its history with live progress | I see capture advancing (fetched count, date reached) |
| U4 | user | to swipe-label messages as signal/noise/modifier | the system distills my provider's format into rules |
| U5 | user | to watch distillation phases and read the resulting rules with match rates | I trust what was learned |
| U6 | user | to audit rule predictions on samples and flag wrong ones | bad rules loop me back to labelling, my corrections feed the corpus |
| U7 | user | to connect my Bybit keys (verified against Bybit) | backtests use a real venue and execution can follow later |
| U8 | user | to set entry/exit risk parameters | the backtest replays signals under *my* risk model |
| U9 | user | to run a backtest and get score / win rate / PnL on the chat | I can rank providers by evidence |
| U10 | user | to browse extracted signals with lifecycle mods and effective state | I see what the provider actually did |
| U11 | user | to link an orphan modifier to its signal manually | lifecycle folding gets the evidence it lacks |
| U12 | user | deletion/gap flags surfaced per chat, deletion flooring score to 0 | scam channels are exposed |
| U13 | user | to manage profile, email (pending verification), password reset, plan | account self-service |
| P1 | platform | plan limits enforced at the API (sources/exchanges/signal volume) | tiers mean something |

---

## 3. Protocol conventions

- JSON wire format: **camelCase** (Pydantic `alias_generator=to_camel`); DB stays snake_case.
- Ids: `chatId` = Telegram channel id as **string**; `userId`, signal ids = UUID strings; message ids = Telegram message id as string.
- Display strings the frontend renders verbatim (per frontend sim): `lastDate` `"Nov 18, 2025"`, message/signal `date` `"Jun 7"`, `time` `"14:32"`. All other metrics are **numbers** (`score` 0–100, `winRate` %, `pnl` %).
- Auth: `Authorization: Bearer <jwt>` everywhere; SSE endpoints additionally accept `?token=<jwt>` (EventSource cannot set headers).
- Errors: uniform `{ "error": { "code": "PLAN_LIMIT_SOURCES", "message": "…" } }` with proper status (400/401/403/404/409).
- Long ops: `POST` returns `202 {"jobId": "…"}`; progress via `GET …/progress` (`text/event-stream`), events `progress` → terminal `done` | `error`.

---

## 4. API surface

### Auth — `api/routers/auth.py`

| Endpoint | Method | Request | Response |
|---|---|---|---|
| `/auth/register` | POST | `{firstName, lastName, email, password}` (password ≥ 10) | `201 {token, user}` |
| `/auth/login` | POST | `{email, password}` | `{token, user}` |
| `/auth/logout` | POST | — | `204` (stateless; client discards token) |
| `/auth/me` | GET | — | `{firstName, lastName, email, plan, pendingEmail, cancelAt}` |

### User profile & subscription — `api/routers/user.py`

| Endpoint | Method | Request | Response |
|---|---|---|---|
| `/user` | PATCH | `{firstName?, lastName?}` | user |
| `/user/email` | POST | `{email}` | user (`pendingEmail` set; confirm token logged — mail stub) |
| `/user/email/confirm` | POST | `{token}` | user (email applied, `pendingEmail` null) |
| `/user/password/reset-request` | POST | — | `202` (request logged — mail stub; no token issued, reset completion deferred with email infra) |
| `/user/subscription/change` | POST | `{plan}` | user |
| `/user/subscription/cancel` | POST | — | user (`cancelAt` = now + 30 d) |
| `/user/subscription/resume` | POST | — | user (`cancelAt` null) |

### Telegram link — `api/routers/telegram.py`

| Endpoint | Method | Request | Response |
|---|---|---|---|
| `/telegram/connect` | POST | `{apiId, apiHash, phone}` | `202` (code sent; pending link stored) |
| `/telegram/verify` | POST | `{code}` | `{connected: true}` (encrypted StringSession stored) |
| `/telegram/status` | GET | — | `{connected, phone}` (phone masked `+44 •••• 8821`) |

### Chats — `api/routers/chats.py`

| Endpoint | Method | Request | Response |
|---|---|---|---|
| `/chats` | GET | — | `{chats: [Chat]}` |
| `/chats` | POST | `{tag}` (@handle) | `201 Chat` (resolved via user's Telethon; plan-gated) |
| `/chats/{id}` | DELETE | — | `204` (drops subscription + user-scoped data; capture stays) |
| `/chats/{id}/backfill` | POST | — | `202 {jobId}` |
| `/chats/{id}/backfill/cancel` | POST | — | `204` (status → `cancelled`) |
| `/chats/{id}/backfill/progress` | GET | SSE | `progress: {fetched, lastDate, phase}` |

**Chat** = `{id, name, tag, subscribers, initials, tint, status, fetched, lastDate, score, winRate, pnl, hasRisk, historyGaps, signalDeletion}`

- `status` ∈ `new | backfilling | backfilled | verified | analyzed | cancelled`
  (order corrected vs. rough requirements: **verified precedes analyzed** — verified = rules audited, analyzed = backtested)
- Derived: `fetched` = captured message count; `lastDate` = earliest captured `posted_at`; `score/winRate/pnl` = latest `backtest_result`; `historyGaps` = any SUSPECTED `deleted_signal_evidence`; `signalDeletion` = any CONFIRMED with `was_signal_candidate`; `hasRisk` = status ∈ {verified, analyzed}; `score` forced 0 when `signalDeletion`.
- Backfill SSE phases (verbatim): `Opening MTProto session…`, `Reading channel history…`, `Decrypting message batch…`, `Resolving media references…`, `Backfilling older window…`, `Indexing message bodies…`.
- Backfill completion auto-runs **rescan** (deletion evidence → flags).

### Label step — `api/routers/labels.py`

| Endpoint | Method | Request | Response |
|---|---|---|---|
| `/chats/{id}/messages` | GET | `?limit=40` | `{messages: [Message]}` (labeling sample, oldest-first among candidates) |
| `/chats/{id}/messages/{msgId}/label` | POST | `{label}` ∈ `signal\|noise\|modifier` | `204` (upsert `golden_label`) |
| `/chats/{id}/labels` | GET | — | `{signalCount, noiseCount, modifierCount, total}` |

**Message** = `{id, time, date, author, text, media, replyTo}`; `media` ∈ `image|doc|null` (mapped from Telethon payload; sim's `chart` never produced); `replyTo` = `{author, text}|null`. Sim-only fields `truth`/`mod` are **not** in the API — truth is what the user assigns; mods are computed at fold time.

Gate (enforced server-side at distill): `signalCount ≥ 5`.

### Distill step — `api/routers/distill.py`

| Endpoint | Method | Request | Response |
|---|---|---|---|
| `/chats/{id}/distill` | POST | — | `202 {jobId}` (409 `LABELS_INSUFFICIENT` if < 5 signals) |
| `/chats/{id}/distill/progress` | GET | SSE | `progress: {phase}` |
| `/chats/{id}/rules` | GET | — | `{rules: [{id, label, detail, match}]}` |

- SSE phases (verbatim, matching frontend): `Reading your labelled signals`, `Extracting structure & tickers`, `Inferring discriminative patterns`, `Cross-checking against non-signals`, `Compiling filter ruleset`.
- Distiller (Anthropic SDK) emits per-pattern display metadata `{label, detail}` → stored on `filter_rule.display`; `match` = share of golden signal labels each pattern matches (computed at read via `apply_filter_rule`).

### Verify step — `api/routers/verify.py`

| Endpoint | Method | Request | Response |
|---|---|---|---|
| `/chats/{id}/verify/samples` | GET | — | `{samples: [{…Message, predicted}], attempt}` |
| `/chats/{id}/verify` | POST | `{verdicts: [{messageId, verdict: correct\|wrong}]}` | `{passed, misclassified: [messageId]}` |

Semantics (replaces the sim's "planted misclassifications"): `predicted` = distilled `FilterRule` applied to a holdout sample (messages without golden labels). Rule errors surface naturally on attempt 1. Rules:

- `< 6` verdicts → `400 VERIFY_TOO_FEW_VERDICTS` (frontend `VERIFY_MIN = 6`).
- Any `wrong` → `passed: false`; each wrong verdict writes a corrected `golden_label` (flip of prediction) and, where the filter missed a signal, a `FilterDriftWarning(HUMAN_AUDIT)`; `verify_attempt` increments; frontend loops to Label → re-distill.
- Zero `wrong` → `passed: true`; chat status → `verified`.

### Exchanges — `api/routers/exchanges.py`

| Endpoint | Method | Request | Response |
|---|---|---|---|
| `/exchanges` | GET | — | `{exchanges: [{id, name, brand, tint, initials, status, kind, connected, account}]}` |
| `/exchanges/{id}/connect` | POST | `{apiKey, apiSecret}` | exchange (verified against Bybit `GET /v5/user/query-api`, HMAC-signed; plan-gated) |
| `/exchanges/{id}/disconnect` | POST | — | exchange |

Static catalog in code (bybit `available`; others `soon`). `account` = masked key `"J7n2…wL · trade-only"`. Secret stored AES-GCM-encrypted (`SecretCipher` envelope, AAD-bound to user+exchange); never returned.

### Risk config — `api/routers/risk.py`

| Endpoint | Method | Request/Response |
|---|---|---|
| `/chats/{id}/risk` | GET | RiskConfig (defaults if unset) |
| `/chats/{id}/risk` | PUT | RiskConfig |

**RiskConfig** = `{entryMode: first|mid|ladder, levels: 2–5, weighting: equal|martingale, exitSource: signal|custom, stopPct, tpPct, riskPct, leverage}`
(`riskPct` + `leverage` added vs. rough requirements — the simulator needs them; defaults: `mid, 3, equal, signal, 2.5, 7.5, 2.0, 5`).

### Backtest — `api/routers/backtest.py`

| Endpoint | Method | Request | Response |
|---|---|---|---|
| `/chats/{id}/backtest` | POST | — | `202 {jobId}` |
| `/chats/{id}/backtest/progress` | GET | SSE | `progress: {phase}` → `done: {score, winRate, pnl}` |

- SSE phases (verbatim): `Replaying historical signals`, `Applying your risk model`, `Simulating fills & slippage`, `Scoring confidence & drawdown`.
- Pipeline: fold lifecycles → Bybit klines → simulate under risk config → `build_provider_score` → `score` = round(score × 100), `winRate` = wins/tested %, `pnl` = compounded % → persist `backtest_result`, status → `analyzed`.

### Signals — `api/routers/signals.py`

| Endpoint | Method | Request | Response |
|---|---|---|---|
| `/signals` | GET | `?feedId=&status=` | `{signals: [Signal], orphanMods: [OrphanMod], limitReached}` |
| `/signals/{id}` | GET | — | Signal |
| `/signals/{id}/link-mod` | POST | `{modId}` | Signal (writes `lifecycle_link`, refolds) |

**Signal** = `{id, feedId, side, symbol, status, outcome, pnl, date, time, entry, stop, tp[], deleted, cancelled, mods[], effective}`

- `status`: `tested` (outcome kind R_MULTIPLE/MARK_TO_MARKET) | `skipped` (UNFILLED) | `untested` (no outcome); read from the latest `backtest_result.outcomes` snapshot — never refetches klines on read (D15); `outcome`: sign of return; `deleted` from `deleted_signal_evidence`; `mods[]`/`effective{}` projected from `FoldedSignal` timeline (kind from `classify_patch`, `via: reply|inferred`).
- **OrphanMod** = `{id, feedId, symbol, date, time, text, suggestId, reason}` — modifier-labeled/classified messages with no `reply_to` linkage; `suggestId` = latest open same-symbol signal.
- Observer plan: max 200 signals per calendar month surfaced; truncated ⇒ `limitReached: true`.

### Ops

| Endpoint | Method | Response |
|---|---|---|
| `/health` | GET | `{status: "ok"}` (DB `select 1`) |

---

## 5. Data model changes

### New tables (migration `0006_multi_tenant_api`)

| Table | Columns (PK bold) | Notes |
|---|---|---|
| `user_account` | **id** UUID, email unique, password_hash, first_name, last_name, plan (`observer\|operator\|desk`, default observer), pending_email?, cancel_at?, created_at | |
| `user_telegram_link` | **user_id** FK, api_id int, api_hash_encrypted, phone, session_string_encrypted?, phone_code_hash?, status (`pending\|connected`), updated_at | one link per user |
| `user_channel` | **(user_id, channel_id)** FKs, status (chat status enum, default `new`), verify_attempt int default 1, added_at | per-user subscription + pipeline state |
| `user_exchange_connection` | **(user_id, exchange_id str)**, api_key_masked, api_key_encrypted, api_secret_encrypted, connected bool, connected_at | |
| `chat_risk_config` | **(user_id, channel_id)**, entry_mode, levels, weighting, exit_source, stop_pct, tp_pct, risk_pct, leverage, updated_at | numeric pcts |
| `backtest_result` | **id** UUID, user_id FK, channel_id FK, score int, win_rate numeric, pnl numeric, outcomes JSONB, completed_at | latest-per-chat read; `outcomes` = per-signal sim snapshot `[{rootSignalId, kind, rMultiple, pctReturn, exitReason}]` (D15) |
| `lifecycle_link` | **id** UUID, user_id FK, channel_id, message_id, root_signal_id FK, created_at, UNIQUE(user_id, channel_id, message_id) | durable HUMAN_AUDIT linkage for fold |

### Modified tables

| Table | Change |
|---|---|
| `golden_label` | + `user_id` FK; + `label` (`signal\|noise\|modifier`); `is_signal` kept, derived (`label = 'signal'`); UNIQUE → (user_id, channel_id, message_id) |
| `filter_rule` | + `user_id` FK; + `display` JSONB (per-pattern `{label, detail}`); `rule_id` PK stamped user-scoped (`{user_id}:{channel_id}-filter-v{version}` — legacy stamp collides across users); + UNIQUE NULLS NOT DISTINCT (user_id, channel_id, version) |
| `parser_rule` | + `user_id` FK; `rule_id` stamped user-scoped (`{user_id}:{channel_id}-parser-{n}-v{version}`; many per version, no version unique) |
| `extracted_signal` | + `user_id` FK (nullable through transition); UNIQUE(event_id) → UNIQUE NULLS NOT DISTINCT (user_id, event_id) — outcomes of per-user parser rules are per-user projections (D16) |
| `unrecognized_signal` | + `user_id` FK; UNIQUE → NULLS NOT DISTINCT (user_id, event_id) |
| `parser_drift_warning` | + `user_id` FK; UNIQUE → NULLS NOT DISTINCT (user_id, event_id) |
| `filter_drift_warning` | + `user_id` FK; UNIQUE → NULLS NOT DISTINCT (user_id, channel_id, message_id) |

### Decision: capture stays global (deviation from rough requirements)

Rough requirements said "ChannelRow → add user_id". **Rejected**:

- `raw_telegram_message` keys off `channel_id`; per-user channels would force per-user duplication of the entire append-only capture and a composite-PK upheaval.
- Channel content is identical for every subscriber; one capture serves all tenants (ADR 0001 preserved).
- All *user-meaning* state (status, attempt, labels, rules, risk, backtests) is per-user in `user_channel` + the tables above.

Consequence: backfill cursor (`captured_through_message_id`) is global per channel; any user's backfill advances it for everyone.

---

## 6. Plan enforcement

| Limit | Observer | Operator | Desk | Enforcement point |
|---|---|---|---|---|
| Sources (chats) | 1 | 10 | ∞ | `POST /chats` → `403 PLAN_LIMIT_SOURCES` |
| Signals/month | 200 | ∞ | ∞ | `GET /signals` truncation + `limitReached` |
| Exchanges | 0 | 1 | multi | `POST /exchanges/{id}/connect` → `403 PLAN_LIMIT_EXCHANGES` |
| API access | – | – | ✓ | deferred (no public keys in v1) |

Constants in `services/accounts/plans.py`; guards are FastAPI dependencies.

---

## 7. Long-running operations

| Operation | Real duration | Mechanism |
|---|---|---|
| Backfill | minutes–hours | async task + SSE (`fetched`, `lastDate`, `phase`); resumable by cursor; cancellable |
| Distill | LLM latency (~10–60 s) | async task + SSE (phase per stage) |
| Backtest | CPU + kline fetch | async task + SSE (phase per stage) |

Jobs: in-process `JobRegistry` (one running job per `(user, chat, kind)`, `409 JOB_ALREADY_RUNNING` on duplicate), `asyncio.Queue` per subscriber, `sse-starlette` for streaming. Not restart-persistent — acceptable: backfill resumes from cursor, distill/backtest are re-runnable projections.

---

## 8. Dependencies

| Add | Why |
|---|---|
| `fastapi`, `uvicorn[standard]` | HTTP layer |
| `sse-starlette` | SSE streaming (less hand-rolled code) |
| `anthropic` | replaces `subprocess claude` |
| `pyjwt` | JWT — chosen over python-jose (unmaintained, CVEs) / authlib (oversized for HS256) |
| `bcrypt` | direct use — passlib is unmaintained and breaks with bcrypt ≥ 4.1 |
| `cryptography` | AES-GCM (`SecretCipher` envelopes `v1:<key_id>:<nonce_b64>:<ciphertext_b64>`, AAD tenant binding, env keyring rotation) for session strings + exchange secrets |

Remove: `typer`. Config additions (env `VERASIG_`): `jwt_secret`, `secret_keys` (keyring: `2026-06:base64key,2026-01:oldbase64key`; first = primary), `anthropic_api_key`, `anthropic_model` (default `claude-sonnet-4-6`), `cors_origins`. Removed: `session_path`, `telegram_api_id/hash/phone` (per-user now), `distiller_command`, `extractor_command`.

---

## 9. Decisions log (modifications to the rough requirements)

| # | Decision | Rationale |
|---|---|---|
| D1 | Capture tables stay global; tenancy via `user_channel` | see §5 |
| D2 | Status order `backfilled → verified → analyzed` | matches frontend (`verified` = rules pass; `analyzed` = backtested) |
| D3 | Verify = human audit of real rule predictions on holdout; wrong verdicts feed corpus + drift warnings | "planted errors" was sim scaffolding; real rules err naturally on attempt 1 |
| D4 | `golden_label.label` 3-way enum | frontend labels signal/noise/modifier; modifier feeds lifecycle |
| D5 | `lifecycle_link` table added | `/signals/{id}/link-mod` needs durable HUMAN_AUDIT evidence for the pure fold |
| D6 | PyJWT + bcrypt + AES-GCM (`SecretCipher`) | maintained, minimal, well-established; envelope key ids enable rotation |
| D7 | Anthropic SDK as injected `runner`; `ClaudeCli*` adapters renamed `Anthropic*` | existing seam; canned-runner tests unchanged |
| D8 | `POST /chats/{id}/backfill/cancel`, subscription change/resume, email confirm added | frontend workflow needs them; rough requirements omitted |
| D9 | RiskConfig + `riskPct`, `leverage` | simulator requires position sizing inputs |
| D10 | Metrics numeric on the wire; only date/time display strings preformatted | seed strings are presentation; requirements' examples kept where explicit |
| D11 | Mail delivery stubbed (logged) | no email infra in v1; endpoints + states are real |
| D12 | Register takes `firstName`/`lastName` | matches user model + `/auth/me`; frontend splits its single `name` field (frontend follow-up) |
| D13 | `media` ∈ `image\|doc\|null`; `chart` never emitted | backend cannot distinguish chart from image |
| D14 | On verify pass status → `verified` immediately | "stop here" path needs no extra call; backtest later flips to `analyzed` |
| D15 | `backtest_result` snapshots score **and per-signal `outcomes` JSONB** | `/signals` must not refetch klines per read; deviation from ADR 0009 ("never stored") is deliberate — the canonical score stays recomputable, stored rows are display snapshots of one run |
| D16 | Tenant boundary: capture + seed-heuristic candidates stay global and user-independent; **all rule-driven projections are user-scoped** (extraction outcomes, drift warnings); user `FilterRule`s apply at read time, never materializing global `raw_signal_event` rows | per-user rules over a global `extracted_signal` would collide on UNIQUE(event_id); rule-driven late-materialization (`sweep_advisory`) is not API-exposed in v1 |

## 10. Frontend follow-ups (out of backend scope, tracked here)

- Add an API client layer (none exists — pure in-memory sim today) and replace `setTimeout` sims with real calls + SSE.
- Split register `name` → `firstName`/`lastName`.
- Format numeric metrics / parse preformatted dates per §3.
- Auth storage: keep token (localStorage) instead of boolean flag.
