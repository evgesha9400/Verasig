# Stage 0 — Local Observer: Design Spec

**Status:** draft, pending sign-off · **Date:** 2026-06-02 · **Supersedes:** nothing (first work doc)

## 1. Purpose

- Prove Verasig can **evaluate Telegram signal-provider quality** from historical + live-observed messages.
- **Observe-only.** No execution, no orders, no exchange credentials, no cloud.
- **Local-only** = the whole stack runs via `docker compose` on any machine with Docker.
- Disposable: easy to delete (`docker compose down -v`) or change.

## 2. Stage 0 pass gate (from validation-stages.md)

> The operator can classify a signal source as **good / bad / untradeable** purely from stored evidence.

- **good/bad** ← simulated outcome (expectancy, drawdown).
- **untradeable** ← incomplete/unrecognized signals (hygiene).
- Every classification must be backed by a `ProviderScoreExplanation` linking to stored evidence.

## 3. Scope

### In
- Telegram **user-account** session ingestion (Telethon).
- Public + private channel **history backfill** (first) and a **live listener** (last slice).
- Append-only `RawTelegramMessage` capture.
- Candidate filter → `RawSignalEvent`.
- Human-assisted **distillation loop** → `ParserRule`s + golden corpus (Streamlit).
- Deterministic extraction → `ExtractedSignal` | `UnrecognizedSignal`.
- LLM fallback via **Claude/Codex CLI** (behind an interface) → `ParserDriftWarning`.
- Signal **lifecycle folding** (entry + modifications + close, linked by `reply_to`).
- `DeletedSignalEvidence` (CONFIRMED snapshot-diff + SUSPECTED id-gap).
- Conservative **simulation** vs Bybit public klines (pluggable `ExecutionPolicy`).
- Re-weightable `ProviderScore` + `ProviderScoreExplanation`.
- Local **Streamlit** workbench + scorecard.

### Out (non-goals)
- Demo execution · live execution · Bybit order placement · exchange credentials.
- Cloud deployment · billing · multi-user tenancy · public launch.
- Discord · image/multimodal extraction · marketplace · portfolio management.
- Autonomous auto-research / autonomous parser-rule mining.
- Final/optimal score formula (explicit open research question — deferred).

## 4. Architecture (2-layer, per CLAUDE.md)

```
┌──────────────────────────── docker compose ────────────────────────────┐
│  FOUNDATION                                                              │
│   db (Postgres)   telegram session (volume)   secrets/ mount (.env)      │
├──────────────────────────────────────────────────────────────────────── │
│  SERVICE  (one image, many commands — typer CLI)                         │
│   login → backfill → candidates → distill(UI) → extract → fallback       │
│         → lifecycle → deletion → score → simulate → live → dashboard(UI) │
└──────────────────────────────────────────────────────────────────────── ┘
```

- **Foundation** = storage + comms config: Postgres, Telethon session, Bybit market-data client.
- **Service** = one uv-built Python image; each pipeline stage is a CLI subcommand; UI stages launch Streamlit. The live daemon is the same image run long-lived.
- **Dependency rule:** `domain/` (pure contracts) ← `services/` (logic) ← `storage/`+`foundation/` (IO). UI and CLI are thin adapters over services. Logic never imports IO frameworks directly.

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
                        Simulated outcome ─────────▶ ProviderScore + ProviderScoreExplanation ─▶ Streamlit scorecard
```

## 4.1 Processing model — resumable & chunked (hard requirement)

- **Resumable, no needless refetch.** Backfill persists a per-channel cursor (`TelegramChannel.captured_through_message_id`). On restart it resumes from the cursor; already-captured messages are **never refetched**. A separate explicit `rescan` (for deletion-diffing) is the only path that re-reads old ranges.
- **Idempotent.** All writes keyed on `(channel_id, message_id)` (raw) / deterministic ids; a crash mid-batch then restart produces zero duplicates.
- **Chunked / streaming — never load everything into RAM.** Every stage iterates in bounded batches and dumps to Postgres per batch: backfill paginates Telegram and commits every N messages; extraction/lifecycle/scoring stream rows via server-side cursors / `yield_per`; klines are fetched per-signal-window, not bulk-cached. Peak memory stays ~flat regardless of channel size.
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
| UI | **Streamlit** | least code, task-concentrated corpus, one container |
| Tests | **pytest** (+ pytest-asyncio, testcontainers-postgres) | TDD; ephemeral DB |
| Lint/format | **ruff** | mandated |

## 6. Folder structure

```
verasig/
├── docker-compose.yml      Dockerfile      pyproject.toml   alembic.ini
├── .env.example            .gitignore       (secrets/, .env, *.session ignored)
├── secrets/                # gitignored: telegram .session, .env
├── migrations/             # alembic
├── docs/                   # business/ context/ adr/ work/
├── src/verasig/
│   ├── cli.py              # typer entrypoint: all subcommands
│   ├── config.py           # pydantic-settings (foundation)
│   ├── foundation/
│   │   ├── db.py               # engine, session, Base
│   │   ├── telegram_session.py # Telethon factory + login flow
│   │   └── market_data.py      # BybitKlineClient (httpx) + MarketData interface
│   ├── domain/             # PURE contracts (no IO)
│   │   ├── channel.py  message.py  event.py  signal.py  lifecycle.py
│   │   ├── parser_rule.py  drift.py  deletion.py  score.py
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
│   └── ui/
│       ├── app.py  workbench.py  scorecard.py
└── tests/
    ├── conftest.py
    ├── fixtures/           # canned messages, CLI outputs, klines (golden corpora)
    ├── unit/               # pure logic, no IO
    └── integration/        # db + pipeline (mocked Telegram/LLM/market data)
```

- Files split by **responsibility**, not layer; things that change together live together.
- Folder names mirror the data flow and the compose service shape (self-documenting, per CLAUDE.md).

## 7. Secrets & auth

- `.env` + `secrets/` are **gitignored**; compose mounts `secrets/` read-only, injects env from `.env`.
- Telethon **first login is interactive** → dedicated `login` subcommand run once via `docker compose run --rm -it app login`; persists a `StringSession` into the mounted volume.
- All other commands load the session **non-interactively**; missing/invalid → fail fast ("run `login` first").
- The `.session` is **password-equivalent** (full account access); a **throwaway Telegram account** is advised given ban risk.

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

## 9. Stage 0 acceptance criteria

- [ ] Fresh clone → `cp .env.example .env` → `docker compose up` brings up `db` + app on **any** Docker host.
- [ ] `docker compose run --rm -it app login` completes interactive auth; session persists across restarts.
- [ ] ≥3 pilot channels backfilled; **100%** of accessible messages captured, append-only, idempotent re-run = 0 dupes.
- [ ] Backfill is **resumable** from a persisted cursor; a mid-run kill + restart resumes and **does not refetch** captured messages.
- [ ] Pipeline runs in **bounded chunks**; peak memory stays flat on a large channel (no full-history RAM load).
- [ ] **Live latency:** median `posted_at → captured_at` ≤ the configured short-poll interval on pilot channels (hybrid push+poll closes MTProto channel-push batching; [ADR 0004](../../adr/0004-hybrid-push-poll-live-ingestion.md)).
- [ ] Distillation loop produces `ParserRule`s and a labeled **golden corpus** for each pilot channel.
- [ ] Deterministic extraction **precision ≥ 95%** on the golden corpus; recall measured + reported.
- [ ] **100%** of LLM-fallback successes emit exactly one `ParserDriftWarning`.
- [ ] Lifecycle folding correctly applies entry→modify→close threads; no phantom lifecycles.
- [ ] `DeletedSignalEvidence` produced: CONFIRMED (snapshot-diff, content retained) + SUSPECTED (id-gap).
- [ ] Conservative simulation yields R-multiple / MTM outcomes + MFE/MAE for signals with sufficient fields.
- [ ] `ProviderScore` computed; **100%** of components traceable via `ProviderScoreExplanation`.
- [ ] Operator opens the Streamlit scorecard and classifies each pilot source **good/bad/untradeable** with evidence links.
- [ ] `pytest` green; `ruff` clean; no secrets in git.

## 10. Risks & open items (carry forward)

| Risk | Stance for Stage 0 |
|---|---|
| Telegram content-licensing / AI-scraping terms (history + LLM over content) | **Unresolved — operator accepted the risk for Stage 0** on a dedicated throwaway account. Practice/test on real signal chats; revisit before any paid launch. |
| Telegram API rate/behaviour limits on user sessions | Resumable cursor + chunked pagination + flood-wait backoff; **no needless rescrape**; throwaway account. |
| Telegram channel-push latency on user accounts (~30s batching) | Hybrid push + bounded short-poll closes `pts` gaps inside the adapter; latency is measured (`posted_at → captured_at`) and gated; TDLib/Pytdbot is the documented escape hatch. See [ADR 0004](../../adr/0004-hybrid-push-poll-live-ingestion.md). |
| User-account ban / ToS | Accepted, documented; **throwaway account required**. |
| Provider scoring → regulatory risk before paid launch | Out of scope (no paid launch); conservative, evidence-only copy. |
| Optimal score formula | Deferred; re-weightable design is the hedge. |

## 11. Start verdict

See `implementation-plan.md` §"Start verdict". Short version: **start now on foundation + all pure-logic, fixture-driven slices (TDD)**; gate the real-Telegram-capture and real-LLM-over-real-content slices behind git setup + explicit operator go-ahead on the documented legal risk.
