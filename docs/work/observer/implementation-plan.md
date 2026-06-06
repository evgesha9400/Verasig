# Observer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove Verasig can score Telegram signal-provider quality from captured messages, fully local (docker compose), observe-only, no execution.

**Architecture:** One uv-built Python image (Typer CLI subcommands + Streamlit UI) over a Postgres container. `domain/` pure contracts ← `services/` logic ← `storage/` repositories + `foundation/` adapters; UI/CLI are thin adapters. Every external dependency sits behind a Protocol so tests run offline.

**Tech Stack:** Python 3.12, uv, Telethon (hybrid push+poll live — [ADR 0004](../../adr/0004-hybrid-push-poll-live-ingestion.md)), Postgres 16, SQLAlchemy 2.0 + Alembic, Pydantic v2, Typer, httpx, Streamlit, pytest (+ testcontainers), ruff. LLM fallback = Claude/Codex CLI via subprocess.

---

## How to read this plan

- work items are **vertical and dependency-ordered**: each ends green, committed, and demonstrable.
- work item 0 and work item 4 are fully fleshed to TDD micro-steps as the pattern; remaining work items give the frozen contract (input/output/test/acceptance + the decisive test) and are expanded just-in-time at execution per `subagent-driven-development`.
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
            └─9 Simulation (Bybit klines, conservative)   ← scoring path
              └─10 Live listener daemon                     ← live capture path
```

---

## work item 0: Foundation & skeleton

**Outcome:** `docker compose up` brings up Postgres + app; `app health` connects to the DB. pytest + ruff wired.

**Files:**
- Create: `pyproject.toml`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `.gitignore`, `alembic.ini`
- Create: `src/verasig/config.py`, `src/verasig/foundation/db.py`, `src/verasig/cli.py`
- Create: `migrations/env.py`, `migrations/versions/0001_baseline.py`
- Test: `tests/conftest.py`, `tests/integration/test_foundation.py`, `tests/integration/test_migrations.py`

**Resolved gaps (grill, 2026-06-03):**
- **A — DB driver:** psycopg3. Add `psycopg[binary]`; config default URL `postgresql+psycopg://…`; conftest replace `psycopg2→psycopg` unchanged.
- **B — secrets/session:** split paths — `./secrets:/secrets:ro` (read-only inputs) + `tgsession:/session` (writable session); `session_path="/session/telegram.session"`.
- **C — Alembic:** full scaffold in work item 0 — `migrations/env.py` (Base + Settings URL) + empty `0001_baseline.py` + an `alembic upgrade head` test on the testcontainer (satisfies test-plan "migrations apply").

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
    monkeypatch.setenv("VERASIG_DB_HOST", "db")
    monkeypatch.setenv("VERASIG_DB_NAME", "verasig")
    s = Settings()
    assert s.database_url == "postgresql+psycopg://verasig:verasig@db:5432/verasig"
```

- [ ] **Step 3: Run it, verify it fails**

Run: `uv run pytest tests/integration/test_foundation.py::test_settings_load_from_env -v`
Expected: FAIL — `ModuleNotFoundError: verasig.config`.

- [ ] **Step 4: Minimal config**

```python
# src/verasig/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VERASIG_", env_file=".env", extra="ignore")
    database_url_override: str | None = None
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "verasig"
    db_user: str = "verasig"
    db_password: str = "verasig"
    telegram_api_id: int | None = None
    telegram_api_hash: str | None = None
    session_path: str = "/session/telegram.session"

    @property
    def database_url(self) -> str:
        return self.database_url_override or ...
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

- [ ] **Step 12: Verify health + commit**

Run: `docker compose up -d db && docker compose run --rm app health`
Expected: `OK: db connected`.
```bash
git add -A && git commit -m "feat: foundation skeleton (compose, postgres, config, cli health)"
```

---

## work item 1: Telegram session & login

- **Input:** `telegram_api_id`/`hash`/`phone` (env), interactive code/2FA (once).
- **Output:** persisted `StringSession` (bare UTF-8 string at `session_path`); non-interactive client for all other commands.
- **Decisive test (unit):** session-string round-trips (`save`→`load`); missing/empty session raises `SessionMissingError("run `login` first")`; absent creds raise `CredentialsMissingError`.
- **Contract:** `TelegramSource` Protocol (`domain/protocols.py`, `data-contracts.md` §9) — Protocol-only stub here; `backfill_batches`/`live_events` are implemented in work items 2/10. work item 1's own seam is the session store + guarded client factory in `telegram_session.py`.
- **Acceptance:** `docker compose run --rm -it app login` completes once; `app whoami` then prints the account non-interactively across restarts.
- **Note:** tests never authenticate against real Telegram — `login`/`whoami`'s live calls are verified outside automated tests; only load/persist/guard + the pure `format_account` formatter are unit-tested.

**Resolved gaps (grill, 2026-06-03):**
- **Seam (Q1):** ship `domain/protocols.py` (full async `TelegramSource` Protocol), `domain/telegram.py` (live event contracts), `foundation/telethon_source.py` (`TelethonSource` adapter), and `foundation/telegram_session.py` (session store + guards + client factory + login). The §9 `TelegramSource` reference is forward-looking — work item 1 stubs the Protocol, does not implement its methods.
- **Protocol types (Q2):** to type the stubbed Protocol, pull in **pure contracts only** — `domain/message.py` (`RawTelegramMessage` per §2 + `DeliveryMode` enum per §1) and `TelegramDeliveryEvent` (in `domain/telegram.py` per §9). NO ORM, NO migration, NO backfill logic (those stay in work item 2). `DeliveryMode` lives in `domain/message.py` (enum with its entity); foundation imports domain, never the reverse.
- **login UX (Q3):** add `telegram_phone: str | None` to `Settings` + `.env(.example)`; `client.start(phone=settings.telegram_phone)` prompts for code + 2FA interactively. api_id/hash stay env-sourced.
- **Creds absent (Q4):** `make_client` raises `CredentialsMissingError("set VERASIG_TELEGRAM_API_ID and VERASIG_TELEGRAM_API_HASH")` (creds-check **before** session-load) so work item-0 `health` keeps working with creds Optional.
- **whoami (Q5):** one line incl. phone — `logged in as @handle · First Last · id=N · +phone`; missing username/last_name omitted gracefully. Pure `format_account(user) -> str` is table-tested with a stub; live `get_me()` is verified outside automated tests.

**Files:**
- Create: `src/verasig/domain/__init__.py`, `src/verasig/domain/message.py`, `src/verasig/domain/telegram.py`, `src/verasig/domain/protocols.py`, `src/verasig/foundation/telethon_source.py`, `src/verasig/foundation/telegram_session.py`
- Edit: `src/verasig/config.py` (+`telegram_phone`), `src/verasig/cli.py` (+`login`, +`whoami`), `.env`, `.env.example`
- Test: `tests/unit/test_domain_message.py`, `tests/unit/test_telegram_source.py`, `tests/unit/test_telegram_session.py`

---

## work item 2: History backfill → RawTelegramMessage (resumable + chunked)

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
  - Test fixtures: synthetic anonymized `fixtures/messages/*.jsonl` driven by `FakeSource`; real `TelethonSource` (resolve + `iter_messages(reverse=True, min_id=cursor)` + flood-wait backoff) is verified outside automated tests.

**Files:**
- Create: `src/verasig/domain/channel.py`, `src/verasig/storage/__init__.py`, `src/verasig/storage/models.py`, `src/verasig/storage/repositories.py`, `src/verasig/services/__init__.py`, `src/verasig/services/ingestion/__init__.py`, `src/verasig/services/ingestion/backfill.py`, `migrations/versions/0002_*.py`
- Edit: `src/verasig/config.py` (+`backfill_batch_size`), `src/verasig/foundation/telethon_source.py` (+`resolve_channel`, +`TelethonSource`), `src/verasig/cli.py` (+`migrate`, +`backfill`, +`stats`)
- Note: added a `migrate` subcommand (`alembic upgrade head`) so the deployed container can create the work item-2 tables before `backfill` (`docker compose run --rm app migrate`).
- Test: `tests/fixtures/messages/*.jsonl`, `tests/integration/test_backfill.py`, `tests/unit/test_fake_source.py` (+ Protocol conformance)

---

## work item 3: Candidate seed filter + unified distillation → FilterRule + ParserRule + golden corpus

> Merges candidate filtering and the distillation loop ([ADR 0005](../../adr/0005-distilled-filter-and-advisory-gate.md)). The candidate filter is **advisory** (priority/triage, not a hard gate); its rules are **distilled** from the same `GoldenLabel` pass that produces parser rules.

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
- **Note:** real external-LLM distillation sends only operator-selected examples to the real LLM. The seed filter + rule application are pure/offline and fixture-testable. A local `FilterGemma`/`ParserGemma` is outside current scope until a later product version (ADR 0005).

**Resolved gaps (grill, 2026-06-04) — work items 3 + 4 execute as one pass:**

- **Scope:** build seed filter + distillation (including Streamlit workbench + real `ClaudeCliDistiller`) **and** all of work item 4 (deterministic extraction). Real-LLM interactions use operator-selected examples only; tests stay offline (FakeDistiller, canned `cli/distill_*.txt`, FakeExchange).
- **3/4 boundary:** work item 4 absorbed wholesale — `ExtractedSignal`/`UnrecognizedSignal` + `Side`/`EntryType`/`SignalEventType`, `deterministic_parser.parse`, `ExtractService` (one-of; required symbol+side; `fallback=None` until work item 5), precision ≥ 0.95 harness.
- **Exchange seam:** `domain/protocols.py` owns the `Exchange` Protocol (`is_listed`/`base_symbols`); `foundation/static_exchange.py` owns the bundled `StaticExchange` seed; `FakeExchange` lives in tests. Real `BybitExchange(httpx)` remains outside current scope until work item 9.
- **Distiller output:** LLM emits JSON `{filter_rule, parser_rules}` (pattern content only); shared `parse_distiller_output` tolerantly extracts (bare or ```json-fenced) + Pydantic-validates; the adapter stamps `rule_id`/`version`/`created_at`/`distilled_from_label_ids` (provenance never hallucinated).
- **MatchReason:** frozen 3-value enum kept — `DIRECTIONAL_KEYWORD` (long/short/buy/sell + RU), `SYMBOL_TOKEN` (Exchange-listed), `PRICE_SHAPED` (subsumes trade-structure keywords/emoji + price patterns).
- **Persistence:** migration `0003` adds all 7 tables — `raw_signal_event`, `extracted_signal`, `unrecognized_signal`, `filter_rule`, `parser_rule`, `golden_label`, `filter_drift_warning`; list/map fields + `GoldenLabel.expected` as JSONB; conftest TRUNCATE extended.
- **Fixtures:** synthetic anonymized `tests/fixtures/{messages,labels}/pilot.jsonl` (~50 msgs, EN+RU; signals / partials / chatter + ≥1 planted filter-miss). Oracle for filter-recall ≥ 0.95 (denominator = `GoldenLabel.is_signal`) + parser-precision ≥ 0.95 (`expected`).
- **UI:** full 4-view workbench (Candidates | Unflagged | ⚠ Drift | 🎲 Audit) — pure presenter in `services/distillation/workbench.py`, thin `ui/workbench.py`, `AppTest` smoke.
- **CLI:** `candidates` (derive) · `workbench` (Streamlit) · `extract` (candidates → signal/unrecognized) · `sweep` (advisory parse-all → late-materialize `PARSER_BACKFILL` + `FilterDriftWarning`). `candidates`/`extract`/`sweep` are offline; only the workbench Distil-click reaches the real LLM.
- **Decided inline (doc/precedent):** enums co-located with their entity (`DeliveryMode` precedent); `uuid4` / `datetime.now(tz=utc)` defaults (tests pass explicit instants); `candidate_text` = verbatim text; media-only/blank → non-candidate; late-materialization idempotent on `(channel_id, message_id)`.

**Files (this pass):**
- `domain/`: `event.py` `signal.py` `filter_rule.py` `parser_rule.py` `label.py` `drift.py`
- `foundation/static_exchange.py`
- `services/ingestion/candidate_filter.py` (seed + FilterRule apply + derivation + advisory sweep), `services/extraction/{deterministic_parser.py, extract_service.py}`, `services/distillation/{rule_distiller.py, workbench.py}`
- `storage/models.py` (+7 rows), `storage/repositories.py`, `migrations/versions/0003_*.py`
- `ui/app.py` `ui/workbench.py`; `cli.py` (+`candidates`/`workbench`/`extract`/`sweep`), `config.py` (+`distiller_command`)
- `tests/unit/*`, `tests/integration/*`, `tests/fixtures/{messages,labels,cli}/*`, `tests/fakes.py` (+`FakeExchange`, +`FakeDistiller`)

---

## work item 4: Deterministic extraction → ExtractedSignal | UnrecognizedSignal

> **Absorbed into the work item 3 pass (grill 2026-06-04).** The contracts + parser + `ExtractService` + precision harness below are built together with work item 3; the steps remain as the TDD micro-pattern. work item 5 adds LLM fallback.

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
        # fallback wired in work item 5
        return ExtractOutcome(unrecognized=_unrecognized(event, "no_match"), drift_warnings=[])
```

- [ ] **Step 8: Verify pass; precision harness; commit**

Run: `uv run pytest tests/unit -v` → PASS.
Add `tests/integration/test_precision_recall.py` using `fixtures/labels` → assert `precision >= 0.95`, report recall.
```bash
git add -A && git commit -m "feat: deterministic extraction with required symbol+side and one-of outcome"
```

---

## work item 5: LLM fallback + ParserDriftWarning

- **Input:** `RawSignalEvent` that missed deterministic parsing.
- **Output:** `ExtractedSignal` (method=`LLM_FALLBACK`) or `UnrecognizedSignal`; **one `ParserDriftWarning` per fallback success**.
- **Contracts:** `LlmExtractor` Protocol; adapter `ClaudeCliExtractor` (subprocess parse; Codex via `command="codex"` — a named subclass is trivial later, YAGNI) + `FakeExtractor`.
- **Decisive tests (unit):** fallback called **only** on deterministic miss; success ⇒ exactly one drift warning (100% coverage metric); CLI-output parser tested against `fixtures/cli/extract_*.txt`; **real CLI never invoked**.
- **Acceptance:** replay corpus → unmatched events route to fallback → drift warnings 1:1 with fallback successes; real content reaches the real LLM only through the configured extractor command.

**Resolved gaps (grill, 2026-06-04) — see [ADR 0006](../../adr/0006-extraction-outcomes-shape-and-lifecycle.md):**

- **Shape/linkage split (root fix of the §3-vs-§9 collision):** new `TradeIntent` (provenance-free trade levels) + `ExtractedSignal(TradeIntent)` (linkage). Both extractors symmetric `text -> TradeIntent | None` (`parse(rule, candidate_text)`, `extract(candidate_text)`); `ExtractService._link(intent, event, method, rule_id)` is the single linkage site. Refactors the (absorbed) work item-4 deterministic parser + simplifies `evaluation.py` (drops its dummy event). The linkage assertion moves from the parser test to the service test.
- **LLM output = exactly `TradeIntent`** (one task; no self-grading, no lifecycle classification). Shared tolerant `find_json_object` (new `services/json_extract.py`, shared with `rule_distiller`); `parse_extractor_output(stdout) -> TradeIntent | None` returns `None` on unparseable/missing symbol+side (a fallback miss, not a crash — unlike the distiller which raises). Fixtures: `cli/extract_pilot.txt` (success) + `cli/extract_miss.txt` (→ None).
- **`parser_confidence` dropped** from the contract — redundant with `extraction_method`; work item 8 derives its parse-reliability component from the `extraction_method` distribution + unrecognized rate.
- **Fallback ON by default**, disableable: `Settings.extractor_fallback_enabled: bool = True` (+ `.env`) and a per-run `extract --no-llm` flag; `Settings.extractor_command: str = "claude"`. The off-switch is for offline/free runs. CLI seam `_make_fallback_extractor` is monkeypatched in tests (FakeExtractor) — **no test touches the real CLI**.
- **`ExtractService.extract(event)` wiring:** deterministic match → `_link(…, DETERMINISTIC, rule.rule_id)`, fallback not called; miss + no fallback → `UnrecognizedSignal(reason="no_match", attempted=[DETERMINISTIC])`; miss + fallback success → `_link(…, LLM_FALLBACK, None)` + one `ParserDriftWarning(deterministic_result="no_match", fallback_result="extracted", fallback_signal_id=…)`; miss + fallback fail (None) → `UnrecognizedSignal(reason="fallback_failed", attempted=[DETERMINISTIC, LLM_FALLBACK])`.
- **Persistence — recomputable projection (ADR 0006):** `record_outcome(session, outcome)` (drift travels inside `ExtractOutcome.drift_warnings`, not a separate arg) upserts the winning outcome `ON CONFLICT(event_id) DO UPDATE`, deletes the losing sibling, and upserts/clears the `parser_drift_warning`. `UNIQUE(event_id)` on `extracted_signal`, `unrecognized_signal`, `parser_drift_warning`. Re-extract is `+0` and transitions `unrecognized -> extracted` cleanly. Raw tables stay append-only.
- **Adapter:** one `ClaudeCliExtractor(command=…, runner=…)` mirroring `ClaudeCliDistiller` (Codex via `command="codex"`; a named subclass is trivial later — YAGNI). `FakeExtractor(returns=…, calls)` in `tests/fakes.py`.
- **Migrations:** edit `0003` to drop the now-dead `parser_confidence` column; add `0004` (`parser_drift_warning` table + `UNIQUE(event_id)` on `extracted_signal`/`unrecognized_signal`). conftest TRUNCATE list extended.
- **Out of scope:** the workbench ⚠ Drift view stays filter-drift only (no parser-drift UI here).

**Files:**
- `domain/signal.py` (+`TradeIntent`, `ExtractedSignal(TradeIntent)`, −`parser_confidence`), `domain/drift.py` (+`ParserDriftWarning`)
- `services/extraction/llm_fallback.py` (new: `parse_extractor_output` + `ClaudeCliExtractor`; `LlmExtractor` Protocol lives in `domain/protocols.py`) + `services/json_extract.py` (new: shared `find_json_object`), `services/extraction/deterministic_parser.py` (→ `TradeIntent`), `services/extraction/extract_service.py` (wire fallback + `_link` + drift), `services/distillation/evaluation.py` (→ `TradeIntent`, drop dummy event), `services/ingestion/candidate_derivation.py` (`parse(rule, text)`)
- `storage/models.py` (−`parser_confidence`, +`ParserDriftWarningRow`, +`UNIQUE`), `storage/repositories.py` (+`record_outcome`, +`read_parser_drift_warnings`), `migrations/versions/0003_*.py` (edit), `migrations/versions/0004_*.py` (new)
- `config.py` (+`extractor_fallback_enabled`, +`extractor_command`), `cli.py` (`extract --no-llm` + `_make_fallback_extractor` + `record_outcome` + drift count in output)
- `tests/fakes.py` (+`FakeExtractor`), `tests/fixtures/cli/extract_pilot.txt` + `extract_miss.txt`, unit + integration tests; `tests/conftest.py` (TRUNCATE +`parser_drift_warning`)

---

## work item 6: Signal lifecycle fold

- **Input:** a channel's `ExtractedSignal` entries + their `RawTelegramMessage`s (`reply_to_message_id` for links, `posted_at` for the true timeline).
- **Output:** in-memory `FoldedSignal` (entry + applied modifications + optional close) — recomputable, never stored.
- **Decisive tests (unit, pure):** entry then "move SL to BE" reply ⇒ effective SL updated at modification time (= effective entry); average-in ⇒ effective size + size-weighted entry (priced legs); market-price add ⇒ `leg_price`/`effective_entry` unresolved until market-data simulation; reduce lowers size without moving entry; CLOSE (keyword or `size → 0`) terminates with `closed_at`; **standalone complete signal stays single-step (no phantom lifecycle)**; out-of-order updates handled (sort by `posted_at`); different-symbol reply starts its own root.
- **Acceptance:** a crafted entry→modify→close thread folds to the expected effective-parameter timeline; `verasig lifecycle <ref>` prints it.

**Resolved gaps (grill, 2026-06-05) — see [ADR 0007](../../adr/0007-lifecycle-fold-pure-recomputable.md):**

- **Placement:** new pure `services/lifecycle/` fold — `fold(entry_signals, messages, version) -> list[FoldedSignal]`. Extractors stay pure `text -> TradeIntent` (NEW_ENTRY only); no DB writes, no migration. Lifecycle classification happens at fold-time, not in extraction.
- **Modifications are not signals:** a reply ("move SL to BE") carries no `side`, so it is never an `ExtractedSignal`; it is recognized from the `reply_to` chain. `event_type`/`references_message_id` live in the folded view, never written back to `extracted_signal`.
- **Storage = recompute:** `FoldedSignal` is in-memory + `fold_version`-stamped; auditable by recompute over append-only messages + recomputable signals (the fold adds no new information; its sources never vanish — unlike `DeletedSignalEvidence`). `SimOutcome.folded_signal_id := root_signal_id`.
- **Contract growth ([data-contracts §5](data-contracts.md)):** `FoldStep` += `source_message_id`, `event_type`, `effective_size`, `effective_entry?`, `leg_size?`, `leg_price?`; `source_signal_id` pinned to `root_signal_id`; `FoldedSignal` += `fold_version`.
- **Modify semantics:** SL (incl. BE := current `effective_entry`), TP (stated set replaces), average-in (+leg, stated multiplier, price or market), reduce (size↓, entry unchanged), full close. Effective state carries forward cumulatively. Position size = equal-weight legs × stated multipliers (no `size` field on `TradeIntent`). Market legs (`leg_price=None`) → `effective_entry=None`, resolved by work item 9.
- **Threading:** transitive `reply_to` walk to the nearest entry root; symbol-guarded membership (same/no symbol joins; different symbol starts its own root); CLOSE by full-close keyword (EN+RU) or `effective_size → 0`.
- **Surface:** read-only `verasig lifecycle <ref>` (reads DB, folds, prints; no writes, offline). Out of scope: scoring/sim/deletion/live (work items 7–10), market-price fills (work item 9).

**Files (this pass):**
- `domain/lifecycle.py` (`FoldStep`, `FoldedSignal`, `FOLD_VERSION`)
- `services/lifecycle/__init__.py`, `services/lifecycle/fold.py` (pure fold + thread resolution), `services/lifecycle/patch.py` (pure lifecycle patch classifier: SL/BE/TP/add/reduce/close + multipliers + price, EN+RU)
- `cli.py` (+`lifecycle`)
- `tests/unit/test_lifecycle_patch.py`, `tests/unit/test_lifecycle_fold.py` (crafted threads), `tests/integration/test_cli_lifecycle.py`

---

## work item 7: Deletion evidence

- **Input:** the channel's **stored** `RawTelegramMessage`s + a **fresh live message-id re-fetch** (`TelegramSource.live_message_ids`); `LIVE_EVENT` deletions arrive in work item 10.
- **Output:** persisted `DeletedSignalEvidence` — `CONFIRMED`/`SNAPSHOT_DIFF` (`stored − live`, content retained) + `SUSPECTED`/`ID_GAP` (`range − stored − live`, absent from both, no content).
- **Decisive tests (unit, pure):** present-then-absent ⇒ CONFIRMED with original text + correct `was_signal_candidate`; id-gap absent from both ⇒ SUSPECTED (no content); contiguous / all-still-live ⇒ nothing.
- **Acceptance:** delete a captured message, then `rescan` ⇒ CONFIRMED evidence retaining the original content; `deletions <ref>` prints it.

**Resolved gaps (grill, 2026-06-05) — see [ADR 0008](../../adr/0008-deletion-evidence-durable-projection.md):**

- **Diff model (Q1):** raw capture is insert-only, so detection is **stored set vs a fresh live re-fetch** (full history), never two stored backfills. `CONFIRMED = stored − live` (original text + `first_seen_at` retained from the stored row).
- **SUSPECTED (Q2):** `range − stored − live` over `range = [min..max]` of `stored ∪ live` — a slot **absent from both** snapshots. The live set rescues still-present content/service ids, so the work item-8 deletion rate is not flooded; contiguous/all-live ⇒ nothing.
- **Seam (Q3):** new `async live_message_ids(channel_id) -> set[int]` on `TelegramSource` (amends §9); `TelethonSource` projects ids from `iter_messages`; `FakeSource` returns a canned set (offline tests).
- **What is evidence (Q4):** **store all** confirmed deletions (chatter incl., for audit); **score + display only** `was_signal_candidate` ones (chatter affects nothing — enforced at score/display, detector stays complete); `SUSPECTED` shown per channel.
- **Idempotency (Q5):** durable projection (NOT recomputable — the live snapshot is ephemeral). One row per `(channel_id, message_id)` (`UNIQUE`); rescan `+0`; `SUSPECTED→CONFIRMED` upgrades only (guarded); first-noticed `detected_at` preserved.
- **Surface (Q6):** gated `rescan <ref>` (re-fetch + detect + store; aborts on empty/failed re-fetch) + offline `deletions <ref>` (read stored: signal-confirmed with text + per-channel suspected count). Mirrors `backfill` vs `stats`/`lifecycle`.
- **Clock seam:** pure `detect_deletions(...)` takes `detected_at` (deterministic tests); the model defaults `_now()`.
- **Decided inline (convention):** `domain/deletion.py` (StrEnums co-located, `uuid4`/`_now` defaults); `services/deletion/{diff,rescan}.py` (pure core + gated orchestration, mirroring `lifecycle/` + `backfill.py`); no test touches real Telegram.

**Files (this pass):**
- `domain/deletion.py` (`DeletionConfidence`, `DeletionMethod`, `DeletedSignalEvidence`)
- `services/deletion/__init__.py`, `services/deletion/diff.py` (pure `detect_deletions`), `services/deletion/rescan.py` (gated re-fetch → detect → persist)
- `domain/protocols.py` (+`live_message_ids` on `TelegramSource`), `foundation/telethon_source.py` (+`TelethonSource`)
- `storage/models.py` (+`DeletedSignalEvidenceRow`), `storage/repositories.py` (+`upsert_deletion_evidence`, +`read_deletion_evidence`), `migrations/versions/0005_deletion_evidence.py`
- `cli.py` (+`rescan`, +`deletions`, +formatters)
- `tests/fakes.py` (+`FakeSource.live_message_ids`), `tests/unit/test_deletion_diff.py`, `tests/integration/test_deletion_evidence.py`, `tests/integration/test_cli_deletions.py`, `tests/conftest.py` (TRUNCATE +`deleted_signal_evidence`)

---

## work item 8: Hygiene scorecard + ProviderScore/Explanation

- **Input:** events, signals, drift, deletions, active-user proxy, and optional simulation components.
- **Output:** `ProviderScore` + `ProviderScoreExplanation`.
- **Decisive tests (unit, pure):** each metric fn (frequency, completeness, parser-confidence, deletion rate, proxy); composite = Σ(normalized×weight); **every component has `evidence_refs`**; re-weighting changes the score deterministically; "0 simulable signals" noted.
- **Acceptance:** scorecard renders per provider; 100% of components trace to stored evidence.

**Resolved gaps (grill, 2026-06-06) — see [ADR 0009](../../adr/0009-provider-score-recomputable-scorecard.md):**

- **Storage class:** in-memory recompute, NEVER stored (ADR 0007 fold precedent, not ADR 0006/0008) — no migration, no table, no `conftest` change. `computed_at` + `weights_version` reproduce a past score; `computed_at` injected for deterministic tests, model defaults `_now()`.
- **Composite:** `score = Σ(normalized × weight)` plain sum (frozen §7 — no renormalization), over only evidence-backed components. `domain/score.py` holds `ScoreWeights(version, by_component)` + `DEFAULT_WEIGHTS` (v0); injected into the builder (re-weight = pass another `ScoreWeights`, deterministic).
- **Components:** *scored* — `sim_expectancy` 0.30 + `drawdown` 0.20 (excluded + noted when simulation evidence is absent), `deletion_behaviour` 0.20, `completeness` 0.10, `parser_confidence` 0.10, `evidence_availability` 0.10; *context @ weight 0* — `signal_frequency`, `active_user_proxy`. Without simulation evidence, active weights sum 0.50 → score honestly partial. No fabrication: absent-simulation / empty-denominator (0/0) components are excluded + noted, never scored 0 or 0.5.
- **Per-component math:** deletion = 1−(CONFIRMED∧signal ÷ `RawSignalEvent` count); completeness = mean(present-{entry,stop,≥1 TP} ÷ 3, MARKET counts as entry); parser_confidence = DETERMINISTIC ÷ total candidates; evidence_availability = captured ÷ (captured + `ID_GAP`) — emitted only when a rescan provably ran (≥1 row `method ∈ {SNAPSHOT_DIFF, ID_GAP}`; `LIVE_EVENT` excluded), else excluded + noted (a never-rescanned channel never reads 1.0); frequency = candidates ÷ window-days; proxy raw=`subscriber_count`, normalized=mean(saturate{subs, median views, median forwards}) over available, name `active_user_proxy` (never a quality claim).
- **evidence_refs:** typed-prefix grammar (`channel:` / `message:<ch>/<msg>` / `event:` / `signal:` / `unrecognized:` / `deletion:` / `parser_drift:` / `filter_drift:`), naming every row used to **measure** the value (numerator + denominator) so a measured 0.0 still traces; bulk message-corpus denominators anchor on `channel:<id>` (deterministic `count_messages`), not thousands of `message:` refs.
- **Placement:** pure `services/scoring/hygiene.py` (un-weighted metric measurements: raw / normalized / evidence_refs / notes, or excluded+note) + `services/scoring/scorecard.py` (apply `ScoreWeights` → `ScoreComponent.contribution = normalized×weight`, sum `score`, stamp `computed_at`/`weights_version`, gather `notes` → build `ProviderScore` + `ProviderScoreExplanation`). Repo reads stay in the CLI, mirroring `_fold_channel`. work item 9 adds `simulator.py` + `policies.py` alongside.
- **Surface:** offline `verasig score <ref>` (read repos → pure builder → `format_score` + `format_explanation`); unknown channel exits 1. Mirrors `stats`/`lifecycle`/`deletions`. No persistence and no Streamlit scorecard here.

**Files (this pass):**
- `domain/score.py` (`ScoreComponent`, `ProviderScore`, `ProviderScoreExplanation`, `ScoreWeights`, `DEFAULT_WEIGHTS`, `WEIGHTS_VERSION="v0"`, `_now`)
- `services/scoring/__init__.py`, `services/scoring/hygiene.py` (pure per-component measurements), `services/scoring/scorecard.py` (weighted assembly → `ProviderScore` + `ProviderScoreExplanation`)
- `cli.py` (+`score`, +`format_score`, +`format_explanation`, +`_score_channel`)
- `tests/unit/test_hygiene.py` (each metric fn, table-driven; exclude+note paths), `tests/unit/test_scorecard.py` (composite = Σ(normalized×weight); re-weight changes score; absent-simulation note; partial score), `tests/integration/test_score_traceability.py` (seed rows → score → 100% of `evidence_refs` resolve to stored rows incl. `channel:` aggregate), `tests/integration/test_cli_score.py` (CliRunner: scorecard + explanation print; unknown channel exits 1)
- No migration; no `tests/conftest.py` change.

---

## work item 9: Simulation

- **Input:** `FoldedSignal`s + Bybit klines + `ExecutionPolicy`.
- **Output:** `SimOutcome` per signal (R-multiple/MTM, MFE/MAE) → fills sim components of `ProviderScore`.
- **Contracts:** `MarketData` + `ExecutionPolicy` Protocols in `domain/protocols.py`; adapters/policies: `BybitKlineClient` httpx + Fake, `ProviderStatedPolicy`.
- **Decisive tests (unit, canned klines):** market fill=next-candle open; limit never reached ⇒ `UNFILLED`; **same-candle stop+tp ⇒ stop-first (-1R)**; MFE/MAE; policy **injectable** (dummy `CustomRiskPolicy` proves the seam).
- **Acceptance:** known signal + known klines ⇒ expected conservative R; scorecard shows simulated expectancy + drawdown with full explanation.

**Resolved gap (2026-06-06):**

- **Operator path:** `verasig score <ref>` remains offline and partial by default. `verasig score <ref> --simulate --until <iso-datetime>` fetches public Bybit klines through `MarketData`, simulates folded signals in memory, and includes `sim_expectancy` + `drawdown` in the recomputed scorecard. Tests monkeypatch the market-data seam and never call the real Bybit network.

---

## work item 10: Live listener daemon

- **Input:** running Telethon session + pilot `channel_ids`.
- **Output:** continuous `RawTelegramMessage` capture via **hybrid push+poll** (passive `events.NewMessage` + bounded short-poll closing `pts` gaps, deduped on `(channel_id, message_id)`) + real-time `DeletedSignalEvidence` (LIVE_EVENT, precise timing). Capture is **queue-first**: persist the row immediately, parse/score async — never block the update loop.
- **Contract:** `TelegramSource.live_events(channel_ids)` → `TelegramLiveEvent` (`TelegramDeliveryEvent` for message `mode`/`captured_at`/`pts`; `TelegramDeletionEvent` for live deletes); see [ADR 0004](../../adr/0004-hybrid-push-poll-live-ingestion.md).
- **Decisive tests (unit/integration, fake event stream):**
  - push event ⇒ row tagged `mode=PUSH`; delayed/absent push then poll ⇒ same message arrives **once** (`mode=POLL`/`CATCH_UP`), deduped vs push and vs backfill.
  - delete event ⇒ CONFIRMED evidence with timestamp.
  - **latency:** with a fake clock, median `captured_at − posted_at` ≤ the configured poll interval.
- **Acceptance:** run `app live <channels>`, post + delete a test message ⇒ captured (within the poll interval) then CONFIRMED-deleted with timestamps.
- **Live verification notes:** use a dedicated account/session and migrated DB; run `uv run verasig live <channel>`; post a unique text message; verify `verasig stats <channel>` count increments within the poll interval; delete it; verify a `deleted_signal_evidence` row with `method=LIVE_EVENT`, `confidence=CONFIRMED`, `original_text`, `first_seen_at`, and `detected_at`. If verifying through `verasig deletions`, materialize the message as a `RawSignalEvent` before deletion so the reader does not hide chatter.

---

## Execution Order

1. Build pure, fixture-driven logic first: foundation, seed filtering, deterministic extraction, lifecycle folding, deletion evidence, scoring, and simulation.
2. Enable real Telegram and real LLM paths only with configured credentials/session; automated tests stay offline.
3. Process Telegram in bounded batches with resumable cursors; never load full history into RAM.

## Self-review notes

- **Spec coverage:** every entity in `data-contracts.md` maps to a work item (channel/message→2; event + FilterRule/ParserRule + GoldenLabel + FilterDriftWarning→3; signal/unrecognized→4; parser-drift→5; folded→6; deletion→7; score/explanation→8; sim→9; live→10). ✓
- **Type consistency:** `ExtractedSignal` fields, `Side`/`EntryType`/`MatchReason`/`MaterializationPath` enums, `ExtractOutcome`, `FilterRule`/`ParserRule`, and Protocol names match across work items and `data-contracts.md`. ✓
- **No placeholders:** work items 0 and 4 carry full code; remaining work items carry frozen contracts + decisive tests, expanded JIT at execution per the chosen execution skill. ✓
