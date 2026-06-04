# Stage 0 — Local Observer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove Verasig can score Telegram signal-provider quality from captured messages, fully local (docker compose), observe-only, no execution.

**Architecture:** One uv-built Python image (Typer CLI subcommands + Streamlit UI) over a Postgres container. `domain/` pure contracts ← `services/` logic ← `storage/`+`foundation/` IO; UI/CLI are thin adapters. Every external dependency sits behind a Protocol so tests run offline.

**Tech Stack:** Python 3.12, uv, Telethon (hybrid push+poll live — [ADR 0004](../../adr/0004-hybrid-push-poll-live-ingestion.md)), Postgres 16, SQLAlchemy 2.0 + Alembic, Pydantic v2, Typer, httpx, Streamlit, pytest (+ testcontainers), ruff. LLM fallback = Claude/Codex CLI via subprocess.

---

## How to read this plan

- Slices are **vertical and dependency-ordered**: each ends green, committed, and demonstrable.
- Slice 0 and Slice 4 are fully fleshed to TDD micro-steps as the pattern; remaining slices give the frozen contract (input/output/test/acceptance + the decisive test) and are expanded just-in-time at execution per `subagent-driven-development`.
- Contracts referenced here are frozen in `data-contracts.md`; metrics in `test-plan.md`.
- **Commit after every passing step** (conventional commits). **Never skip a test.**

---

## Dependency graph

```
0 Foundation
└─1 Session/login
  └─2 Backfill (RawTelegramMessage)
    └─3 Candidate seed filter + unified distillation (FilterRule + ParserRule + golden corpus; advisory RawSignalEvent)   ── needs UI + CLI distiller
      └─4 Deterministic extract (ExtractedSignal|Unrecognized)
        ├─5 LLM fallback + drift
        ├─6 Lifecycle fold
        └─7 Deletion evidence (snapshot-diff + id-gap)
          └─8 Hygiene scorecard + ProviderScore/Explanation
            └─9 Simulation (Bybit klines, conservative)   ← FINAL scoring slice
              └─10 Live listener daemon                     ← FINAL slice overall
```

---

## Slice 0: Foundation & skeleton

**Outcome:** `docker compose up` brings up Postgres + app; `app health` connects to the DB. pytest + ruff wired.

**Files:**
- Create: `pyproject.toml`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `.gitignore`, `alembic.ini`
- Create: `src/verasig/config.py`, `src/verasig/foundation/db.py`, `src/verasig/cli.py`
- Create: `migrations/env.py`, `migrations/versions/0001_baseline.py`
- Test: `tests/conftest.py`, `tests/integration/test_foundation.py`, `tests/integration/test_migrations.py`

**Resolved gaps (grill, 2026-06-03):**
- **A — DB driver:** psycopg3. Add `psycopg[binary]`; config default URL `postgresql+psycopg://…`; conftest replace `psycopg2→psycopg` unchanged.
- **B — secrets/session:** split paths — `./secrets:/secrets:ro` (read-only inputs) + `tgsession:/session` (writable session); `session_path="/session/telegram.session"`.
- **C — Alembic:** full scaffold in Slice 0 — `migrations/env.py` (Base + Settings URL) + empty `0001_baseline.py` + an `alembic upgrade head` test on the testcontainer (satisfies test-plan "migrations apply").

- [ ] **Step 1: Init uv project + dev deps**

```bash
uv init --package --name verasig .
uv add sqlalchemy alembic "pydantic>=2" pydantic-settings typer httpx telethon streamlit "psycopg[binary]"
uv add --dev pytest pytest-asyncio testcontainers[postgres] ruff
```

- [ ] **Step 2: Write the failing config test**

```python
# tests/integration/test_foundation.py
from verasig.config import Settings

def test_settings_load_from_env(monkeypatch):
    monkeypatch.setenv("VERASIG_DATABASE_URL", "postgresql://u:p@db:5432/verasig")
    s = Settings()
    assert s.database_url.endswith("/verasig")
```

- [ ] **Step 3: Run it, verify it fails**

Run: `uv run pytest tests/integration/test_foundation.py::test_settings_load_from_env -v`
Expected: FAIL — `ModuleNotFoundError: verasig.config`.

- [ ] **Step 4: Minimal config**

```python
# src/verasig/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VERASIG_", env_file=".env")
    database_url: str = "postgresql+psycopg://verasig:verasig@db:5432/verasig"
    telegram_api_id: int | None = None
    telegram_api_hash: str | None = None
    session_path: str = "/session/telegram.session"
```

- [ ] **Step 5: Verify config test passes**

Run: `uv run pytest tests/integration/test_foundation.py::test_settings_load_from_env -v` → PASS.

- [ ] **Step 6: Write the failing DB-health test**

```python
# tests/integration/test_foundation.py (add)
from sqlalchemy import text
from verasig.foundation.db import make_engine

def test_health_connects(pg_url):                      # pg_url from conftest (testcontainers)
    engine = make_engine(pg_url)
    with engine.connect() as conn:
        assert conn.execute(text("select 1")).scalar() == 1
```

```python
# tests/conftest.py
import pytest
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="session")
def pg_url():
    with PostgresContainer("postgres:16") as pg:
        yield pg.get_connection_url().replace("psycopg2", "psycopg")
```

- [ ] **Step 7: Run it, verify it fails**

Run: `uv run pytest tests/integration/test_foundation.py::test_health_connects -v`
Expected: FAIL — `verasig.foundation.db` missing.

- [ ] **Step 8: Minimal engine + Base**

```python
# src/verasig/foundation/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

class Base(DeclarativeBase): ...

def make_engine(url: str):
    return create_engine(url, future=True)

def make_session_factory(url: str):
    return sessionmaker(bind=make_engine(url), future=True)
```

- [ ] **Step 9: Verify health test passes**

Run: `uv run pytest -v` → PASS.

- [ ] **Step 9a: Write the failing Alembic apply test (Gap C)**

```python
# tests/integration/test_migrations.py
from alembic import command
from alembic.config import Config

def test_migrations_apply(pg_url):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", pg_url)
    command.upgrade(cfg, "head")        # no error == migrations apply
```
Run: `uv run pytest tests/integration/test_migrations.py -v` → FAIL (no alembic env yet).

- [ ] **Step 9b: Scaffold Alembic + empty baseline**

`uv run alembic init migrations`, then wire `migrations/env.py`:
- import `Base` from `verasig.foundation.db`; `target_metadata = Base.metadata`
- resolve URL from `Settings().database_url`, overridable via `config.get_main_option("sqlalchemy.url")` (tests inject the testcontainer URL).

Add an empty baseline `migrations/versions/0001_baseline.py` (`down_revision = None`, `def upgrade(): pass`, `def downgrade(): pass`). Verify Step 9a → PASS. Commit.

- [ ] **Step 10: CLI `health` subcommand**

```python
# src/verasig/cli.py
import typer
from sqlalchemy import text
from verasig.config import Settings
from verasig.foundation.db import make_engine

app = typer.Typer()

@app.command()
def health():
    with make_engine(Settings().database_url).connect() as c:
        c.execute(text("select 1"))
    typer.echo("OK: db connected")

if __name__ == "__main__":
    app()
```

- [ ] **Step 11: Compose + Dockerfile + ignore files**

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:16
    environment: { POSTGRES_USER: verasig, POSTGRES_PASSWORD: verasig, POSTGRES_DB: verasig }
    volumes: [ "pgdata:/var/lib/postgresql/data" ]
  app:
    build: .
    env_file: [ .env ]
    volumes: [ "./secrets:/secrets:ro", "tgsession:/secrets" ]
    depends_on: [ db ]
    command: [ "health" ]
volumes: { pgdata: {}, tgsession: {} }
```
```dockerfile
# Dockerfile
FROM python:3.12-slim
RUN pip install uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .
ENTRYPOINT ["uv","run","verasig"]
```
```gitignore
# .gitignore
.env
secrets/
*.session
.venv/
__pycache__/
```

- [ ] **Step 12: Manual acceptance + commit**

Run: `docker compose up -d db && docker compose run --rm app health`
Expected: `OK: db connected`.
```bash
git add -A && git commit -m "feat: foundation skeleton (compose, postgres, config, cli health)"
```

---

## Slice 1: Telegram session & login

- **Input:** `telegram_api_id`/`hash`/`phone` (env), interactive code/2FA (once).
- **Output:** persisted `StringSession` (bare UTF-8 string at `session_path`); non-interactive client for all other commands.
- **Decisive test (unit):** session-string round-trips (`save`→`load`); missing/empty session raises `SessionMissingError("run `login` first")`; absent creds raise `CredentialsMissingError`.
- **Contract:** `TelegramSource` Protocol (`data-contracts.md` §9) — Protocol-only stub this slice; `backfill_batches`/`live_events` are implemented in Slices 2/10. Slice 1's own seam is the session store + guarded client factory in `telegram_session.py`.
- **Acceptance:** `docker compose run --rm -it app login` completes once; `app whoami` then prints the account non-interactively across restarts.
- **Note:** tests never authenticate against real Telegram — `login`/`whoami`'s live calls are exercised manually; only load/persist/guard + the pure `format_account` formatter are unit-tested.

**Resolved gaps (grill, 2026-06-03):**
- **Seam (Q1):** ship **both** `foundation/telegram_source.py` (full async `TelegramSource` Protocol, Protocol-only) **and** `foundation/telegram_session.py` (session store + guards + client factory + login). The §9 `TelegramSource` reference is forward-looking — Slice 1 stubs the Protocol, does not implement its methods.
- **Protocol types (Q2):** to type the stubbed Protocol, pull in **pure contracts only** — `domain/message.py` (`RawTelegramMessage` per §2 + `DeliveryMode` enum per §1) and `TelegramDeliveryEvent` (in `telegram_source.py` per §9). NO ORM, NO migration, NO backfill logic (those stay in Slice 2). `DeliveryMode` lives in `domain/message.py` (enum with its entity); foundation imports domain, never the reverse.
- **login UX (Q3):** add `telegram_phone: str | None` to `Settings` + `.env(.example)`; `client.start(phone=settings.telegram_phone)` prompts for code + 2FA interactively. api_id/hash stay env-sourced.
- **Creds absent (Q4):** `make_client` raises `CredentialsMissingError("set VERASIG_TELEGRAM_API_ID and VERASIG_TELEGRAM_API_HASH")` (creds-check **before** session-load) so Slice-0 `health` keeps working with creds Optional.
- **whoami (Q5):** one line incl. phone — `logged in as @handle · First Last · id=N · +phone`; missing username/last_name omitted gracefully. Pure `format_account(user) -> str` is table-tested with a stub; live `get_me()` is manual.

**Files:**
- Create: `src/verasig/domain/__init__.py`, `src/verasig/domain/message.py`, `src/verasig/foundation/telegram_source.py`, `src/verasig/foundation/telegram_session.py`
- Edit: `src/verasig/config.py` (+`telegram_phone`), `src/verasig/cli.py` (+`login`, +`whoami`), `.env`, `.env.example`
- Test: `tests/unit/test_domain_message.py`, `tests/unit/test_telegram_source.py`, `tests/unit/test_telegram_session.py`

---

## Slice 2: History backfill → RawTelegramMessage (resumable + chunked)

- **Input:** `channel_id`.
- **Output:** append-only `RawTelegramMessage` rows + a `TelegramChannel` row (with `subscriber_count`), and an advancing `captured_through_message_id` cursor.
- **Resilience/resource requirements (spec §4.1):**
  - Paginate Telegram oldest→newest in batches of `N` (config, e.g. 200); **commit each batch** + advance cursor in the same transaction.
  - On start, **resume from `captured_through_message_id`**; never refetch captured ids.
  - Never hold the full history in RAM — process one batch at a time, then release.
  - Flood-wait/rate-limit → exponential backoff, then resume from cursor.
- **Decisive tests (integration, PG + FakeSource over `fixtures/messages`):**
  - persists every message with full provenance; unique `(channel_id, message_id)`; **idempotent re-run adds 0**; raw table never UPDATEd.
  - **resume:** run backfill, kill after batch 1 (FakeSource raises mid-stream), restart → continues from cursor, final row count correct, **0 refetched ids** (FakeSource asserts it was never asked for ids ≤ cursor).
  - **chunking:** FakeSource of 10k messages with batch=200 → at most batch-size objects materialized at once (assert via a counting/streaming fake).
- **Acceptance:** backfill a real channel → row count == accessible count; mid-run kill + restart resumes with no refetch and no dupes; `app stats <channel>` prints capture count + cursor.

**Resolved gaps (grill, 2026-06-03):**
- **Channel resolve (Q1):** add `async resolve_channel(reference: str | int) -> TelegramChannel` to the `TelegramSource` Protocol (synced into data-contracts §9). `backfill` resolves first (→ id, title, handle, subscriber_count), upserts the `TelegramChannel` row, then streams `backfill_batches(channel_id, after=cursor, batch)`. CLI accepts `@handle` / id / `t.me` link; `FakeSource.resolve_channel` returns a canned channel.
- **Defaults (reversible, taken inline):**
  - `raw_payload` ORM column → Postgres **JSONB**; idempotency → `INSERT … ON CONFLICT (channel_id, message_id) DO NOTHING`.
  - cursor `captured_through_message_id` = committed high-water mark; paginate **oldest→newest**, resume via `after_message_id=cursor`; batch insert + cursor advance in **one transaction**.
  - `backfill_batch_size: int = 200` added to `Settings`.
  - `stats <ref>` prints `@handle id=N · title · captured=X · cursor=Y · subs=Z`.
  - Test fixtures: synthetic anonymized `fixtures/messages/*.jsonl` driven by `FakeSource`; real `TelethonSource` (resolve + `iter_messages(reverse=True, min_id=cursor)` + flood-wait backoff) is **manual-acceptance only**, never in tests.

**Files:**
- Create: `src/verasig/domain/channel.py`, `src/verasig/storage/__init__.py`, `src/verasig/storage/models.py`, `src/verasig/storage/repositories.py`, `src/verasig/services/__init__.py`, `src/verasig/services/ingestion/__init__.py`, `src/verasig/services/ingestion/backfill.py`, `migrations/versions/0002_*.py`
- Edit: `src/verasig/config.py` (+`backfill_batch_size`), `src/verasig/foundation/telegram_source.py` (+`resolve_channel`, +`TelethonSource`), `src/verasig/cli.py` (+`migrate`, +`backfill`, +`stats`)
- Note: added a `migrate` subcommand (`alembic upgrade head`) so the deployed container can create the Slice-2 tables before `backfill` (`docker compose run --rm app migrate`).
- Test: `tests/fixtures/messages/*.jsonl`, `tests/integration/test_backfill.py`, `tests/unit/test_fake_source.py` (+ Protocol conformance)

---

## Slice 3: Candidate seed filter + unified distillation → FilterRule + ParserRule + golden corpus

> Merges the former candidate-filter and distillation-loop slices ([ADR 0005](../../adr/0005-distilled-filter-and-advisory-gate.md)). The candidate filter is **advisory** (priority/triage, not a hard gate); its rules are **distilled** from the same `GoldenLabel` pass that produces parser rules.

- **Input:** a channel's `RawTelegramMessage` corpus.
- **Output:**
  - advisory `RawSignalEvent`s — first from a cheap **seed heuristic**, then from distilled `FilterRule`s;
  - `FilterRule` (recall-first, from `is_signal`) + `ParserRule`s (precision-first, from `expected` fields), distilled in one workbench loop;
  - `GoldenLabel`s (the golden corpus);
  - `FilterDriftWarning`s when a background parse / audit finds a signal the filter missed.
- **Contracts:** `RawSignalEvent` (advisory, §2), `FilterRule`, `ParserRule`, `FilterDriftWarning`, `GoldenLabel` (§4); `RuleDistiller` Protocol (`distill_filter` + `distill_parsers`, §9).
- **Seam / mechanism (ADR 0005):**
  - **Seed (cold start):** a pure, recall-first heuristic — candidate if the text holds an exchange-listed symbol/base coin (via an `Exchange` Protocol seam, e.g. a `Bybit` adapter + `FakeExchange` in tests), a directional keyword (EN+RU), or a trade-structure keyword/emoji. `matched_reasons: list[MatchReason]`; `candidate_text` = verbatim message text; media-only/blank → not a candidate.
  - **Distillation:** operator labels `is_signal` (+ expected fields for positives) in the Streamlit workbench; the external LLM distils a recall-first `FilterRule` and precision-first `ParserRule`s; rules applied, matched messages filtered, residue + a random unflagged sample re-presented; repeat. Only operator-selected examples leave the machine (privacy §10); bulk text is scanned only by local deterministic rules.
  - **Advisory gate:** deterministic rules may run over all `RawTelegramMessage`s; a hit on a non-candidate **late-materializes** a `RawSignalEvent` (`materialized_by=PARSER_BACKFILL`) + emits a `FilterDriftWarning`.
- **UI — distillation workbench (Streamlit):** the operator must reach *beyond* candidates, not just label inside a pre-filtered list.

  ```
  ┌ Distillation workbench — @channel ───────────────────────────────────┐
  │ View: ( Candidates | Unflagged | ⚠ Drift | 🎲 Audit )                 │
  │ Recall vs GoldenLabel:  filter 0.93   parser P 0.96    Residue: 41    │
  ├───────────────────────────────────────────────────────────────────── │
  │ #1042  "BTC long entry 65k SL 64k TP 67k"            [✓ signal][fields]│
  │ #1044  "gm frens wagmi"                               [✗ not]          │
  │ #1047  "зашёл по эфиру, стоп под лоем"     ⚠ filter-miss [✓ signal][…] │
  ├───────────────────────────────────────────────────────────────────── │
  │ [ Distil rules from labels ] → FilterRule v3 (recall) + ParserRule r7 │
  └─────────────────────────────────────────────────────────────────────  ┘
  ```

  - **View switcher** — `Candidates` (flagged, priority order) · `Unflagged` (the rest) · `⚠ Drift` (the `FilterDriftWarning` queue) · `🎲 Audit` (random unflagged sample, to discover missed formats). A hard gate would only ever show `Candidates`.
  - **One label, two grounds** — `✓/✗ signal` trains the `FilterRule`; `[fields]` trains the `ParserRule`s. Single pass, two objectives.
  - **Filter-recall meter (vs `GoldenLabel`)** — the gate's miss-rate is *visible* (it was unmeasurable under a hard gate).
  - **Distil action** — one button emits a recall-first `FilterRule` + precision-first `ParserRule`s; matched messages drop out; residue + a fresh random sample re-present.
  - **Loop:** label → distil → matched drop out → residue + audit sample re-presented → repeat until residue is small and recall holds.
- **Runtime behaviour (advisory, not a wall):**
  - candidate derivation sets **priority**, blocks nothing;
  - the **cheap deterministic parser sweeps all** `RawTelegramMessage`s in bounded batches; a hit on a non-candidate late-materializes a `RawSignalEvent` (`PARSER_BACKFILL`) + a `FilterDriftWarning`;
  - the **expensive LLM fallback stays scoped to candidates/residue** (cost + §10 unchanged) — only the cheap parse went broad;
  - filter misses are therefore **recoverable + visible**, never silent; each drift warning is a labeled example for the next distillation;
  - **cold start:** before any labels, the workbench shows seed-heuristic hits first **plus** a chronological/random sample so the operator can bootstrap the first labels without a working filter.
- **Decisive tests:**
  - unit (pure, table-driven): seed filter — chatter→reject; directional/symbol/price→accept; `matched_reasons` recorded; recall-first over-include; `Exchange` symbols injected (offline).
  - unit (pure): `FilterRule`/`ParserRule` application is pure + table-driven against fixtures; `FakeDistiller(labels)` returns a `FilterRule` + `ParserRule`s.
  - integration: labels + rules persist; **re-applying distilled rules reproduces the labels** (filter recall ≥ target on `is_signal`; parser ≥ target precision on `expected`); a planted filter miss emits exactly one `FilterDriftWarning`.
  - smoke (optional): Streamlit `AppTest` drives label → distil(filter+parser) → filter → iterate; residue + unflagged sample shrink.
- **Acceptance:** candidate **recall ≥ 0.95** of human-labeled signals on the labeled corpus (false positives acceptable — extraction filters them); operator labels a pilot channel via the UI; both rule kinds produced; residue shrinks each pass; golden corpus saved. **Metric denominator = `GoldenLabel`** (filter recall on `is_signal`; parser precision/recall on `expected`), not the candidate subset.
- **Note:** real external-LLM distillation is gated behind operator go-ahead (selected examples → real LLM; see Start verdict). The seed filter + rule application are pure/offline and fixture-testable now. A local `FilterGemma`/`ParserGemma` is deferred to a later stage (ADR 0005).

**Resolved gaps (grill, 2026-06-04) — Slices 3 + 4 execute as ONE pass:**

> **Status (2026-06-04): IMPLEMENTED — green + committed** on `feature/stage-0-foundation`. 161 tests pass, ruff clean. Filter recall + parser precision = **1.00** on the golden corpus (gate 0.95); planted filter-miss → exactly one `FilterDriftWarning`; Streamlit workbench `AppTest` smoke (label→distil→filter→iterate) green. Real-LLM `ClaudeCliDistiller` Distil + UI-over-real-content remain **go-ahead-gated manual acceptance** (no test touches the real CLI). Next: Slice 5 (LLM fallback).

- **Scope:** build the entire merged slice now — seed filter + distillation (incl. Streamlit workbench + real `ClaudeCliDistiller`) **and** all of Slice 4 (deterministic extraction). The real-LLM Distil + UI-over-real-content stay **go-ahead-gated manual acceptance**; tests stay offline (FakeDistiller, canned `cli/distill_*.txt`, FakeExchange).
- **3/4 boundary:** Slice 4 absorbed wholesale — `ExtractedSignal`/`UnrecognizedSignal` + `Side`/`EntryType`/`SignalEventType`, `deterministic_parser.parse`, `ExtractService` (one-of; required symbol+side; `fallback=None` until Slice 5), precision ≥ 0.95 harness.
- **Exchange seam:** `foundation/exchange.py` = `Exchange` Protocol (`is_listed`/`base_symbols`) + bundled `StaticExchange` seed + `FakeExchange` (tests); real `BybitExchange(httpx)` deferred to Slice 9.
- **Distiller output:** LLM emits JSON `{filter_rule, parser_rules}` (pattern content only); shared `parse_distiller_output` tolerantly extracts (bare or ```json-fenced) + Pydantic-validates; the adapter stamps `rule_id`/`version`/`created_at`/`distilled_from_label_ids` (provenance never hallucinated).
- **MatchReason:** frozen 3-value enum kept — `DIRECTIONAL_KEYWORD` (long/short/buy/sell + RU), `SYMBOL_TOKEN` (Exchange-listed), `PRICE_SHAPED` (subsumes trade-structure keywords/emoji + price patterns).
- **Persistence:** migration `0003` adds all 7 tables — `raw_signal_event`, `extracted_signal`, `unrecognized_signal`, `filter_rule`, `parser_rule`, `golden_label`, `filter_drift_warning`; list/map fields + `GoldenLabel.expected` as JSONB; conftest TRUNCATE extended.
- **Fixtures:** synthetic anonymized `tests/fixtures/{messages,labels}/pilot.jsonl` (~50 msgs, EN+RU; signals / partials / chatter + ≥1 planted filter-miss). Oracle for filter-recall ≥ 0.95 (denominator = `GoldenLabel.is_signal`) + parser-precision ≥ 0.95 (`expected`).
- **UI:** full 4-view workbench (Candidates | Unflagged | ⚠ Drift | 🎲 Audit) — pure presenter in `services/distillation/workbench.py`, thin `ui/workbench.py`, `AppTest` smoke.
- **CLI:** `candidates` (derive) · `workbench` (Streamlit) · `extract` (candidates → signal/unrecognized) · `sweep` (advisory parse-all → late-materialize `PARSER_BACKFILL` + `FilterDriftWarning`). `candidates`/`extract`/`sweep` are offline; only the workbench Distil-click reaches the real LLM.
- **Decided inline (doc/precedent):** enums co-located with their entity (`DeliveryMode` precedent); `uuid4` / `datetime.now(tz=utc)` defaults (tests pass explicit instants); `candidate_text` = verbatim text; media-only/blank → non-candidate; late-materialization idempotent on `(channel_id, message_id)`.

**Files (this pass):**
- `domain/`: `event.py` `signal.py` `filter_rule.py` `parser_rule.py` `label.py` `drift.py`
- `foundation/exchange.py`
- `services/ingestion/candidate_filter.py` (seed + FilterRule apply + derivation + advisory sweep), `services/extraction/{deterministic_parser.py, extract_service.py}`, `services/distillation/{rule_distiller.py, workbench.py}`
- `storage/models.py` (+7 rows), `storage/repositories.py`, `migrations/versions/0003_*.py`
- `ui/app.py` `ui/workbench.py`; `cli.py` (+`candidates`/`workbench`/`extract`/`sweep`), `config.py` (+`distiller_command`)
- `tests/unit/*`, `tests/integration/*`, `tests/fixtures/{messages,labels,cli}/*`, `tests/fakes.py` (+`FakeExchange`, +`FakeDistiller`)

---

## Slice 4: Deterministic extraction → ExtractedSignal | UnrecognizedSignal

> **Absorbed into the Slice 3 pass (grill 2026-06-04).** The contracts + parser + `ExtractService` + precision harness below are built together with Slice 3; the steps remain as the TDD micro-pattern. Slice 5 (LLM fallback) stays the next slice.

**Outcome:** apply `ParserRule`s to a `RawSignalEvent`, producing exactly one of `{ExtractedSignal, UnrecognizedSignal}`, enforcing `symbol`+`side` required and side normalization.

**Files:**
- Create: `src/verasig/domain/signal.py`, `src/verasig/services/extraction/deterministic_parser.py`, `src/verasig/services/extraction/extract_service.py`
- Test: `tests/unit/test_deterministic_parser.py`

- [ ] **Step 1: Write the failing required-fields test**

```python
# tests/unit/test_deterministic_parser.py
from decimal import Decimal
from verasig.services.extraction.deterministic_parser import parse
from verasig.domain.parser_rule import ParserRule

RULE = ParserRule(
    rule_id="r1", version=1,
    patterns=[r"(?P<symbol>[A-Z]{2,10})\s+(?P<side>long|short|buy|sell)"
              r"(?:.*?entry\s+(?P<entry>\d+))?(?:.*?sl\s+(?P<sl>\d+))?(?:.*?tp\s+(?P<tp>\d+))?"],
    field_map={"symbol":"symbol","side":"side","entry":"entry_single","sl":"stop_loss","tp":"take_profit"},
    side_aliases={"long":"LONG","buy":"LONG","short":"SHORT","sell":"SHORT"},
)

def test_full_signal_parses():
    s = parse(RULE, "BTC long entry 65000 sl 64000 tp 67000")
    assert (s.symbol, s.side) == ("BTCUSDT", "LONG")
    assert s.entry_low == s.entry_high == Decimal("65000")
    assert s.stop_loss == Decimal("64000") and s.take_profits == [Decimal("67000")]

def test_market_entry_no_price():
    s = parse(RULE, "ETH sell market")
    assert (s.symbol, s.side, s.entry_type) == ("ETHUSDT", "SHORT", "MARKET")
    assert s.stop_loss is None and s.take_profits == []

def test_no_side_is_unrecognized():
    assert parse(RULE, "BTC looking strong") is None   # → UnrecognizedSignal upstream
```

- [ ] **Step 2: Run, verify all fail**

Run: `uv run pytest tests/unit/test_deterministic_parser.py -v`
Expected: FAIL — module/`ExtractedSignal` missing.

- [ ] **Step 3: Define the canonical contract**

```python
# src/verasig/domain/signal.py
from decimal import Decimal
from enum import StrEnum
from pydantic import BaseModel, model_validator

class Side(StrEnum): LONG="LONG"; SHORT="SHORT"
class EntryType(StrEnum): MARKET="MARKET"; LIMIT_SINGLE="LIMIT_SINGLE"; LIMIT_RANGE="LIMIT_RANGE"

class ExtractedSignal(BaseModel):
    symbol: str
    side: Side
    entry_type: EntryType | None = None
    entry_low: Decimal | None = None
    entry_high: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profits: list[Decimal] = []
    parser_confidence: float = 1.0
    rule_id: str | None = None

    @model_validator(mode="after")
    def _require_core(self):
        if not self.symbol or self.side is None:
            raise ValueError("symbol and side are required")
        return self
```

- [ ] **Step 4: Minimal parser**

```python
# src/verasig/services/extraction/deterministic_parser.py
import re
from decimal import Decimal
from verasig.domain.signal import ExtractedSignal, Side, EntryType

def _symbol(raw: str) -> str:
    raw = raw.upper()
    return raw if raw.endswith("USDT") else f"{raw}USDT"

def parse(rule, text: str) -> ExtractedSignal | None:
    for pat in rule.patterns:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if not m: continue
        gd = m.groupdict()
        side_raw = (gd.get("side") or "").lower()
        if not gd.get("symbol") or side_raw not in rule.side_aliases:
            return None
        entry = gd.get("entry")
        return ExtractedSignal(
            symbol=_symbol(gd["symbol"]),
            side=Side(rule.side_aliases[side_raw]),
            entry_type=EntryType.LIMIT_SINGLE if entry else EntryType.MARKET,
            entry_low=Decimal(entry) if entry else None,
            entry_high=Decimal(entry) if entry else None,
            stop_loss=Decimal(gd["sl"]) if gd.get("sl") else None,
            take_profits=[Decimal(gd["tp"])] if gd.get("tp") else [],
            rule_id=rule.rule_id,
        )
    return None
```

- [ ] **Step 5: Verify parser tests pass**

Run: `uv run pytest tests/unit/test_deterministic_parser.py -v` → PASS.

- [ ] **Step 6: Write failing extract-service test (one-of invariant)**

```python
# tests/unit/test_extract_service.py
from verasig.services.extraction.extract_service import ExtractService

def test_yields_exactly_one_outcome():
    out = ExtractService(rules=[RULE], fallback=None).extract(event("BTC long entry 65000"))
    assert out.signal is not None and out.unrecognized is None

def test_unparseable_yields_unrecognized():
    out = ExtractService(rules=[RULE], fallback=None).extract(event("gm frens"))
    assert out.signal is None and out.unrecognized is not None
    assert out.unrecognized.reason in {"no_match","no_side","no_symbol"}
```

- [ ] **Step 7: Run, verify fail; then implement ExtractService (deterministic-only)**

```python
# src/verasig/services/extraction/extract_service.py
from dataclasses import dataclass
from verasig.domain.signal import ExtractedSignal
from verasig.services.extraction.deterministic_parser import parse

@dataclass
class ExtractOutcome:
    signal: ExtractedSignal | None = None
    unrecognized: "UnrecognizedSignal | None" = None
    drift_warnings: list = None

class ExtractService:
    def __init__(self, rules, fallback=None):
        self.rules, self.fallback = rules, fallback
    def extract(self, event) -> ExtractOutcome:
        for rule in self.rules:
            s = parse(rule, event.candidate_text)
            if s: return ExtractOutcome(signal=s, drift_warnings=[])
        # fallback wired in Slice 5
        return ExtractOutcome(unrecognized=_unrecognized(event, "no_match"), drift_warnings=[])
```

- [ ] **Step 8: Verify pass; precision harness; commit**

Run: `uv run pytest tests/unit -v` → PASS.
Add `tests/integration/test_precision_recall.py` using `fixtures/labels` → assert `precision >= 0.95`, report recall.
```bash
git add -A && git commit -m "feat: deterministic extraction with required symbol+side and one-of outcome"
```

---

## Slice 5: LLM fallback + ParserDriftWarning

- **Input:** `RawSignalEvent` that missed deterministic parsing.
- **Output:** `ExtractedSignal` (method=`LLM_FALLBACK`) or `UnrecognizedSignal`; **one `ParserDriftWarning` per fallback success**.
- **Contracts:** `LlmExtractor` Protocol; adapters `ClaudeCliExtractor`/`CodexCliExtractor` (subprocess parse) + `FakeExtractor`.
- **Decisive tests (unit):** fallback called **only** on deterministic miss; success ⇒ exactly one drift warning (100% coverage metric); CLI-output parser tested against `fixtures/cli/extract_*.txt`; **real CLI never invoked**.
- **Acceptance:** replay corpus → unmatched events route to fallback → drift warnings 1:1 with fallback successes; gated behind operator go-ahead (real content → real LLM; see Start verdict).

---

## Slice 6: Signal lifecycle fold

- **Input:** `ExtractedSignal`s + `reply_to` links, time-ordered.
- **Output:** `FoldedSignal` (entry + applied modifications + optional close).
- **Decisive tests (unit, pure):** entry then "move SL to BE" reply ⇒ effective SL updated at modification time; CLOSE terminates; **standalone complete signal stays single-step (no phantom lifecycle)**; out-of-order updates handled.
- **Acceptance:** a crafted entry→modify→close thread folds to the expected effective-parameter timeline.

---

## Slice 7: Deletion evidence

- **Input:** two backfill snapshots (live events later).
- **Output:** `DeletedSignalEvidence` — `CONFIRMED` (snapshot-diff, content retained) + `SUSPECTED` (id-gap).
- **Decisive tests (unit, pure):** present-then-absent ⇒ CONFIRMED with original text + `was_signal_candidate`; id-gap in sequence ⇒ SUSPECTED (no content); contiguous ids ⇒ nothing.
- **Acceptance:** delete a message between two re-scans ⇒ CONFIRMED evidence retaining the original content.

---

## Slice 8: Hygiene scorecard + ProviderScore/Explanation

- **Input:** events, signals, drift, deletions, active-user proxy (sim components null/pending).
- **Output:** `ProviderScore` + `ProviderScoreExplanation`.
- **Decisive tests (unit, pure):** each metric fn (frequency, completeness, parser-confidence, deletion rate, proxy); composite = Σ(normalized×weight); **every component has `evidence_refs`**; re-weighting changes the score deterministically; "0 simulable signals" noted.
- **Acceptance:** scorecard renders per provider; 100% of components trace to stored evidence.

---

## Slice 9: Simulation (FINAL scoring slice)

- **Input:** `FoldedSignal`s + Bybit klines + `ExecutionPolicy`.
- **Output:** `SimOutcome` per signal (R-multiple/MTM, MFE/MAE) → fills sim components of `ProviderScore`.
- **Contracts:** `MarketData` Protocol (`BybitKlineClient` httpx + Fake); `ExecutionPolicy` (`ProviderStatedPolicy`).
- **Decisive tests (unit, canned klines):** market fill=next-candle open; limit never reached ⇒ `UNFILLED`; **same-candle stop+tp ⇒ stop-first (-1R)**; MFE/MAE; policy **injectable** (dummy `CustomRiskPolicy` proves the seam).
- **Acceptance:** known signal + known klines ⇒ expected conservative R; scorecard shows simulated expectancy + drawdown with full explanation.

---

## Slice 10: Live listener daemon (FINAL slice overall)

- **Input:** running Telethon session + pilot `channel_ids`.
- **Output:** continuous `RawTelegramMessage` capture via **hybrid push+poll** (passive `events.NewMessage` + bounded short-poll closing `pts` gaps, deduped on `(channel_id, message_id)`) + real-time `DeletedSignalEvidence` (LIVE_EVENT, precise timing). Capture is **queue-first**: persist the row immediately, parse/score async — never block the update loop.
- **Contract:** `TelegramSource.live_events(channel_ids)` → `TelegramDeliveryEvent` (`mode`, `captured_at`, `pts`); see [ADR 0004](../../adr/0004-hybrid-push-poll-live-ingestion.md).
- **Decisive tests (unit/integration, fake event stream):**
  - push event ⇒ row tagged `mode=PUSH`; delayed/absent push then poll ⇒ same message arrives **once** (`mode=POLL`/`CATCH_UP`), deduped vs push and vs backfill.
  - delete event ⇒ CONFIRMED evidence with timestamp.
  - **latency:** with a fake clock, median `captured_at − posted_at` ≤ the configured poll interval.
- **Acceptance:** run `app live <channels>`, post + delete a test message ⇒ captured (within the poll interval) then CONFIRMED-deleted with timestamps.

---

## Start verdict

**Start now — partially.** The plan and contracts are clear and frozen. Two preconditions and one gate:

1. **Precondition — git (CLAUDE.md mandates it):** `git init`, create `main` (+ `develop`), commit the docs, then branch `feature/stage-0-foundation`. The repo currently has no VCS.
2. **Start immediately (no external/legal exposure):** Slices **0, 4, 6, 7, 8, 9** — plus the **seed filter + rule-application** of Slice 3 — are pure-logic / fixture-driven — build them TDD against committed fixtures with **zero** Telegram, LLM, or network calls. This is the bulk of the engine and proves the thesis on recorded data.
3. **Reality slices — operator has given go-ahead (accepted risk).** Slices **1, 2, 5, 10** — plus **Slice 3's distillation sub-step** (external LLM over operator-selected examples only) — touch a real Telegram account and/or a real LLM. The operator **accepted the legal risk for Stage 0** on a **dedicated throwaway Telegram account** (Telegram content-licensing + AI-scraping terms remain unresolved; revisit before paid launch). Per ADR 0005, bulk channel text is never sent to the external LLM. Constraints: resumable + chunked (spec §4.1) — **no rescrape on restart**, process in batches, never load full history into RAM.

> Recommended first move: git init → Slice 0 → Slice 3's seed filter + Slices 4/6/7 against fixtures, then bring real Telegram online (Slices 1→2) and run Slice 3's distillation on the throwaway account.

## Self-review notes

- **Spec coverage:** every entity in `data-contracts.md` maps to a slice (channel/message→2; event + FilterRule/ParserRule + GoldenLabel + FilterDriftWarning→3; signal/unrecognized→4; parser-drift→5; folded→6; deletion→7; score/explanation→8; sim→9; live→10). ✓
- **Type consistency:** `ExtractedSignal` fields, `Side`/`EntryType`/`MatchReason`/`MaterializationPath` enums, `ExtractOutcome`, `FilterRule`/`ParserRule`, and Protocol names match across slices and `data-contracts.md`. ✓
- **No placeholders:** Slices 0 and 4 carry full code; later slices carry frozen contracts + decisive tests, expanded JIT at execution per the chosen execution skill. ✓
