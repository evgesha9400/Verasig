# Parser Overlay — Phase 1 (Foundation + Manage) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist a per-account "parser overlay" (custom coin aliases, direction tokens, reject phrases, per-template thresholds) in the backend and merge it into the deterministic Template-Mining parser at mine time, with a Manage panel to view/add/remove entries — so corrections durably recover misses and exclude noise across runs and feeds.

**Architecture:** New `parser_overlay` table (one JSON row per user) + `GET/PUT /parser-overlay`. The frontend page fetches the overlay and threads it (as an explicit `overlay` argument, default `{}`) through the pure domain pipeline: the two leaf detectors merge custom aliases/tokens; `applyAcceptedRules`/`compileRuleFromTemplate` merge reject phrases + threshold overrides. A Manage panel edits the overlay and re-mines. Phase 2 (guided per-row suggestions) builds on this.

**Tech Stack:** Backend — FastAPI, SQLAlchemy (Postgres/JSONB), Alembic, Pydantic (`CamelModel`), pytest. Frontend — React 18 + Vite (JSX, no TS), Vitest + @testing-library/react (no jest-dom), `@verasig/design-system`.

## Global Constraints

- No LLM, no ML, no external network in the parser — overlay is explicit deterministic data.
- Domain stays pure: `src/domain/template-mining/**` imports no react/router/DS/CSS (enforced by `src/static-guards.test.js`); the overlay is **passed in**, never fetched in the domain.
- Frontend tests use `getByText`/`queryByText`/`getByRole` + `toBeTruthy`/`toBeNull` (NO jest-dom).
- Backend repository functions call `session.flush()`; routes call `session.commit()`.
- Pydantic request/response models extend `CamelModel` (snake_case fields ⇄ camelCase JSON).
- Overlay JSON shape (camelCase keys, stored verbatim in `parser_overlay.config`):
  `{ "instrumentAliases": {alias: SYMBOL}, "directionTokens": {token: "BUY"|"SELL"}, "rejectPhrases": [string], "templateThresholds": {templateKey: number} }`
- Overlay is **account-level** (applies to all the user's feeds).
- Run on branch `feature/parser-first-template-mining`. Commit after each task. Do NOT stage the user's local `Makefile` change.

---

### Task 1: Backend — `parser_overlay` table + migration

**Files:**
- Modify: `apps/backend/src/verasig/storage/models.py` (add `ParserOverlayRow`)
- Create: `apps/backend/migrations/versions/0012_parser_overlay.py`
- Test: `apps/backend/tests/feeds/test_parser_overlay_repository.py` (created in Task 2; this task is verified by `alembic upgrade head`)

**Interfaces:**
- Produces: `ParserOverlayRow` ORM model — columns `user_id: UUID (PK, FK user_account.id CASCADE)`, `config: dict (JSONB)`, `created_at`, `updated_at`. Table `parser_overlay`.

- [ ] **Step 1: Add the ORM model.** Append to `apps/backend/src/verasig/storage/models.py` (uses the already-imported `Uuid`, `ForeignKey`, `JSONB`, `DateTime`, `Mapped`, `mapped_column`, `datetime`, `UUID`):

```python
class ParserOverlayRow(Base):
    __tablename__ = "parser_overlay"

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user_account.id", ondelete="CASCADE"), primary_key=True
    )
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
```

- [ ] **Step 2: Create the migration** `apps/backend/migrations/versions/0012_parser_overlay.py`:

```python
"""Per-account parser overlay (custom aliases, direction tokens, reject phrases,
template thresholds) merged into the deterministic Template-Mining parser.

Revision ID: 0012_parser_overlay
Revises: 0011_generic_source
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0012_parser_overlay"
down_revision = "0011_generic_source"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "parser_overlay",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("config", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id", name="parser_overlay_pkey"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.id"],
            name="fk_parser_overlay_user",
            ondelete="CASCADE",
        ),
    )


def downgrade() -> None:
    op.drop_table("parser_overlay")
```

> Note: the archived `lab` branch also has a `0012_*`; the lineages are separate and that branch is archived. If it is ever revived, one of the two `0012`s is renamed.

- [ ] **Step 3: Apply and verify the migration.**

Run: `cd apps/backend && uv run alembic upgrade head && uv run alembic current`
Expected: ends at `0012_parser_overlay (head)`, no errors.

- [ ] **Step 4: Commit.**

```bash
git add apps/backend/src/verasig/storage/models.py apps/backend/migrations/versions/0012_parser_overlay.py
git commit -m "feat(overlay): parser_overlay table + migration 0012"
```

---

### Task 2: Backend — overlay repository

**Files:**
- Create: `apps/backend/src/verasig/features/parser_overlay/__init__.py` (empty)
- Create: `apps/backend/src/verasig/features/parser_overlay/repository.py`
- Test: `apps/backend/tests/feeds/test_parser_overlay_repository.py`

**Interfaces:**
- Consumes: `ParserOverlayRow` (Task 1).
- Produces:
  - `read_overlay(session: Session, user_id: UUID) -> dict` — the stored config, or `{}` when none.
  - `upsert_overlay(session: Session, user_id: UUID, config: dict) -> None` — insert-or-replace the row's config; sets timestamps; `flush()` (no commit).

- [ ] **Step 1: Write the failing test** `apps/backend/tests/feeds/test_parser_overlay_repository.py`:

```python
from uuid import uuid4

from seed import insert_source

from verasig.domain.account import Plan, UserAccount
from verasig.features.accounts import repository as account_repository
from verasig.features.parser_overlay.repository import read_overlay, upsert_overlay
from datetime import datetime, timezone


def _account():
    return UserAccount(
        id=uuid4(),
        email="overlay@example.com",
        password_hash="hash",
        first_name="Ada",
        last_name="Lovelace",
        plan=Plan.OBSERVER,
        pending_email=None,
        cancel_at=None,
        created_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )


def test_read_overlay_defaults_to_empty(db_session):
    account = account_repository.insert_account(db_session, _account())
    assert read_overlay(db_session, account.id) == {}


def test_upsert_overlay_round_trips_and_replaces(db_session):
    account = account_repository.insert_account(db_session, _account())
    upsert_overlay(db_session, account.id, {"instrumentAliases": {"АПТ": "APTUSDT"}})
    db_session.commit()
    assert read_overlay(db_session, account.id) == {
        "instrumentAliases": {"АПТ": "APTUSDT"}
    }

    upsert_overlay(db_session, account.id, {"rejectPhrases": ["closed"]})
    db_session.commit()
    assert read_overlay(db_session, account.id) == {"rejectPhrases": ["closed"]}
```

- [ ] **Step 2: Run it; verify it fails.**

Run: `cd apps/backend && uv run pytest tests/feeds/test_parser_overlay_repository.py -q`
Expected: FAIL — `ModuleNotFoundError: ...features.parser_overlay.repository`.

- [ ] **Step 3: Create the package + repository.** `apps/backend/src/verasig/features/parser_overlay/__init__.py` is empty. `apps/backend/src/verasig/features/parser_overlay/repository.py`:

```python
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from verasig.storage.models import ParserOverlayRow


def read_overlay(session: Session, user_id: UUID) -> dict:
    row = session.get(ParserOverlayRow, user_id)
    return dict(row.config) if row else {}


def upsert_overlay(session: Session, user_id: UUID, config: dict) -> None:
    now = datetime.now(tz=UTC)
    statement = (
        pg_insert(ParserOverlayRow.__table__)
        .values(user_id=user_id, config=config, created_at=now, updated_at=now)
        .on_conflict_do_update(
            index_elements=["user_id"],
            set_={"config": config, "updated_at": now},
        )
    )
    session.execute(statement)
    session.flush()
```

- [ ] **Step 4: Run the test; verify it passes.**

Run: `cd apps/backend && uv run pytest tests/feeds/test_parser_overlay_repository.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit.**

```bash
git add apps/backend/src/verasig/features/parser_overlay/ apps/backend/tests/feeds/test_parser_overlay_repository.py
git commit -m "feat(overlay): per-account overlay repository (read/upsert)"
```

---

### Task 3: Backend — schema + routes + registration

**Files:**
- Create: `apps/backend/src/verasig/features/parser_overlay/schemas.py`
- Create: `apps/backend/src/verasig/features/parser_overlay/routes.py`
- Modify: `apps/backend/src/verasig/entrypoints/api.py` (import + add to `ALL_ROUTERS`)
- Test: `apps/backend/tests/api/test_parser_overlay.py`

**Interfaces:**
- Consumes: `read_overlay`, `upsert_overlay` (Task 2); `get_current_user` (returns `UserAccount` with `.id: UUID`).
- Produces: `GET /parser-overlay` → `{ "overlay": {...} }`; `PUT /parser-overlay` body `{ "overlay": {...} }` → echoes `{ "overlay": {...} }`. Per-account; another user cannot read/write it.

- [ ] **Step 1: Write the failing API test** `apps/backend/tests/api/test_parser_overlay.py` (mirrors `tests/api/test_labels.py` register/auth helpers):

```python
def _register(client, email="ada@example.com"):
    response = client.post(
        "/auth/register",
        json={
            "firstName": "Ada",
            "lastName": "Lovelace",
            "email": email,
            "password": "correct horse battery staple",
        },
    )
    assert response.status_code == 201
    return response.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_overlay_defaults_empty_then_round_trips(client):
    token = _register(client)

    initial = client.get("/parser-overlay", headers=_auth(token))
    assert initial.status_code == 200
    assert initial.json()["overlay"] == {
        "instrumentAliases": {},
        "directionTokens": {},
        "rejectPhrases": [],
        "templateThresholds": {},
    }

    saved = client.put(
        "/parser-overlay",
        headers=_auth(token),
        json={"overlay": {"instrumentAliases": {"АПТ": "APTUSDT"}}},
    )
    assert saved.status_code == 200
    assert saved.json()["overlay"]["instrumentAliases"] == {"АПТ": "APTUSDT"}

    reread = client.get("/parser-overlay", headers=_auth(token))
    assert reread.json()["overlay"]["instrumentAliases"] == {"АПТ": "APTUSDT"}


def test_overlay_is_per_account(client):
    owner = _register(client, "owner@example.com")
    other = _register(client, "other@example.com")
    client.put(
        "/parser-overlay",
        headers=_auth(owner),
        json={"overlay": {"rejectPhrases": ["closed"]}},
    )

    assert client.get("/parser-overlay", headers=_auth(other)).json()["overlay"][
        "rejectPhrases"
    ] == []


def test_overlay_requires_auth(client):
    assert client.get("/parser-overlay").status_code == 401
```

- [ ] **Step 2: Run it; verify it fails.**

Run: `cd apps/backend && uv run pytest tests/api/test_parser_overlay.py -q`
Expected: FAIL — 404 (route not registered).

- [ ] **Step 3: Create the schema** `apps/backend/src/verasig/features/parser_overlay/schemas.py`:

```python
from pydantic import Field

from verasig.foundation.http.schemas import CamelModel


class ParserOverlayData(CamelModel):
    instrument_aliases: dict[str, str] = Field(default_factory=dict)
    direction_tokens: dict[str, str] = Field(default_factory=dict)
    reject_phrases: list[str] = Field(default_factory=list)
    template_thresholds: dict[str, float] = Field(default_factory=dict)


class ParserOverlayBody(CamelModel):
    overlay: ParserOverlayData
```

- [ ] **Step 4: Create the routes** `apps/backend/src/verasig/features/parser_overlay/routes.py`:

```python
from fastapi import APIRouter, Depends, Request

from verasig.domain.account import UserAccount
from verasig.features.parser_overlay.repository import read_overlay, upsert_overlay
from verasig.features.parser_overlay.schemas import ParserOverlayBody, ParserOverlayData
from verasig.foundation.http.auth_dependencies import get_current_user

router = APIRouter(prefix="/parser-overlay")


@router.get("")
def get_overlay(
    request: Request, user: UserAccount = Depends(get_current_user)
) -> ParserOverlayBody:
    with request.app.state.session_factory() as session:
        config = read_overlay(session, user.id)
    return ParserOverlayBody(overlay=ParserOverlayData(**config))


@router.put("")
def put_overlay(
    request: Request,
    payload: ParserOverlayBody,
    user: UserAccount = Depends(get_current_user),
) -> ParserOverlayBody:
    config = payload.overlay.model_dump(by_alias=True)
    with request.app.state.session_factory() as session:
        upsert_overlay(session, user.id, config)
        session.commit()
    return ParserOverlayBody(overlay=ParserOverlayData(**config))
```

- [ ] **Step 5: Register the router** in `apps/backend/src/verasig/entrypoints/api.py`. Add the import beside the other feature imports:

```python
from verasig.features.parser_overlay import routes as parser_overlay_routes
```

Add to the `ALL_ROUTERS` tuple (after `feed_routes.router`):

```python
    parser_overlay_routes.router,
```

- [ ] **Step 6: Run the test; verify it passes.**

Run: `cd apps/backend && uv run pytest tests/api/test_parser_overlay.py -q`
Expected: PASS (3 tests).

- [ ] **Step 7: Commit.**

```bash
git add apps/backend/src/verasig/features/parser_overlay/schemas.py apps/backend/src/verasig/features/parser_overlay/routes.py apps/backend/src/verasig/entrypoints/api.py apps/backend/tests/api/test_parser_overlay.py
git commit -m "feat(overlay): GET/PUT /parser-overlay (per-account)"
```

---

### Task 4: Domain — overlay-aware leaf detectors

**Files:**
- Modify: `apps/frontend/web/src/domain/template-mining/instruments.js` (`detectInstruments(text, overlay)`)
- Modify: `apps/frontend/web/src/domain/template-mining/directions.js` (`detectDirections(text, overlay)`)
- Test: `apps/frontend/web/src/domain/template-mining/instruments.test.js`, `.../directions.test.js`

**Interfaces:**
- Produces:
  - `detectInstruments(text, overlay = {})` — merges `overlay.instrumentAliases` ({alias→SYMBOL}) at dictionary confidence (0.95).
  - `detectDirections(text, overlay = {})` — merges `overlay.directionTokens` ({token→"BUY"|"SELL"}) at **word** confidence (0.9) so a taught emoji is not penalized as "emoji-only".

- [ ] **Step 1: Write failing instrument test.** Append to `apps/frontend/web/src/domain/template-mining/instruments.test.js`:

```js
it('recognises a custom alias from the overlay', () => {
  const without = detectInstruments('АПТ long here')
  expect(without.some((h) => h.normalized === 'APTUSDT')).toBe(false)

  const overlay = { instrumentAliases: { 'АПТ': 'APTUSDT' } }
  const hits = detectInstruments('АПТ long here', overlay)
  expect(hits.some((h) => h.normalized === 'APTUSDT')).toBe(true)
})
```

- [ ] **Step 2: Write failing direction test.** Append to `apps/frontend/web/src/domain/template-mining/directions.test.js`:

```js
it('recognises a custom direction token at word strength', () => {
  expect(detectDirections('🚀 entry now')).toHaveLength(0)

  const overlay = { directionTokens: { '🚀': 'BUY' } }
  const hits = detectDirections('🚀 entry now', overlay)
  expect(hits[0].normalized).toBe('BUY')
  expect(hits[0].confidence).toBe(0.9)
})
```

(`🚀` is also a built-in BUY emoji at 0.4 — overlay must override to 0.9. Verify the assertion catches the confidence, since the test reads `hits[0]`. If both rules match, dedupe is by position; ensure the overlay rule is included and its hit present. The assertion below filters by confidence to be safe — replace the two `expect` lines with:)

```js
  const hits = detectDirections('🚀 entry now', overlay)
  expect(hits.some((h) => h.normalized === 'BUY' && h.confidence === 0.9)).toBe(true)
```

- [ ] **Step 3: Run both; verify they fail.**

Run: `cd apps/frontend/web && npx vitest run src/domain/template-mining/instruments.test.js src/domain/template-mining/directions.test.js`
Expected: the two new tests FAIL (overlay arg ignored).

- [ ] **Step 4: Implement instruments overlay merge.** In `instruments.js`, change `collectAliasHits` to accept rules, add an overlay-rules builder, and add the param:

```js
function collectAliasHits(text, hits, rules) {
  for (const rule of rules) {
    rule.matcher.lastIndex = 0
    let match
    while ((match = rule.matcher.exec(text)) !== null) {
      pushHit(
        hits,
        match.index,
        match.index + match[0].length,
        rule.normalized,
        match[0],
        DICTIONARY_CONFIDENCE
      )
    }
  }
}

// Overlay aliases (user-taught alias -> canonical symbol) join the built-in
// rules, longest-term first so specific aliases win the overlap dedupe.
function aliasRulesWith(overlay) {
  const aliases = overlay?.instrumentAliases
  if (!aliases || Object.keys(aliases).length === 0) return ALIAS_RULES
  const extra = Object.entries(aliases).map(([term, normalized]) => ({
    matcher: aliasMatcher(term),
    normalized
  }))
  return [...extra, ...ALIAS_RULES].sort(
    (a, b) => b.matcher.source.length - a.matcher.source.length
  )
}

export function detectInstruments(text, overlay = {}) {
  if (!text) return []
  const hits = []
  collectAliasHits(text, hits, aliasRulesWith(overlay))
  collectCoinLabelHits(text, hits)
  collectCryptoPairHits(text, hits)
  collectForexPairHits(text, hits)
  collectBareTickerHits(text, hits)
  return dedupeHits(hits).map((hit) => ({
    raw: hit.raw,
    normalized: hit.normalized,
    start: hit.start,
    end: hit.end,
    confidence: hit.confidence
  }))
}
```

- [ ] **Step 5: Implement directions overlay merge.** In `directions.js`, add an escaper + overlay rules + param:

```js
function escapeRegExp(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

// A taught token: letter-bounded when alphabetic (so "up" doesn't hit "upset"),
// raw when it's an emoji/symbol. Word strength, so it isn't treated as emoji-only.
function tokenMatcher(token) {
  const body = escapeRegExp(token)
  return /^[\p{L}]+$/u.test(token)
    ? new RegExp(`(?<!\\p{L})${body}(?!\\p{L})`, 'giu')
    : new RegExp(body, 'g')
}

function overlayDirectionRules(overlay) {
  const tokens = overlay?.directionTokens
  if (!tokens) return []
  return Object.entries(tokens).map(([token, normalized]) => ({
    matcher: tokenMatcher(token),
    normalized,
    confidence: WORD_CONFIDENCE
  }))
}

export function detectDirections(text, overlay = {}) {
  if (!text) return []
  const rules = [...RULES, ...overlayDirectionRules(overlay)]
  const hits = []
  for (const rule of rules) {
    rule.matcher.lastIndex = 0
    let match
    while ((match = rule.matcher.exec(text)) !== null) {
      hits.push({
        raw: match[0],
        normalized: rule.normalized,
        start: match.index,
        end: match.index + match[0].length,
        confidence: rule.confidence
      })
    }
  }
  return hits.sort((a, b) => a.start - b.start)
}
```

- [ ] **Step 6: Run the detector tests; verify all pass.**

Run: `cd apps/frontend/web && npx vitest run src/domain/template-mining/instruments.test.js src/domain/template-mining/directions.test.js`
Expected: PASS (existing + 2 new).

- [ ] **Step 7: Commit.**

```bash
git add apps/frontend/web/src/domain/template-mining/instruments.js apps/frontend/web/src/domain/template-mining/directions.js apps/frontend/web/src/domain/template-mining/instruments.test.js apps/frontend/web/src/domain/template-mining/directions.test.js
git commit -m "feat(overlay): overlay-aware instrument/direction detectors"
```

---

### Task 5: Domain — thread overlay through extraction, template, mining

**Files:**
- Modify: `apps/frontend/web/src/domain/template-mining/fields.js`
- Modify: `apps/frontend/web/src/domain/template-mining/template.js`
- Modify: `apps/frontend/web/src/domain/template-mining/extract.js`
- Modify: `apps/frontend/web/src/domain/template-mining/mining.js`
- Test: `apps/frontend/web/src/domain/template-mining/mining.test.js`

**Interfaces:**
- Consumes: `detectInstruments(text, overlay)`, `detectDirections(text, overlay)` (Task 4).
- Produces (all add an optional trailing `overlay = {}`, default = today's behavior):
  - `extractSignalFields(message, overlay)`
  - `normalizeTemplate(candidate, overlay)`
  - `attemptExtractSignal(input, overlay)`
  - `classifyMessageIntent(input, overlay)`
  - `mineTemplateGroups(messages, overlay)`

- [ ] **Step 1: Write the failing integration test.** Append to `apps/frontend/web/src/domain/template-mining/mining.test.js`:

```js
it('mines a signal that only parses once the overlay teaches its coin + token', () => {
  // 🚀 is a weak built-in BUY emoji; "АПТ" is unknown. Without both as confident
  // signals this message is not a clean candidate family.
  const message = {
    id: 'x1',
    text: 'АПТ 🚀\nEntry: 2.50\nStop: 2.40\nTarget: 2.70'
  }
  const overlay = {
    instrumentAliases: { 'АПТ': 'APTUSDT' },
    directionTokens: { '🚀': 'BUY' }
  }

  const withOverlay = mineTemplateGroups([message], overlay)
  const instruments = withOverlay.flatMap((g) =>
    g.candidates.map((c) => c.fields.instrument)
  )
  expect(instruments).toContain('APTUSDT')
})
```

- [ ] **Step 2: Run it; verify it fails.**

Run: `cd apps/frontend/web && npx vitest run src/domain/template-mining/mining.test.js`
Expected: the new test FAILS (overlay ignored → instrument not `APTUSDT`).

- [ ] **Step 3: Thread overlay in `fields.js`.** Change the detector-calling helpers and the entry point:

```js
function primaryInstrument(clean, overlay) {
  return detectInstruments(clean, overlay)[0] || null
}

function primaryDirection(clean, overlay) {
  const directions = detectDirections(clean, overlay)
  if (directions.length === 0) return null
  return [...directions].sort(
    (a, b) => b.confidence - a.confidence || a.start - b.start
  )[0]
}
```

In `classifyLine`, pass overlay to the header check (add `overlay` to its signature and the call in `extractSignalFields`):

```js
function classifyLine(line, state, overlay) {
  // ... unchanged until the header check ...
  const isHeader =
    detectInstruments(line, overlay).length > 0 ||
    detectDirections(line, overlay).length > 0
  if (isHeader && prices.length > 0 && !state.headerEntry) {
    state.headerEntry = entryFromPrice(prices[0])
  }
}

export function extractSignalFields(message, overlay = {}) {
  const { clean, lines } = normalizeMessageText(messageText(message))
  const instrument = primaryInstrument(clean, overlay)
  const direction = primaryDirection(clean, overlay)

  const state = { /* unchanged */ }
  for (const line of lines) classifyLine(line, state, overlay)
  // ... unchanged return ...
}
```

- [ ] **Step 4: Thread overlay in `template.js`.** Add `overlay` to the span collectors and `normalizeTemplate`:

```js
function instrumentSpans(clean, overlay) {
  return detectInstruments(clean, overlay).map((entity) => ({
    start: entity.start,
    end: entity.end,
    token: '<INSTRUMENT>'
  }))
}

function directionSpans(clean, overlay) {
  return detectDirections(clean, overlay).map((entity) => ({
    start: entity.start,
    end: entity.end,
    token: entity.confidence < 0.7 ? '<SIDE_EMOJI>' : '<SIDE>'
  }))
}

function collectSpans(clean, overlay) {
  const spans = [
    ...instrumentSpans(clean, overlay),
    ...directionSpans(clean, overlay),
    ...priceSpans(clean),
    ...marketSpans(clean)
  ].sort((a, b) => a.start - b.start || b.end - a.end)
  // ... unchanged dedupe/return ...
}

export function normalizeTemplate(candidate, overlay = {}) {
  const text = candidate.message?.text ?? candidate.text ?? ''
  const { clean } = normalizeMessageText(text)
  const spans = collectSpans(clean, overlay)
  // ... unchanged remainder ...
}
```

- [ ] **Step 5: Thread overlay in `extract.js`.** Pass `overlay` to every detector/extractor/normalizer call:

```js
export function attemptExtractSignal(input, overlay = {}) {
  const message = asMessage(input)
  const { clean } = normalizeMessageText(message.text)
  const instruments = detectInstruments(clean, overlay)
  const directions = detectDirections(clean, overlay)
  if (instruments.length === 0 || directions.length === 0) return null

  const fields = extractSignalFields(message, overlay)
  const intent = classifyIntent(message.text, fields)
  if (intent !== 'new_signal') return null

  const { templateKey, normalizedTemplate } = normalizeTemplate({ message }, overlay)
  if (!normalizedTemplate.trim()) return null

  const prices = detectPrices(clean)
  const geometry = validatePriceGeometry(fields)
  const confidence = scoreCandidate({ message, fields, directions })
  const rejectionReasons = collectRejectionReasons(intent, fields, directions, geometry)

  return {
    message, instruments, directions, prices, fields, intent,
    confidence, rejectionReasons, templateKey, normalizedTemplate
  }
}

export function classifyMessageIntent(input, overlay = {}) {
  const message = asMessage(input)
  return classifyIntent(message.text, extractSignalFields(message, overlay))
}
```

- [ ] **Step 6: Thread overlay in `mining.js`.**

```js
export function mineTemplateGroups(messages, overlay = {}) {
  const candidates = (messages || [])
    .map((message) => attemptExtractSignal(message, overlay))
    .filter(Boolean)
  const buckets = bucketByTemplate(candidates)
  const groups = [...buckets.entries()].map(([key, list]) => toGroup(key, list))
  return sortGroups(groups)
}
```

- [ ] **Step 7: Run the domain tests; verify all pass.**

Run: `cd apps/frontend/web && npx vitest run src/domain/template-mining/`
Expected: PASS (all existing + the new mining test). No-overlay paths unchanged.

- [ ] **Step 8: Commit.**

```bash
git add apps/frontend/web/src/domain/template-mining/fields.js apps/frontend/web/src/domain/template-mining/template.js apps/frontend/web/src/domain/template-mining/extract.js apps/frontend/web/src/domain/template-mining/mining.js apps/frontend/web/src/domain/template-mining/mining.test.js
git commit -m "feat(overlay): thread overlay through extraction/template/mining"
```

---

### Task 6: Domain — overlay in audit (reject phrases + thresholds)

**Files:**
- Modify: `apps/frontend/web/src/domain/template-mining/rules.js`
- Test: `apps/frontend/web/src/domain/template-mining/rules.test.js`

**Interfaces:**
- Consumes: `attemptExtractSignal(input, overlay)`, `classifyMessageIntent(input, overlay)`, `mineTemplateGroups(messages, overlay)` (Task 5); `detectInstruments/detectDirections(text, overlay)` (Task 4).
- Produces:
  - `compileRuleFromTemplate(group, overlay = {})` — appends `overlay.rejectPhrases` to `rejectIfContains`; uses `overlay.templateThresholds[group.templateKey]` as `confidenceThreshold` when present, else `deriveThreshold`.
  - `applyAcceptedRules(messages, rules, overlay = {})` — threads overlay to extraction, intent, miss detection, and the rare re-mine.

- [ ] **Step 1: Write the failing tests.** Append to `apps/frontend/web/src/domain/template-mining/rules.test.js` (use existing helpers/imports in that file; these assume `compileRuleFromTemplate`, `applyAcceptedRules`, `mineTemplateGroups` are imported there):

```js
it('lowers a template threshold from the overlay', () => {
  const group = {
    templateKey: 'tpl_demo',
    confidenceAvg: 0.9,
    candidates: [{ fields: { orderType: 'limit', entry: {}, stopLoss: 1, takeProfits: [1] } }]
  }
  const base = compileRuleFromTemplate(group)
  const tuned = compileRuleFromTemplate(group, {
    templateThresholds: { tpl_demo: 0.42 }
  })
  expect(tuned.confidenceThreshold).toBe(0.42)
  expect(tuned.confidenceThreshold).not.toBe(base.confidenceThreshold)
})

it('appends overlay reject phrases to a compiled rule', () => {
  const group = {
    templateKey: 'tpl_demo',
    confidenceAvg: 0.9,
    candidates: [{ fields: { orderType: 'limit', entry: {}, stopLoss: 1, takeProfits: [1] } }]
  }
  const rule = compileRuleFromTemplate(group, { rejectPhrases: ['giveaway'] })
  expect(rule.rejectIfContains).toContain('giveaway')
})
```

- [ ] **Step 2: Run them; verify they fail.**

Run: `cd apps/frontend/web && npx vitest run src/domain/template-mining/rules.test.js`
Expected: the two new tests FAIL (overlay arg ignored).

- [ ] **Step 3: Implement in `rules.js`.** Update `compileRuleFromTemplate`:

```js
export function compileRuleFromTemplate(group, overlay = {}) {
  const present = presentFields(group)
  const overrideThreshold = overlay?.templateThresholds?.[group.templateKey]
  return {
    id: `rule_${group.templateKey.replace(/^tpl_/, '')}`,
    name: formatLabel(group),
    templateKey: group.templateKey,
    required: ['instrument', 'direction'],
    fields: ruleFieldMap(present),
    rejectIfContains: [...REJECT_PHRASES, ...(overlay?.rejectPhrases ?? [])],
    confidenceThreshold:
      typeof overrideThreshold === 'number'
        ? overrideThreshold
        : deriveThreshold(group.confidenceAvg)
  }
}
```

Thread overlay through the audit. Update `isPotentialMiss`, `routeNonCandidate`, and `applyAcceptedRules`:

```js
function isPotentialMiss(message, overlay) {
  const { clean } = normalizeMessageText(message.text)
  const hasInstrument = detectInstruments(clean, overlay).length > 0
  const hasDirection = detectDirections(clean, overlay).length > 0
  if (hasInstrument !== hasDirection) return true
  if (!hasInstrument && !hasDirection) {
    return detectPrices(clean).length > 0 && hasTradingLabel(clean)
  }
  return false
}

function routeNonCandidate(message, buckets, overlay) {
  const intent = classifyMessageIntent(message, overlay)
  if (NON_SIGNAL_INTENTS.has(intent)) {
    buckets.rejected.push({ message, intent })
    return
  }
  if (isPotentialMiss(message, overlay)) buckets.misses.push(message)
}

export function applyAcceptedRules(messages, rules, overlay = {}) {
  const ruleByKey = new Map(rules.map((rule) => [rule.templateKey, rule]))
  const buckets = { parsed: [], ambiguous: [], rejected: [], rare: [], misses: [] }

  for (const message of messages || []) {
    const candidate = attemptExtractSignal(message, overlay)
    if (!candidate) {
      routeNonCandidate(message, buckets, overlay)
      continue
    }
    routeCandidate(candidate, ruleByKey, buckets)
  }

  return {
    parsedSignals: buckets.parsed,
    ambiguousCandidates: buckets.ambiguous,
    rejectedCandidates: buckets.rejected,
    rareTemplates: mineTemplateGroups(
      buckets.rare.map((candidate) => candidate.message),
      overlay
    ),
    potentialMisses: buckets.misses
  }
}
```

- [ ] **Step 4: Run the rules tests; verify all pass.**

Run: `cd apps/frontend/web && npx vitest run src/domain/template-mining/rules.test.js`
Expected: PASS (existing + 2 new).

- [ ] **Step 5: Commit.**

```bash
git add apps/frontend/web/src/domain/template-mining/rules.js apps/frontend/web/src/domain/template-mining/rules.test.js
git commit -m "feat(overlay): reject phrases + template thresholds in the audit"
```

---

### Task 7: Frontend — overlay API client

**Files:**
- Modify: `apps/frontend/web/src/shared/api/pipelineApi.js`
- Test: `apps/frontend/web/src/shared/api/pipelineApi.test.js`

**Interfaces:**
- Produces:
  - `getParserOverlay(token)` → `GET /parser-overlay` → response body `{ overlay }`.
  - `putParserOverlay(token, overlay)` → `PUT /parser-overlay` with `{ overlay }` → `{ overlay }`.

- [ ] **Step 1: Write the failing tests.** Append inside the `describe('pipelineApi — label', ...)` block (or a new block) in `pipelineApi.test.js`, importing `getParserOverlay, putParserOverlay`:

```js
it('reads the parser overlay', async () => {
  fetch.mockResolvedValueOnce(jsonResponse({ overlay: { rejectPhrases: ['x'] } }))
  const body = await getParserOverlay('jwt-token')
  expect(body.overlay.rejectPhrases).toEqual(['x'])
  expect(fetch).toHaveBeenCalledWith('http://localhost:8000/parser-overlay', {
    method: 'GET',
    headers: { Authorization: 'Bearer jwt-token' }
  })
})

it('writes the parser overlay', async () => {
  fetch.mockResolvedValueOnce(jsonResponse({ overlay: { rejectPhrases: ['x'] } }))
  await putParserOverlay('jwt-token', { rejectPhrases: ['x'] })
  expect(fetch).toHaveBeenCalledWith('http://localhost:8000/parser-overlay', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', Authorization: 'Bearer jwt-token' },
    body: JSON.stringify({ overlay: { rejectPhrases: ['x'] } })
  })
})
```

- [ ] **Step 2: Run them; verify they fail.**

Run: `cd apps/frontend/web && npx vitest run src/shared/api/pipelineApi.test.js`
Expected: FAIL — `getParserOverlay`/`putParserOverlay` are not exported.

- [ ] **Step 3: Implement in `pipelineApi.js`** (beside `listFeedHistory`):

```js
export function getParserOverlay(token) {
  return requestJson(`/parser-overlay`, { token })
}

export function putParserOverlay(token, overlay) {
  return requestJson(`/parser-overlay`, { method: 'PUT', token, body: { overlay } })
}
```

- [ ] **Step 4: Run the tests; verify they pass.**

Run: `cd apps/frontend/web && npx vitest run src/shared/api/pipelineApi.test.js`
Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add apps/frontend/web/src/shared/api/pipelineApi.js apps/frontend/web/src/shared/api/pipelineApi.test.js
git commit -m "feat(overlay): frontend client getParserOverlay/putParserOverlay"
```

---

### Task 8: Frontend — page wiring (fetch + thread overlay, re-mine on change)

**Files:**
- Modify: `apps/frontend/web/src/app/ProductApp.jsx` (pass overlay client callbacks to the page)
- Modify: `apps/frontend/web/src/features/template-mining/TemplateMiningPage.jsx`
- Test: `apps/frontend/web/src/features/template-mining/TemplateMiningPage.test.jsx`

**Interfaces:**
- Consumes: `getParserOverlay`/`putParserOverlay` (Task 7); `mineTemplateGroups(messages, overlay)`, `compileRuleFromTemplate(group, overlay)`, `applyAcceptedRules(messages, rules, overlay)` (Tasks 5–6).
- Produces: `TemplateMiningPage` accepts `overlay` (object) + `onSaveOverlay(overlay)` (async) props; holds `overlay` in state seeded from `onLoadOverlay`; threads it into mining/compile/audit; saving an overlay re-mines.

- [ ] **Step 1: Write the failing test.** Append to `TemplateMiningPage.test.jsx`. It proves the page threads a provided overlay into mining (an otherwise-unrecognised coin parses):

```js
it('threads a provided overlay into mining', async () => {
  const user = userEvent.setup()
  const messages = [{ id: 'o1', text: 'АПТ 🚀\nEntry: 2.5\nStop: 2.4\nTarget: 2.7' }]
  const onListMessages = vi.fn().mockResolvedValue({ messages })
  render(
    <TemplateMiningPage
      feeds={[{ id: 'apex', name: 'Apex' }]}
      authToken="jwt"
      onListMessages={onListMessages}
      overlay={{
        instrumentAliases: { 'АПТ': 'APTUSDT' },
        directionTokens: { '🚀': 'BUY' }
      }}
    />
  )
  await user.click(screen.getByRole('button', { name: /Run template mining/i }))
  expect(await screen.findByText('Messages scanned')).toBeTruthy()
  // APTUSDT only appears if the overlay reached the detectors.
  expect(await screen.findAllByText(/APTUSDT/)).toBeTruthy()
})
```

- [ ] **Step 2: Run it; verify it fails.**

Run: `cd apps/frontend/web && npx vitest run src/features/template-mining/TemplateMiningPage.test.jsx`
Expected: FAIL — overlay prop ignored; `APTUSDT` not found.

- [ ] **Step 3: Thread overlay in `TemplateMiningPage.jsx`.** Accept an `overlay` prop (default `{}`) and pass it into the three pipeline calls:

```js
export function TemplateMiningPage({
  feeds = [],
  authToken,
  onListMessages,
  fireToast,
  overlay = {}
}) {
  // ... existing state ...

  const mined = mineTemplateGroups(minedMessages, overlay)   // in finishMining

  const rules = useMemo(
    () => acceptedGroups.map((group) => compileRuleFromTemplate(group, overlay)),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [acceptedGroups.map((group) => group.templateKey).join('|'), overlay]
  )

  const audit = useMemo(() => {
    if (!result || rules.length === 0) return null
    return applyAcceptedRules(result.messages, rules, overlay)
  }, [result, rules, overlay])
  // ... rest unchanged ...
}
```

`finishMining` must read the current `overlay`; change its `mineTemplateGroups(minedMessages)` call to `mineTemplateGroups(minedMessages, overlay)`.

- [ ] **Step 4: Wire `ProductApp.jsx`.** Import the client and load the overlay once, pass it down. Add near the other pipeline imports:

```js
import { getParserOverlay, putParserOverlay, listFeedHistory, listMessages, /* … */ } from '../shared/api/pipelineApi.js'
```

In `ProductApp`, add overlay state + load effect:

```js
const [overlay, setOverlay] = useState({})

useEffect(() => {
  if (!authToken) return
  getParserOverlay(authToken)
    .then((body) => setOverlay(body.overlay || {}))
    .catch(() => {})
}, [authToken])

async function saveOverlay(next) {
  const body = await putParserOverlay(authToken, next)
  setOverlay(body.overlay || next)
}
```

Pass to the page in the `nav === 'mining'` branch:

```js
<TemplateMiningPage
  feeds={feeds}
  authToken={authToken}
  onListMessages={(chatId) => listFeedHistory(authToken, chatId)}
  fireToast={fireToast}
  overlay={overlay}
  onSaveOverlay={saveOverlay}
/>
```

- [ ] **Step 5: Run the page test + full domain/app suite.**

Run: `cd apps/frontend/web && npx vitest run src/features/template-mining/ src/app/`
Expected: PASS (new test + existing). If the existing AuditReview/page tests pass an `overlay`-less page, the `overlay = {}` default keeps them green.

- [ ] **Step 6: Commit.**

```bash
git add apps/frontend/web/src/app/ProductApp.jsx apps/frontend/web/src/features/template-mining/TemplateMiningPage.jsx apps/frontend/web/src/features/template-mining/TemplateMiningPage.test.jsx
git commit -m "feat(overlay): fetch + thread the overlay through the mining page"
```

---

### Task 9: Frontend — Manage Overlay panel

**Files:**
- Create: `apps/frontend/web/src/features/template-mining/OverlayManager.jsx`
- Create: `apps/frontend/web/src/features/template-mining/OverlayManager.test.jsx`
- Modify: `apps/frontend/web/src/features/template-mining/TemplateMiningPage.jsx` (render the panel)
- Modify: `apps/frontend/web/src/features/template-mining/templateMining.css` (panel styles)

**Interfaces:**
- Consumes: `overlay` (object), `onSaveOverlay(nextOverlay)` (async) — from the page.
- Produces: `OverlayManager({ overlay, onSave })` — lists the four overlay sections (instrument aliases, direction tokens, reject phrases, template thresholds), each row removable; an add-row per section. Every edit calls `onSave(nextOverlay)` with the full next overlay.

- [ ] **Step 1: Write the failing test** `OverlayManager.test.jsx`:

```js
import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { OverlayManager } from './OverlayManager.jsx'

const OVERLAY = {
  instrumentAliases: { 'АПТ': 'APTUSDT' },
  directionTokens: { '🚀': 'BUY' },
  rejectPhrases: ['giveaway'],
  templateThresholds: {}
}

describe('OverlayManager', () => {
  it('lists current overlay entries', () => {
    render(<OverlayManager overlay={OVERLAY} onSave={vi.fn()} />)
    expect(screen.getByText('APTUSDT')).toBeTruthy()
    expect(screen.getByText('giveaway')).toBeTruthy()
  })

  it('removing a reject phrase saves the overlay without it', async () => {
    const user = userEvent.setup()
    const onSave = vi.fn()
    render(<OverlayManager overlay={OVERLAY} onSave={onSave} />)
    await user.click(screen.getByRole('button', { name: /Remove reject phrase giveaway/i }))
    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({ rejectPhrases: [] })
    )
  })

  it('adding a reject phrase saves the overlay with it', async () => {
    const user = userEvent.setup()
    const onSave = vi.fn()
    render(<OverlayManager overlay={OVERLAY} onSave={onSave} />)
    await user.type(screen.getByPlaceholderText(/Add reject phrase/i), 'promo')
    await user.click(screen.getByRole('button', { name: /^Add reject phrase$/i }))
    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({ rejectPhrases: ['giveaway', 'promo'] })
    )
  })
})
```

- [ ] **Step 2: Run it; verify it fails.**

Run: `cd apps/frontend/web && npx vitest run src/features/template-mining/OverlayManager.test.jsx`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement `OverlayManager.jsx`.** A compact panel; normalizes missing sections to empty, and always calls `onSave` with a complete overlay object:

```jsx
import { useState } from 'react'
import { Button, Icon, Input } from '@verasig/design-system'

const EMPTY = {
  instrumentAliases: {},
  directionTokens: {},
  rejectPhrases: [],
  templateThresholds: {}
}

function normalize(overlay) {
  return { ...EMPTY, ...(overlay || {}) }
}

export function OverlayManager({ overlay, onSave }) {
  const current = normalize(overlay)
  const [alias, setAlias] = useState({ term: '', symbol: '' })
  const [token, setToken] = useState({ term: '', side: 'BUY' })
  const [phrase, setPhrase] = useState('')

  const save = (patch) => onSave({ ...current, ...patch })

  const removeKey = (mapName, key) => {
    const next = { ...current[mapName] }
    delete next[key]
    save({ [mapName]: next })
  }
  const addAlias = () => {
    if (!alias.term || !alias.symbol) return
    save({ instrumentAliases: { ...current.instrumentAliases, [alias.term]: alias.symbol } })
    setAlias({ term: '', symbol: '' })
  }
  const addToken = () => {
    if (!token.term) return
    save({ directionTokens: { ...current.directionTokens, [token.term]: token.side } })
    setToken({ term: '', side: 'BUY' })
  }
  const addPhrase = () => {
    if (!phrase.trim()) return
    save({ rejectPhrases: [...current.rejectPhrases, phrase.trim()] })
    setPhrase('')
  }
  const removePhrase = (value) =>
    save({ rejectPhrases: current.rejectPhrases.filter((p) => p !== value) })

  return (
    <section className="vrs-tm-overlay">
      <div className="vrs-tm-section__head">
        <div>
          <div className="vrs-tm-section__title">Taught to the parser</div>
          <div className="vrs-tm-section__sub">
            Custom coins, direction tokens and reject phrases applied to every mine
          </div>
        </div>
      </div>

      <div className="vrs-tm-overlay__group">
        <div className="vrs-tm-overlay__label">Coin aliases</div>
        {Object.entries(current.instrumentAliases).map(([term, symbol]) => (
          <div key={term} className="vrs-tm-overlay__row">
            <span>
              {term} → {symbol}
            </span>
            <Button
              variant="ghost"
              size="sm"
              aria-label={`Remove alias ${term}`}
              iconLeft={<Icon name="x" size={13} />}
              onClick={() => removeKey('instrumentAliases', term)}
            />
          </div>
        ))}
        <div className="vrs-tm-overlay__add">
          <Input
            placeholder="Alias e.g. АПТ"
            value={alias.term}
            aria-label="Alias term"
            onChange={(e) => setAlias({ ...alias, term: e.target.value })}
          />
          <Input
            placeholder="Symbol e.g. APTUSDT"
            value={alias.symbol}
            aria-label="Alias symbol"
            onChange={(e) => setAlias({ ...alias, symbol: e.target.value })}
          />
          <Button variant="secondary" size="sm" onClick={addAlias}>
            Add alias
          </Button>
        </div>
      </div>

      <div className="vrs-tm-overlay__group">
        <div className="vrs-tm-overlay__label">Direction tokens</div>
        {Object.entries(current.directionTokens).map(([term, side]) => (
          <div key={term} className="vrs-tm-overlay__row">
            <span>
              {term} → {side}
            </span>
            <Button
              variant="ghost"
              size="sm"
              aria-label={`Remove direction token ${term}`}
              iconLeft={<Icon name="x" size={13} />}
              onClick={() => removeKey('directionTokens', term)}
            />
          </div>
        ))}
        <div className="vrs-tm-overlay__add">
          <Input
            placeholder="Token e.g. 🚀"
            value={token.term}
            aria-label="Direction token"
            onChange={(e) => setToken({ ...token, term: e.target.value })}
          />
          <select
            aria-label="Token side"
            value={token.side}
            onChange={(e) => setToken({ ...token, side: e.target.value })}
          >
            <option value="BUY">BUY</option>
            <option value="SELL">SELL</option>
          </select>
          <Button variant="secondary" size="sm" onClick={addToken}>
            Add token
          </Button>
        </div>
      </div>

      <div className="vrs-tm-overlay__group">
        <div className="vrs-tm-overlay__label">Reject phrases</div>
        {current.rejectPhrases.map((value) => (
          <div key={value} className="vrs-tm-overlay__row">
            <span>{value}</span>
            <Button
              variant="ghost"
              size="sm"
              aria-label={`Remove reject phrase ${value}`}
              iconLeft={<Icon name="x" size={13} />}
              onClick={() => removePhrase(value)}
            />
          </div>
        ))}
        <div className="vrs-tm-overlay__add">
          <Input
            placeholder="Add reject phrase"
            value={phrase}
            aria-label="Reject phrase"
            onChange={(e) => setPhrase(e.target.value)}
          />
          <Button variant="secondary" size="sm" onClick={addPhrase}>
            Add reject phrase
          </Button>
        </div>
      </div>
    </section>
  )
}

export default OverlayManager
```

- [ ] **Step 4: Add styles** to `templateMining.css`:

```css
/* ---- overlay manager ---- */
.vrs-tm-overlay {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.vrs-tm-overlay__group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.vrs-tm-overlay__label {
  font-family: var(--font-sans);
  font-size: var(--text-2xs);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-faint);
}
.vrs-tm-overlay__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 6px 10px;
  font-family: var(--font-mono);
  font-size: var(--text-2xs);
  color: var(--text-body);
  background: var(--surface-sunken);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
}
.vrs-tm-overlay__add {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 8px;
}
.vrs-tm-overlay__add .vrs-field {
  flex: 1 1 160px;
}
```

- [ ] **Step 5: Render it on the page.** In `TemplateMiningPage.jsx`, import and render after `CompiledRulesPanel` (only when authenticated + `onSaveOverlay` provided):

```jsx
import { OverlayManager } from './OverlayManager.jsx'
// ...
{onSaveOverlay && <OverlayManager overlay={overlay} onSave={onSaveOverlay} />}
```

Add `onSaveOverlay` to the component's destructured props.

- [ ] **Step 6: Run the panel test + the template-mining suite.**

Run: `cd apps/frontend/web && npx vitest run src/features/template-mining/`
Expected: PASS (OverlayManager + existing).

- [ ] **Step 7: Commit.**

```bash
git add apps/frontend/web/src/features/template-mining/OverlayManager.jsx apps/frontend/web/src/features/template-mining/OverlayManager.test.jsx apps/frontend/web/src/features/template-mining/TemplateMiningPage.jsx apps/frontend/web/src/features/template-mining/templateMining.css
git commit -m "feat(overlay): manage panel (view/add/remove) wired to the page"
```

---

### Task 10: Full gate + end-to-end verification

**Files:** none (verification only).

- [ ] **Step 1: Backend gate.**

Run: `cd /Users/evgesha/Projects/trading/Verasig && make backend-format && make backend-lint && make backend-test`
Expected: ruff clean; all backend tests pass (including the two new overlay test files).

- [ ] **Step 2: Frontend gate.**

Run: `make frontend-format && make frontend-lint && make frontend-format-check && make frontend-test && make frontend-build`
Expected: eslint clean; prettier clean; all frontend tests pass; build succeeds.

- [ ] **Step 3: End-to-end on the real feed (Playwright).** Bring up `make dev` (DB is stamped at `0011`; `migrate` then applies `0012`). Mint the dev JWT for `aleshiner@mail.ru`, open Mining, Run, Apply suggestions. Then, via the Manage panel:
  - Add a reject phrase that appears in a current Parsed row → that row moves to Rejected on re-mine (the count drops).
  - Add a direction token / coin alias present in a current Miss → that message becomes a candidate (Parsed/Ambiguous) on re-mine.
  - Reload the page → `GET /parser-overlay` restores the entries (persistence holds).
  Confirm 0 console errors and no horizontal overflow.

- [ ] **Step 4: No stray changes.**

Run: `git status --short`
Expected: only the user's `Makefile` modification remains unstaged; everything else committed.

---

## Self-Review

**Spec coverage:** Overlay store + migration (T1) · repository (T2) · GET/PUT API + per-account scoping (T3) · vocabulary lever via overlay-aware detectors (T4) threaded through the whole pipeline (T5) · reject-phrase + threshold levers (T6) · client (T7) · page fetch/thread/re-mine (T8) · Manage panel view/add/remove (T9) · tests at every layer + e2e (T2,T3,T4,T5,T6,T7,T8,T9,T10). Phase-2 (guided per-row) is explicitly out of scope. All Phase-1 spec sections map to a task.

**Placeholder scan:** No TBD/TODO; every code step shows real code; every command shows expected output.

**Type/name consistency:** `overlay` shape (`instrumentAliases`/`directionTokens`/`rejectPhrases`/`templateThresholds`) is identical across backend `config`, API body `{overlay}`, client, domain merges, and the Manage panel. `read_overlay`/`upsert_overlay`, `getParserOverlay`/`putParserOverlay`, `compileRuleFromTemplate(group, overlay)`, `applyAcceptedRules(messages, rules, overlay)`, `mineTemplateGroups(messages, overlay)` names match between their producing and consuming tasks. The default `overlay = {}` on every domain signature keeps all existing callers/tests green.
