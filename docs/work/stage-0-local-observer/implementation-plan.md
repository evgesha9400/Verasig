# Stage 0 — Local Observer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove Verasig can score Telegram signal-provider quality from captured messages, fully local (docker compose), observe-only, no execution.

**Architecture:** One uv-built Python image (Typer CLI subcommands + Streamlit UI) over a Postgres container. `domain/` pure contracts ← `services/` logic ← `storage/`+`foundation/` IO; UI/CLI are thin adapters. Every external dependency sits behind a Protocol so tests run offline.

**Tech Stack:** Python 3.12, uv, Telethon, Postgres 16, SQLAlchemy 2.0 + Alembic, Pydantic v2, Typer, httpx, Streamlit, pytest (+ testcontainers), ruff. LLM fallback = Claude/Codex CLI via subprocess.

---

## How to read this plan

- Slices are **vertical and dependency-ordered**: each ends green, committed, and demonstrable.
- Slice 0 and Slice 5 are fully fleshed to TDD micro-steps as the pattern; remaining slices give the frozen contract (input/output/test/acceptance + the decisive test) and are expanded just-in-time at execution per `subagent-driven-development`.
- Contracts referenced here are frozen in `data-contracts.md`; metrics in `test-plan.md`.
- **Commit after every passing step** (conventional commits). **Never skip a test.**

---

## Dependency graph

```
0 Foundation
└─1 Session/login
  └─2 Backfill (RawTelegramMessage)
    └─3 Candidate filter (RawSignalEvent)
      └─4 Distillation loop (ParserRule + golden corpus)   ── needs UI + CLI distiller
        └─5 Deterministic extract (ExtractedSignal|Unrecognized)
          ├─6 LLM fallback + drift
          ├─7 Lifecycle fold
          └─8 Deletion evidence (snapshot-diff + id-gap)
            └─9 Hygiene scorecard + ProviderScore/Explanation
              └─10 Simulation (Bybit klines, conservative)   ← FINAL scoring slice
                └─11 Live listener daemon                     ← FINAL slice overall
```

---

## Slice 0: Foundation & skeleton

**Outcome:** `docker compose up` brings up Postgres + app; `app health` connects to the DB. pytest + ruff wired.

**Files:**
- Create: `pyproject.toml`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `.gitignore`, `alembic.ini`
- Create: `src/verasig/config.py`, `src/verasig/foundation/db.py`, `src/verasig/cli.py`
- Test: `tests/conftest.py`, `tests/integration/test_foundation.py`

- [ ] **Step 1: Init uv project + dev deps**

```bash
uv init --package --name verasig .
uv add sqlalchemy alembic "pydantic>=2" pydantic-settings typer httpx telethon streamlit
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
    database_url: str = "postgresql://verasig:verasig@db:5432/verasig"
    telegram_api_id: int | None = None
    telegram_api_hash: str | None = None
    session_path: str = "/secrets/telegram.session"
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

- **Input:** `telegram_api_id`/`hash`/phone (env), interactive code/2FA (once).
- **Output:** persisted `StringSession` in the mounted volume; non-interactive client for all other commands.
- **Decisive test (unit):** session-string round-trips; missing session raises a clear `SessionMissingError("run `login` first")`.
- **Contract:** `TelegramSource` Protocol (`data-contracts.md` §9).
- **Acceptance:** `docker compose run --rm -it app login` completes once; `app whoami` then prints the account non-interactively across restarts.
- **Note:** tests never authenticate against real Telegram — the `login` flow is exercised manually; logic (load/persist/guard) is unit-tested with a fake string.

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
- **Acceptance:** backfill a real (throwaway-account) channel → row count == accessible count; mid-run kill + restart resumes with no refetch and no dupes; `app stats <channel>` prints capture count + cursor.

---

## Slice 3: Candidate filter → RawSignalEvent

- **Input:** `RawTelegramMessage`.
- **Output:** `RawSignalEvent` for candidates only (+ `matched_reason`).
- **Decisive tests (unit, pure, table-driven):** chatter → reject; directional-keyword/symbol/price-shaped → accept; `matched_reason` recorded. Recall-first (over-include).
- **Acceptance:** on the labeled corpus, candidate **recall ≥ 0.95** of human-labeled signals (false positives acceptable — extraction filters them).

---

## Slice 4: Distillation loop → ParserRule + golden corpus

- **Input:** a channel's `RawTelegramMessage` corpus.
- **Output:** `ParserRule`s + `GoldenLabel`s (the golden corpus).
- **Contracts:** `RuleDistiller` Protocol; `ParserRule`, `GoldenLabel` (`data-contracts.md`).
- **Decisive tests:**
  - unit: `FakeDistiller(labels) → ParserRule`; rule-application (`apply(rule, text)→fields|None`) is pure and table-driven against fixtures.
  - integration: labels + rules persist; **re-applying distilled rules reproduces the labels** at ≥ target precision.
  - smoke (optional): Streamlit `AppTest` drives highlight → distill → filter → iterate; cursor advances to earliest labeled message.
- **Acceptance:** operator labels a pilot channel via the UI; rules produced; residue shrinks each pass; operator stops when satisfied; golden corpus saved.

---

## Slice 5: Deterministic extraction → ExtractedSignal | UnrecognizedSignal

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
        # fallback wired in Slice 6
        return ExtractOutcome(unrecognized=_unrecognized(event, "no_match"), drift_warnings=[])
```

- [ ] **Step 8: Verify pass; precision harness; commit**

Run: `uv run pytest tests/unit -v` → PASS.
Add `tests/integration/test_precision_recall.py` using `fixtures/labels` → assert `precision >= 0.95`, report recall.
```bash
git add -A && git commit -m "feat: deterministic extraction with required symbol+side and one-of outcome"
```

---

## Slice 6: LLM fallback + ParserDriftWarning

- **Input:** `RawSignalEvent` that missed deterministic parsing.
- **Output:** `ExtractedSignal` (method=`LLM_FALLBACK`) or `UnrecognizedSignal`; **one `ParserDriftWarning` per fallback success**.
- **Contracts:** `LlmExtractor` Protocol; adapters `ClaudeCliExtractor`/`CodexCliExtractor` (subprocess parse) + `FakeExtractor`.
- **Decisive tests (unit):** fallback called **only** on deterministic miss; success ⇒ exactly one drift warning (100% coverage metric); CLI-output parser tested against `fixtures/cli/extract_*.txt`; **real CLI never invoked**.
- **Acceptance:** replay corpus → unmatched events route to fallback → drift warnings 1:1 with fallback successes; gated behind operator go-ahead (real content → real LLM; see Start verdict).

---

## Slice 7: Signal lifecycle fold

- **Input:** `ExtractedSignal`s + `reply_to` links, time-ordered.
- **Output:** `FoldedSignal` (entry + applied modifications + optional close).
- **Decisive tests (unit, pure):** entry then "move SL to BE" reply ⇒ effective SL updated at modification time; CLOSE terminates; **standalone complete signal stays single-step (no phantom lifecycle)**; out-of-order updates handled.
- **Acceptance:** a crafted entry→modify→close thread folds to the expected effective-parameter timeline.

---

## Slice 8: Deletion evidence

- **Input:** two backfill snapshots (live events later).
- **Output:** `DeletedSignalEvidence` — `CONFIRMED` (snapshot-diff, content retained) + `SUSPECTED` (id-gap).
- **Decisive tests (unit, pure):** present-then-absent ⇒ CONFIRMED with original text + `was_signal_candidate`; id-gap in sequence ⇒ SUSPECTED (no content); contiguous ids ⇒ nothing.
- **Acceptance:** delete a message between two re-scans ⇒ CONFIRMED evidence retaining the original content.

---

## Slice 9: Hygiene scorecard + ProviderScore/Explanation

- **Input:** events, signals, drift, deletions, active-user proxy (sim components null/pending).
- **Output:** `ProviderScore` + `ProviderScoreExplanation`.
- **Decisive tests (unit, pure):** each metric fn (frequency, completeness, parser-confidence, deletion rate, proxy); composite = Σ(normalized×weight); **every component has `evidence_refs`**; re-weighting changes the score deterministically; "0 simulable signals" noted.
- **Acceptance:** scorecard renders per provider; 100% of components trace to stored evidence.

---

## Slice 10: Simulation (FINAL scoring slice)

- **Input:** `FoldedSignal`s + Bybit klines + `ExecutionPolicy`.
- **Output:** `SimOutcome` per signal (R-multiple/MTM, MFE/MAE) → fills sim components of `ProviderScore`.
- **Contracts:** `MarketData` Protocol (`BybitKlineClient` httpx + Fake); `ExecutionPolicy` (`ProviderStatedPolicy`).
- **Decisive tests (unit, canned klines):** market fill=next-candle open; limit never reached ⇒ `UNFILLED`; **same-candle stop+tp ⇒ stop-first (-1R)**; MFE/MAE; policy **injectable** (dummy `CustomRiskPolicy` proves the seam).
- **Acceptance:** known signal + known klines ⇒ expected conservative R; scorecard shows simulated expectancy + drawdown with full explanation.

---

## Slice 11: Live listener daemon (FINAL slice overall)

- **Input:** running Telethon session.
- **Output:** continuous `RawTelegramMessage` capture + real-time `DeletedSignalEvidence` (LIVE_EVENT, precise timing).
- **Decisive tests (unit/integration, fake event stream):** new-message event ⇒ row; delete event ⇒ CONFIRMED evidence with timestamp; dedup vs backfill.
- **Acceptance:** run `app live <channel>`, post + delete a test message ⇒ captured then CONFIRMED-deleted with timestamps.

---

## Start verdict

**Start now — partially.** The plan and contracts are clear and frozen. Two preconditions and one gate:

1. **Precondition — git (CLAUDE.md mandates it):** `git init`, create `main` (+ `develop`), commit the docs, then branch `feature/stage-0-foundation`. The repo currently has no VCS.
2. **Start immediately (no external/legal exposure):** Slices **0, 3, 5, 7, 8, 9, 10** are pure-logic / fixture-driven — build them TDD against committed fixtures with **zero** Telegram, LLM, or network calls. This is the bulk of the engine and proves the thesis on recorded data.
3. **Reality slices — operator has given go-ahead (accepted risk).** Slices **1, 2, 4, 6, 11** touch a real Telegram account and/or send real channel content to an LLM. The operator **accepted the legal risk for Stage 0** on a **dedicated throwaway Telegram account** (Telegram content-licensing + AI-scraping terms remain unresolved; revisit before paid launch). Constraints: resumable + chunked (spec §4.1) — **no rescrape on restart**, process in batches, never load full history into RAM.

> Recommended first move: git init → Slice 0 → Slices 3/5/7/8 against fixtures, then bring real Telegram online (Slices 1→2→4) on the throwaway account.

## Self-review notes

- **Spec coverage:** every entity in `data-contracts.md` maps to a slice (channel/message→2, event→3, rule/label→4, signal/unrecognized→5, drift→6, folded→7, deletion→8, score/explanation→9, sim→10); live→11. ✓
- **Type consistency:** `ExtractedSignal` fields, `Side`/`EntryType` enums, `ExtractOutcome`, and Protocol names match across slices and `data-contracts.md`. ✓
- **No placeholders:** Slices 0 and 5 carry full code; later slices carry frozen contracts + decisive tests, expanded JIT at execution per the chosen execution skill. ✓
