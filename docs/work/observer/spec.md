# Observer Design Spec

**Date:** 2026-06-02

## 1. Purpose

- Prove Verasig can **evaluate Telegram signal-provider quality** from historical + live-observed messages.
- **Observe-only.** No execution, no orders, no exchange credentials, no cloud.
- **Local-only** = the whole stack runs via `docker compose` on any machine with Docker.
- Disposable: easy to delete (`docker compose --env-file apps/backend/.env down -v`) or change.

## 2. Success Criterion (from validation-roadmap.md)

> The operator can classify a signal source as **good / bad / untradeable** purely from stored evidence.

- **good/bad** ← simulated outcome (expectancy, drawdown).
- **untradeable** ← incomplete/unrecognized signals (hygiene).
- Every classification must be backed by a `ProviderScoreExplanation` linking to stored evidence.

## 3. Scope

### In
- Telegram **user-account** session ingestion (Telethon).
- Public + private channel **history backfill** and **live listener**.
- Append-only `RawTelegramMessage` capture.
- Candidate filter (**advisory**, seed + distilled) → `RawSignalEvent` ([ADR 0005](../../adr/0005-distilled-filter-and-advisory-gate.md)).
- Human-assisted **distillation loop** → `FilterRule` + `ParserRule`s + golden corpus.
- Deterministic extraction → `ExtractedSignal` | `UnrecognizedSignal`.
- LLM fallback via **Claude/Codex CLI** (behind an interface) → `ParserDriftWarning`.
- Signal **lifecycle folding** (entry + modifications + close, linked by `reply_to`).
- `DeletedSignalEvidence` (CONFIRMED snapshot-diff + SUSPECTED id-gap).
- Conservative **simulation** vs Bybit public klines (pluggable `ExecutionPolicy`).
- Re-weightable `ProviderScore` + `ProviderScoreExplanation`.
- Operator review UI and scorecard are removed from this implementation; future framework TBD.

### Out (non-goals)
- Demo execution · live execution · Bybit order placement · exchange credentials.
- Cloud deployment · billing · multi-user tenancy · public launch.
- Discord · image/multimodal extraction · marketplace · portfolio management.
- Autonomous auto-research / autonomous parser-rule mining.
- Final/optimal score formula (explicit open research question — outside current scope).

## 4. Architecture (2-layer, per CLAUDE.md)

```
┌──────────────────────────── docker compose ────────────────────────────┐
│  FOUNDATION                                                              │
│   db (Postgres)   telegram session (volume)   secrets/ mount (.env)      │
├──────────────────────────────────────────────────────────────────────── │
│  SERVICE  (one image, many commands — typer CLI)                         │
│   login → backfill → candidates → extract → fallback                     │
│         → lifecycle → deletion → score → simulate → live                 │
└──────────────────────────────────────────────────────────────────────── ┘
```

- **Foundation** = concrete IO edge: SQLAlchemy engine/session setup, Telethon session/source adapters, `StaticExchange` seed adapter, Bybit market-data client.
- **Storage** = sibling persistence edge: SQLAlchemy ORM rows and repositories for append-only capture, recomputable projections, and durable evidence.
- **Service** = one uv-built Python image; each pipeline step is a CLI subcommand. The live daemon is the same image run long-lived.
- **Dependency rule:** `domain/` (pure contracts) ← `services/` (logic) ← `storage/`+`foundation/` (IO). CLI is a thin adapter over services. Logic never imports IO frameworks directly.

### Data flow
```
Telegram ──backfill──▶ RawTelegramMessage ──candidate filter──▶ RawSignalEvent
                                                                     │
   ParserRule (from distillation loop) ──┐                          │
                                          ▼                          ▼
                              deterministic parse ───match──▶ ExtractedSignal
                                          │ miss                     │
                                          ▼                          │ reply_to links
                                  LLM CLI fallback ──┬─success──▶ ExtractedSignal + ParserDriftWarning
                                                     └─fail────▶ UnrecognizedSignal
                                                                     │
   re-scan / live delete ──▶ DeletedSignalEvidence                  ▼
   Bybit klines ──▶ simulate(folded signal, policy) ──▶  lifecycle fold
                              │                                      │
                              ▼                                      ▼
                        Simulated outcome ─────────▶ ProviderScore + ProviderScoreExplanation
```

## 4.1 Processing model — resumable & chunked (hard requirement)

- **Resumable, no needless refetch.** Backfill persists a per-channel cursor (`TelegramChannel.captured_through_message_id`). On restart it resumes from the cursor; already-captured messages are **never refetched**. A separate explicit `rescan` (for deletion-diffing) is the only path that re-reads old ranges.
- **Idempotent.** All writes keyed on `(channel_id, message_id)` (raw) / deterministic ids; a crash mid-batch then restart produces zero duplicates.
- **Chunked / streaming — never load everything into RAM.** Every processing path iterates in bounded batches and dumps to Postgres per batch: backfill paginates Telegram and commits every N messages; extraction/lifecycle/scoring stream rows via server-side cursors / `yield_per`; klines are fetched per-signal-window, not bulk-cached. Peak memory stays ~flat regardless of channel size.
- **Checkpoint granularity.** Commit per batch (not per run) so a kill at message 9,000 of 10,000 loses at most one batch and resumes cleanly.
- **Backpressure.** Respect Telegram flood-wait; exponential backoff on rate limits; resume after backoff.

## 5. Tech stack

| Concern | Choice | Why |
|---|---|---|
| Runtime / deps | Python 3.12 + **uv** | mandated; fast, reproducible |
| Telegram | **Telethon** (hybrid push+poll live; [ADR 0004](../../adr/0004-hybrid-push-poll-live-ingestion.md)) | one client for backfill + live; ~30s channel-push delay is MTProto batching, solved by active gap-close poll — not a library swap |
| DB | **Postgres 16** (container) | relational joins + concurrency; production-path |
| ORM / migrations | **SQLAlchemy 2.0** + **Alembic** | robust, best corpus, append-only friendly |
| Contracts | **Pydantic v2** | validated canonical schemas |
| CLI | **Typer** | typed subcommands |
| Market data | **httpx** client behind interface | public klines = simple GET; trivially fakeable |
| LLM fallback | **Claude / Codex CLI** via subprocess, behind interface | reuses user auth; fake in tests |
| Tests | **pytest** (+ pytest-asyncio, testcontainers-postgres) | TDD; ephemeral DB |
| Lint/format | **ruff** | mandated |

## 6. Folder structure

```
verasig/
├── docker-compose.yml      Dockerfile      pyproject.toml   alembic.ini
├── apps/backend/.env.example
├── .gitignore              (secrets/, apps/backend/.env, *.session ignored)
├── secrets/                # gitignored: telegram .session, .env
├── migrations/             # alembic
├── docs/                   # business/ context/ adr/ work/
├── src/verasig/
│   ├── cli.py              # typer entrypoint: all subcommands
│   ├── config.py           # pydantic-settings runtime config
│   ├── foundation/
│   │   ├── db.py               # engine, session, Base
│   │   ├── telegram_session.py # Telethon factory + login flow
│   │   ├── telethon_source.py      # TelethonSource capture adapter
│   │   ├── static_exchange.py      # StaticExchange cold-start adapter
│   │   └── bybit_market_data.py    # BybitKlineClient (httpx) adapter
│   ├── domain/             # PURE contracts (no IO)
│   │   ├── channel.py  message.py  telegram.py  protocols.py
│   │   ├── event.py  signal.py  lifecycle.py
│   │   ├── filter_rule.py  parser_rule.py  drift.py  deletion.py  score.py
│   ├── storage/
│   │   ├── models.py       # SQLAlchemy ORM (append-only tables)
│   │   └── repositories.py # insert-only repos + queries
│   ├── services/
│   │   ├── ingestion/      backfill.py  live.py  candidate_filter.py
│   │   ├── extraction/     deterministic_parser.py  llm_fallback.py  extract_service.py
│   │   ├── distillation/   rule_distiller.py
│   │   ├── lifecycle/      fold.py
│   │   ├── deletion/       detect.py
│   │   └── scoring/        simulator.py  policies.py  hygiene.py  scorecard.py
└── tests/
    ├── conftest.py
    ├── fixtures/           # canned messages, CLI outputs, klines (golden corpora)
    ├── unit/               # pure logic, no IO
    └── integration/        # db + pipeline (mocked Telegram/LLM/market data)
```

- Files split by **responsibility**, not layer; things that change together live together.
- Folder names mirror the data flow and the compose service shape (self-documenting, per CLAUDE.md).

## 7. Secrets & auth

- `apps/backend/.env` + `secrets/` are **gitignored**; compose mounts `secrets/` read-only, injects env from `apps/backend/.env`.
- Telethon **first login is interactive** → dedicated `login` subcommand run once via `docker compose --env-file apps/backend/.env run --rm -it app login`; persists a `StringSession` into the mounted volume.
- All other commands load the session **non-interactively**; missing/invalid → fail fast ("run `login` first").
- The `.session` is **password-equivalent** (full account access); a **dedicated Telegram account** is advised given ban risk.

## 8. Scoring model (v0)

`ProviderScore` = weighted, normalized sum of components; **weights are config placeholders, not claimed optimal**.

| Component | Source | Direction |
|---|---|---|
| Simulated expectancy | sim R-multiple mean | higher better |
| Drawdown | sim MAE | lower better |
| Deletion behaviour | `DeletedSignalEvidence` rate | lower better |
| Signal frequency | events / time | context |
| Completeness | fields present / required | higher better |
| Parser confidence | extraction confidence | higher better |
| Evidence availability | captured vs missing | higher better |
| Active-user proxy | subscribers + post views | context |

- Every component value + weight + input is written to `ProviderScoreExplanation` → 100% of score changes trace to evidence.
- Re-weighting is a config change; the score recomputes deterministically.

## 9. Acceptance Criteria

- [ ] Fresh clone → `make env` → `docker compose --env-file apps/backend/.env up` brings up `db` + app on **any** Docker host.
- [ ] `docker compose --env-file apps/backend/.env run --rm -it app login` completes interactive auth; session persists across restarts.
- [ ] ≥3 pilot channels backfilled; **100%** of accessible messages captured, append-only, idempotent re-run = 0 dupes.
- [ ] Backfill is **resumable** from a persisted cursor; a mid-run kill + restart resumes and **does not refetch** captured messages.
- [ ] Pipeline runs in **bounded chunks**; peak memory stays flat on a large channel (no full-history RAM load).
- [ ] **Live latency:** median `posted_at → captured_at` ≤ the configured short-poll interval on pilot channels (hybrid push+poll closes MTProto channel-push batching; [ADR 0004](../../adr/0004-hybrid-push-poll-live-ingestion.md)).
- [ ] Distillation loop produces a `FilterRule` + `ParserRule`s and a labeled **golden corpus** for each pilot channel.
- [ ] Deterministic extraction **precision ≥ 95%** on the golden corpus; recall measured + reported.
- [ ] **100%** of LLM-fallback successes emit exactly one `ParserDriftWarning`.
- [ ] Lifecycle folding correctly applies entry→modify→close threads; no phantom lifecycles.
- [ ] `DeletedSignalEvidence` produced: CONFIRMED (snapshot-diff, content retained) + SUSPECTED (id-gap).
- [ ] Conservative simulation yields R-multiple / MTM outcomes + MFE/MAE for signals with sufficient fields.
- [ ] `ProviderScore` computed; **100%** of components traceable via `ProviderScoreExplanation`.
- [ ] Operator classification UI is future work; current scoring is CLI/evidence-first.
- [ ] `pytest` green; `ruff` clean; no secrets in git.

## 10. Risks & open items (carry forward)

| Risk | Stance |
|---|---|
| Telegram content-licensing / AI-scraping terms (history + LLM over content) | **Unresolved.** Use a dedicated Telegram account. Practice/test on real signal chats; revisit before any paid launch. Mitigated by [ADR 0005](../../adr/0005-distilled-filter-and-advisory-gate.md): only operator-selected examples reach the external LLM (rule distillation); bulk channel text is scanned only by local deterministic rules. |
| Telegram API rate/behaviour limits on user sessions | Resumable cursor + chunked pagination + flood-wait backoff; **no needless rescrape**; dedicated account. |
| Telegram channel-push latency on user accounts (~30s batching) | Hybrid push + bounded short-poll closes `pts` gaps inside the adapter; latency is measured (`posted_at → captured_at`) and gated; TDLib/Pytdbot is the documented escape hatch. See [ADR 0004](../../adr/0004-hybrid-push-poll-live-ingestion.md). |
| User-account ban / ToS | Accepted, documented; **dedicated account required**. |
| Provider scoring → regulatory risk before paid launch | Out of scope (no paid launch); conservative, evidence-only copy. |
| Optimal score formula | Open research question; re-weightable design is the hedge. |

## 11. Rollout

Build pure, fixture-driven logic first. Enable real Telegram capture and real-LLM paths only with configured credentials, a migrated database, and the risk controls above.
