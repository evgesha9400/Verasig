# Backend API Rewrite — Implementation Plan

> **For agentic workers:** Execute task-by-task, tracking the checkbox (`- [ ]`) steps. If the superpowers plugin is available, use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans; otherwise follow the working rules below verbatim.

**Goal:** Replace the CLI delivery layer with a multi-tenant FastAPI API implementing the contract in [requirements.md](requirements.md), keeping all domain services intact.

**Architecture:** Three layers — `foundation` (db, security, telegram, bybit, anthropic), `services` (existing domain services + new `accounts`, `telegram_link`, `exchanges`, `jobs`, `projection`), `api` (routers + schemas + deps). API routers call services; services never import `api`.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 (sync), Alembic, PostgreSQL 16, Telethon, Anthropic SDK, PyJWT, bcrypt, cryptography (Fernet), sse-starlette, UV.

**Working rules (every task):**
- TDD: failing test → minimal code → green → `make format && make lint` → commit (conventional, bulleted body).
- All work on `feature/backend-api-rewrite` off `develop`; squash broken intermediate commits before merge.
- Run scoped tests per step; full `make test` at every task end.
- Wire-format models inherit `CamelModel` (Task 2); JSON is camelCase, Python/DB snake_case.
- Tenancy guard: every `/chats/{id}/…` router resolves ownership via `require_user_channel` (Task 9); every task touching such routes includes a foreign-user API test (second registered account → 404 `CHAT_NOT_FOUND`).

**Target structure (new/changed only):**

```
apps/backend/src/verasig/
├── api/
│   ├── app.py                      # create_app(): CORS, routers, error handlers
│   ├── deps.py                     # get_settings, get_session_factory, get_current_user, plan guards
│   ├── errors.py                   # ApiError(code, status, message) + handler
│   ├── schemas/
│   │   ├── common.py               # CamelModel base
│   │   ├── auth.py user.py telegram.py chat.py message.py rule.py
│   │   └── verify.py exchange.py risk.py backtest.py signal.py
│   └── routers/
│       ├── health.py auth.py user.py telegram.py chats.py labels.py
│       └── distill.py verify.py exchanges.py risk.py backtest.py signals.py
├── services/
│   ├── accounts/        # plans.py passwords.py tokens.py service.py
│   ├── telegram_link/   # service.py        (connect/verify/status, per-user client factory)
│   ├── exchanges/       # catalog.py service.py
│   ├── jobs/            # registry.py       (JobRegistry + SSE bridge)
│   ├── labeling/        # service.py        (sample, label upsert, counts)
│   ├── verification/    # service.py        (samples w/ predictions, verdict fold-in)
│   ├── backtesting/     # service.py        (fold→klines→simulate→score→persist)
│   └── projection/      # chats.py signals.py rules.py dates.py
├── foundation/
│   ├── security.py      # bcrypt + Fernet helpers
│   ├── anthropic_runner.py
│   ├── bybit_account.py # HMAC key verification
│   └── telegram_session.py   # REWRITTEN: stateless helpers for per-user sessions
├── domain/
│   ├── account.py       # UserAccount, Plan
│   └── risk_config.py   # RiskConfig
└── storage/             # + account_repository.py telegram_link_repository.py
                         #   user_channel_repository.py exchange_repository.py
                         #   risk_repository.py backtest_repository.py lifecycle_link_repository.py
```

---

### Task 1: Dependencies, config, scaffolding

**Files:** Modify `pyproject.toml`, `src/verasig/config.py`, `.env.example`, `tests/unit/test_config.py`

- [ ] **Step 1:** `uv add fastapi "uvicorn[standard]" sse-starlette anthropic pyjwt bcrypt cryptography`. Leave `typer`, `[project.scripts]`, and `cli.py` untouched — the CLI and its 11 importing test files stay green until Task 19 deletes them.
- [ ] **Step 2:** Failing test in `tests/unit/test_config.py`:

```python
def test_settings_carry_api_secrets(monkeypatch):
    monkeypatch.setenv("VERASIG_JWT_SECRET", "jwt-secret")
    monkeypatch.setenv("VERASIG_FERNET_KEY", "fkey")
    settings = Settings(_env_file=None)
    assert settings.jwt_secret == "jwt-secret"
    assert settings.fernet_key == "fkey"
    assert settings.anthropic_model == "claude-sonnet-4-6"
    assert settings.cors_origins == ["http://localhost:5173"]
```

- [ ] **Step 3:** In `Settings`: add `jwt_secret: str = "dev-secret"`, `fernet_key: str = ""`, `anthropic_api_key: str = ""`, `anthropic_model: str = "claude-sonnet-4-6"`, `cors_origins: list[str] = ["http://localhost:5173"]`, `jwt_ttl_days: int = 7`. CLI-era fields (`session_path`, `telegram_api_id/hash/phone`, `distiller_command`, `extractor_command`) stay until Task 19 — `cli.py` still reads them.
- [ ] **Step 4:** Update `.env.example` with the new vars (+ note: `VERASIG_FERNET_KEY` from `uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`).
- [ ] **Step 5:** `uv run pytest tests/unit/test_config.py -v` → PASS. Commit `chore(backend): add API stack dependencies and settings`.

### Task 2: App factory, errors, health

**Files:** Create `api/app.py`, `api/errors.py`, `api/schemas/common.py`, `api/routers/health.py`, `tests/api/conftest.py`, `tests/api/test_health.py`

- [ ] **Step 1:** Failing test:

```python
# tests/api/test_health.py
def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

`tests/api/conftest.py` builds the app over the migrated testcontainers DB (reuse root `conftest.py` fixtures):

```python
@pytest.fixture()
def app(session_factory, pg_url):
    settings = Settings(_env_file=None, database_url_override=pg_url,
                        jwt_secret="test-secret", fernet_key=Fernet.generate_key().decode())
    return create_app(settings, session_factory=session_factory)

@pytest.fixture()
def client(app):
    return TestClient(app)
```

- [ ] **Step 2:** Implement:

```python
# api/errors.py
class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str): ...
async def api_error_handler(request, exc: ApiError) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content={"error": {"code": exc.code, "message": exc.message}})

# api/schemas/common.py
class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

# api/app.py
def create_app(settings: Settings, session_factory: sessionmaker | None = None) -> FastAPI:
    app = FastAPI(title="Verasig API")
    app.state.settings = settings
    app.state.session_factory = session_factory or make_session_factory(settings.database_url)
    app.state.jobs = JobRegistry()          # Task 8 — stub class until then
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                       allow_methods=["*"], allow_headers=["*"])
    app.add_exception_handler(ApiError, api_error_handler)
    for router in ALL_ROUTERS: app.include_router(router)
    return app
```

`api/routers/health.py`: `GET /health` runs `select 1` via `request.app.state.session_factory`.
- [ ] **Step 3:** `uv run pytest tests/api/test_health.py -v` → PASS. Commit `feat(backend): FastAPI app factory with health endpoint`.

### Task 3: Migration 0006 + ORM rows + repositories

**Files:** Create `migrations/versions/0006_multi_tenant_api.py`, `storage/{account,telegram_link,user_channel,exchange,risk,backtest,lifecycle_link}_repository.py`, `domain/account.py`, `domain/risk_config.py`; Modify `storage/models.py`, `storage/repositories.py`, `tests/conftest.py`, `tests/integration/test_migrations.py`, `tests/integration/test_repositories.py`

- [ ] **Step 1:** Failing migration test: extend `test_migrations.py` asserting tables/columns from requirements §5 exist after `upgrade head` (all 7 new tables; `golden_label.user_id`+`label`; `filter_rule.user_id`+`display`; `parser_rule.user_id`; `user_id` on the four extraction-projection tables below).
- [ ] **Step 2:** Add ORM rows to `models.py` (mirror requirements §5 exactly; chat-status enum as `String` + CHECK constraint like existing enum columns). Write migration 0006. Tenant boundary (requirements D16): capture + seed candidates stay global; **all rule-driven projections become user-scoped** — add `user_id` to `extracted_signal` + `unrecognized_signal` (UNIQUE(event_id) → UNIQUE(user_id, event_id)), `parser_drift_warning` (→ UNIQUE(user_id, event_id)), `filter_drift_warning` (→ UNIQUE(user_id, channel_id, message_id)). Rule identity: `rule_id` stays the PK but the distiller stamps it **user-scoped** — `f"{user_id}:{channel_id}-filter-v{version}"` / `f"{user_id}:{channel_id}-parser-{n}-v{version}"` (today's stamp `{channel_id}-filter-v{version}` collides when two users distill the same channel); add `UNIQUE NULLS NOT DISTINCT (user_id, channel_id, version)` on `filter_rule` (one filter per user+channel+version; parser rules are many-per-version, no such unique). Existing-table changes: all added `user_id` columns **nullable** (CLI writes `None` until Task 19; uniques use `NULLS NOT DISTINCT`); new tables enforce NOT NULL. Single migration, no data migration (pre-launch DB).
- [ ] **Step 2b:** Extend `_ALL_TABLES` in `tests/conftest.py` with all 7 new tables (truncation must cover them or state leaks across tests): `user_account`, `user_telegram_link`, `user_channel`, `user_exchange_connection`, `chat_risk_config`, `backtest_result`, `lifecycle_link`.
- [ ] **Step 3:** Domain dataclasses:

```python
# domain/account.py
class Plan(StrEnum): OBSERVER = "observer"; OPERATOR = "operator"; DESK = "desk"
@dataclass(frozen=True)
class UserAccount:
    id: UUID; email: str; password_hash: str; first_name: str; last_name: str
    plan: Plan; pending_email: str | None; cancel_at: datetime | None; created_at: datetime

# domain/risk_config.py
class EntryMode(StrEnum): FIRST="first"; MID="mid"; LADDER="ladder"
class Weighting(StrEnum): EQUAL="equal"; MARTINGALE="martingale"
class ExitSource(StrEnum): SIGNAL="signal"; CUSTOM="custom"
@dataclass(frozen=True)
class RiskConfig:
    entry_mode: EntryMode = EntryMode.MID; levels: int = 3
    weighting: Weighting = Weighting.EQUAL; exit_source: ExitSource = ExitSource.SIGNAL
    stop_pct: Decimal = Decimal("2.5"); tp_pct: Decimal = Decimal("7.5")
    risk_pct: Decimal = Decimal("2.0"); leverage: int = 5
```

Also `domain/label.py`: add `class LabelKind(StrEnum): SIGNAL="signal"; NOISE="noise"; MODIFIER="modifier"` and `label: LabelKind` on `GoldenLabel` (keep `is_signal` as derived property).
- [ ] **Step 4:** Repositories, one module each, function style matching existing repos (session first arg):
  - `account_repository`: `insert_account`, `find_by_email`, `find_by_id`, `update_profile`, `set_pending_email`, `apply_pending_email`, `set_plan`, `set_cancel_at`
  - `telegram_link_repository`: `upsert_pending`, `mark_connected`, `read_link`
  - `user_channel_repository`: `subscribe`, `unsubscribe` (cascades user-scoped rows: labels, rules, risk, backtests, lifecycle links), `read_subscriptions`, `read_subscription`, `set_status`, `bump_verify_attempt`, `count_subscriptions`
  - `exchange_repository`: `upsert_connection`, `set_connected`, `read_connections`
  - `risk_repository`: `upsert_risk_config`, `read_risk_config`
  - `backtest_repository`: `insert_result`, `read_latest_results(user_id) -> dict[channel_id, row]`
  - `lifecycle_link_repository`: `insert_link`, `read_links(user_id, channel_id)`
  - `rule_repository`: thread `user_id` through `upsert/read` for labels + rules
  - `outcome_repository` + `drift_repository`: thread `user_id: UUID | None` through `record_outcome`, `insert_*`, `read_*`; CLI call sites pass `None` until Task 19 deletes them. The four projection tables keep `user_id` **nullable** with `UNIQUE NULLS NOT DISTINCT (user_id, event_id)` (PG ≥ 15) so the one-outcome-per-event invariant holds for both API and transitional CLI writes
- [ ] **Step 5:** Round-trip integration tests per repo in `test_repositories.py` (insert → read → update → assert). `uv run pytest tests/integration/test_migrations.py tests/integration/test_repositories.py -v` → PASS. Commit `feat(backend): multi-tenant schema and repositories`.

### Task 4: Security foundation (bcrypt, Fernet, JWT)

**Files:** Create `foundation/security.py`, `services/accounts/passwords.py`, `services/accounts/tokens.py`, `tests/unit/test_security.py`, `tests/unit/test_tokens.py`

- [ ] **Step 1:** Failing tests: hash→check round-trip true / wrong password false; encrypt→decrypt round-trip; access-token issue→read round-trip; expired token raises; garbage token raises; email-change token round-trips `(user_id, new_email)`; **wrong purpose rejected** (access token fed to `read_email_change_token` raises, and vice versa).
- [ ] **Step 2:** Implement:

```python
# foundation/security.py
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()
def check_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())
def encrypt_secret(plain: str, fernet_key: str) -> str:
    return Fernet(fernet_key.encode()).encrypt(plain.encode()).decode()
def decrypt_secret(token: str, fernet_key: str) -> str:
    return Fernet(fernet_key.encode()).decrypt(token.encode()).decode()

# services/accounts/tokens.py — purpose-claimed JWTs; one private pair, public helpers per purpose
class TokenInvalidError(Exception): ...

def _issue(claims: dict, purpose: str, secret: str, ttl: timedelta) -> str:
    now = datetime.now(tz=UTC)
    return jwt.encode({**claims, "purpose": purpose, "iat": now, "exp": now + ttl},
                      secret, algorithm="HS256")

def _read(token: str, purpose: str, secret: str) -> dict:
    try:
        claims = jwt.decode(token, secret, algorithms=["HS256"])
        if claims.get("purpose") != purpose: raise TokenInvalidError()
        return claims
    except jwt.InvalidTokenError as error:
        raise TokenInvalidError() from error

def issue_token(user_id: UUID, secret: str, ttl: timedelta) -> str:
    return _issue({"sub": str(user_id)}, "access", secret, ttl)

def read_user_id(token: str, secret: str) -> UUID:
    return UUID(_read(token, "access", secret)["sub"])

def issue_email_change_token(user_id: UUID, new_email: str, secret: str, ttl: timedelta) -> str:
    return _issue({"sub": str(user_id), "new_email": new_email}, "email-change", secret, ttl)

def read_email_change_token(token: str, secret: str) -> tuple[UUID, str]:
    claims = _read(token, "email-change", secret)
    return UUID(claims["sub"]), claims["new_email"]
```

(`passwords.py` re-exports hash/check so services never import foundation directly for this.)
- [ ] **Step 3:** `uv run pytest tests/unit/test_security.py tests/unit/test_tokens.py -v` → PASS. Commit `feat(backend): password hashing, secret encryption, jwt tokens`.

### Task 5: Auth endpoints + current-user dependency

**Files:** Create `services/accounts/service.py`, `api/routers/auth.py`, `api/schemas/auth.py`, `api/schemas/user.py`, `api/deps.py`, `tests/api/test_auth.py`

- [ ] **Step 1:** Failing tests: register → 201 with token + user echo; duplicate email → 409 `AUTH_EMAIL_TAKEN`; password < 10 chars → 422; login ok → token; bad password → 401 `AUTH_INVALID_CREDENTIALS`; `/auth/me` with token → user; without → 401; logout → 204.
- [ ] **Step 2:** `services/accounts/service.py` micro-steps: `register_account(session, first_name, last_name, email, password) -> UserAccount` (normalize email lower, reject duplicate, hash), `authenticate(session, email, password) -> UserAccount` (raise `InvalidCredentialsError`), `present_user(account) -> dict` (camel keys via schema, `plan/pendingEmail/cancelAt`).
- [ ] **Step 3:** `api/deps.py`:

```python
def get_current_user(request: Request,
                     authorization: str | None = Header(None),
                     token: str | None = Query(None)) -> UserAccount:
    raw = token or _bearer(authorization)          # SSE uses ?token=
    if raw is None: raise ApiError(401, "AUTH_REQUIRED", "Missing token")
    try: user_id = read_user_id(raw, request.app.state.settings.jwt_secret)
    except TokenInvalidError: raise ApiError(401, "AUTH_INVALID_TOKEN", "Invalid token")
    with request.app.state.session_factory() as session:
        account = find_by_id(session, user_id)
    if account is None: raise ApiError(401, "AUTH_UNKNOWN_USER", "Unknown user")
    return account
```

Router: `POST /auth/register` (201, `{token, user}`), `POST /auth/login`, `POST /auth/logout` (204), `GET /auth/me`. Schemas per requirements §4 with `password: str = Field(min_length=10)`.
- [ ] **Step 4:** `uv run pytest tests/api/test_auth.py -v` → PASS. Commit `feat(backend): jwt auth endpoints and current-user dependency`.

### Task 6: User profile & subscription endpoints

**Files:** Create `api/routers/user.py`, `services/accounts/mailer.py`; Modify `services/accounts/service.py`; Create `tests/api/test_user.py`

- [ ] **Step 1:** Failing tests: PATCH name persists; POST email sets `pendingEmail` + leaves `email`; confirm with logged token applies email and clears pending; reset-request → 202; subscription change → plan updated; cancel sets `cancelAt` ≈ now+30 d; resume clears it; invalid plan → 422.
- [ ] **Step 2:** `mailer.py` = logging stub: `send_email_confirm(email, token)` logs the token (dev retrieves it from logs); `send_password_reset_requested(email)` logs the request **only** — no token exists because v1 has no reset-completion endpoint (deferred with email infra; requirements §1). Confirm token = `issue_email_change_token(user_id, new_email, …)` from Task 4; the confirm endpoint applies via `read_email_change_token`.
- [ ] **Step 3:** Service micro-steps: `rename_account`, `request_email_change`, `confirm_email_change`, `change_plan`, `cancel_subscription`, `resume_subscription`. Router endpoints per requirements §4.
- [ ] **Step 4:** `uv run pytest tests/api/test_user.py -v` → PASS. Commit `feat(backend): profile, email-change, subscription endpoints`.

### Task 7: Per-user Telegram link

**Files:** Modify `foundation/telegram_session.py` (add per-user functions; legacy global-session helpers and their tests stay until Task 19 — `cli.py` still imports them); Create `services/telegram_link/service.py`, `api/routers/telegram.py`, `api/schemas/telegram.py`, `tests/unit/test_telegram_link.py`, `tests/api/test_telegram.py`; Modify `tests/fakes.py`, `domain/protocols.py`

- [ ] **Step 1:** Define the auth seam so tests need no Telethon network — vendor-neutral, pure types only (domain must not import Telethon): `TelegramAuth` protocol in `domain/protocols.py` with `send_code(api_id, api_hash, phone) -> PendingCode(session_string, phone_code_hash)` and `sign_in(session_string, api_id, api_hash, phone, code, phone_code_hash) -> str` (returns final session string). Per-user *sources* come from a separate foundation factory `make_user_source(session_string, api_id, api_hash) -> TelegramSource` (returns a connected `TelethonSource`; used by Tasks 9–10). Add `FakeTelegramAuth` to `tests/fakes.py` (canned hashes; raises `CodeInvalidError` on wrong code).
- [ ] **Step 2:** Failing unit tests for `services/telegram_link/service.py`: connect stores encrypted pending link; verify flips to connected + stores encrypted session; wrong code surfaces error and stays pending; status masks phone (`+44 •••• 8821`).
- [ ] **Step 3:** Implement service (encrypt `api_hash`/`session_string` with Fernet via settings) + real Telethon adapter in `foundation/telegram_session.py`:

```python
async def send_code(api_id, api_hash, phone) -> PendingCode:
    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()
    try:
        sent = await client.send_code_request(phone)
        return PendingCode(client.session.save(), sent.phone_code_hash)
    finally:
        await client.disconnect()       # never leak a connected client on error

async def sign_in(session_string, api_id, api_hash, phone, code, phone_code_hash) -> str:
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    try:
        try: await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
        except SessionPasswordNeededError: raise TwoFactorUnsupportedError()
        return client.session.save()
    finally:
        await client.disconnect()
```

- [ ] **Step 4:** Router: `POST /telegram/connect` → 202; `POST /telegram/verify` → `{connected: true}` (400 `TELEGRAM_CODE_INVALID` on bad code); `GET /telegram/status`. API tests use `FakeTelegramAuth` injected through `app.state.telegram_auth` (set in `create_app`, overridable in test fixture).
- [ ] **Step 5:** Port the still-valuable assertions from `test_telegram_session.py`/`test_cli_telegram.py` into the new unit tests now (the originals are deleted in Task 19). `uv run pytest tests/unit/test_telegram_link.py tests/api/test_telegram.py -v` → PASS. Commit `feat(backend): per-user telegram sessions with encrypted storage`.

### Task 8: Job registry + SSE

**Files:** Create `services/jobs/registry.py`, `api/sse.py`, `tests/unit/test_job_registry.py`, `tests/api/test_sse.py`

- [ ] **Step 1:** Failing unit tests: start runs coroutine and streams published events ending with `done`; **two concurrent subscribers each receive every event** (broadcast, not competing consumers); **a late subscriber (after completion) receives the replay: latest progress then the terminal event**; duplicate start while running raises `JobAlreadyRunningError`; failing coroutine yields terminal `error` event; finished job re-startable.
- [ ] **Step 2:** Implement — one queue **per subscriber** (requirements §7), bounded replay (latest progress + terminal only, so hours-long backfills don't accumulate history):

```python
# services/jobs/registry.py
class JobAlreadyRunningError(Exception): ...

@dataclass
class JobChannel:
    subscribers: list[asyncio.Queue]                  # one queue per stream() caller
    last_progress: tuple[str, dict] | None = None     # bounded replay state
    terminal: tuple[str, dict] | None = None
    task: asyncio.Task | None = None

class JobRegistry:
    def __init__(self): self._channels: dict[str, JobChannel] = {}

    def start(self, key: str, run: Callable[[JobPublisher], Awaitable[dict]]) -> None:
        channel = self._channels.get(key)
        if channel and channel.task and not channel.task.done(): raise JobAlreadyRunningError(key)
        channel = self._channels[key] = JobChannel(subscribers=[])
        publisher = JobPublisher(partial(self._broadcast, key))
        channel.task = asyncio.create_task(self._guard(run, publisher))

    def _broadcast(self, key: str, event: str, data: dict) -> None:
        channel = self._channels[key]
        if event == "progress": channel.last_progress = (event, data)
        else: channel.terminal = (event, data)
        for queue in channel.subscribers: queue.put_nowait((event, data))

    async def _guard(self, run, publisher):
        try: publisher.done(await run(publisher))
        except asyncio.CancelledError: publisher.error("cancelled"); raise
        except Exception as error: publisher.error(str(error))

    def cancel(self, key: str) -> None: ...           # task.cancel() if running

    async def stream(self, key: str) -> AsyncIterator[tuple[str, dict]]:
        channel = self._channels[key]                  # KeyError → 404 JOB_NOT_FOUND at router
        queue: asyncio.Queue = asyncio.Queue()
        for replay in (channel.last_progress, channel.terminal):
            if replay: queue.put_nowait(replay)
        channel.subscribers.append(queue)
        try:
            while True:
                event, data = await queue.get()
                yield event, data
                if event in ("done", "error"): return
        finally:
            channel.subscribers.remove(queue)

class JobPublisher:                                    # wraps the broadcast callable
    def progress(self, data: dict): self._emit("progress", data)
    def done(self, data: dict):     self._emit("done", data)
    def error(self, message: str):  self._emit("error", {"message": message})
```

Job key convention: `f"{user_id}:{channel_id}:{kind}"`, `kind ∈ {backfill, distill, backtest}`.
- [ ] **Step 3:** `api/sse.py`: `def sse_stream(registry, key) -> EventSourceResponse` mapping `(event, data)` → sse-starlette events with JSON-encoded data. API test: dummy router started in test app publishes 2 progress + done; client reads via `with client.stream("GET", …)`.
- [ ] **Step 4:** Replace Task 2's stub with the real `JobRegistry` in `create_app`. `uv run pytest tests/unit/test_job_registry.py tests/api/test_sse.py -v` → PASS. Commit `feat(backend): in-process job registry with sse streaming`.

### Task 9: Chats CRUD + projection

**Files:** Create `services/projection/chats.py`, `services/projection/dates.py`, `api/routers/chats.py`, `api/schemas/chat.py`, `tests/unit/test_chat_projection.py`, `tests/api/test_chats.py`

- [ ] **Step 1:** `services/projection/dates.py`: `format_long(d) -> "Nov 18, 2025"`, `format_short(d) -> "Jun 7"`, `format_time(d) -> "14:32"` (`%-d` day, no locale deps). Unit-test all three.
- [ ] **Step 2:** Failing projection tests: chat summary derives `fetched` (message count), `lastDate` (earliest `posted_at`, long format), flags from deletion evidence (SUSPECTED→`historyGaps`, CONFIRMED+`was_signal_candidate`→`signalDeletion`), score block from latest `backtest_result`, **score forced 0 when signalDeletion**, `hasRisk = status in {verified, analyzed}`, deterministic `initials`/`tint` from title hash (`var(--viz-{1..6})`).
- [ ] **Step 3:** Implement `present_chats(session, user_id) -> list[dict]` joining `user_channel` + `telegram_channel` + counts + evidence + latest backtest. One query per concern, assembled in a main `present_chats` method.
- [ ] **Step 4:** Failing API tests: GET empty → `{chats: []}`; POST `{tag}` resolves via the user's Telegram source (`app.state.telegram_source_factory(link) -> TelegramSource`; production default = `make_user_source` over the decrypted `user_telegram_link` from Task 7, tests inject a `FakeSource` factory), subscribes, 201; POST without telegram link → 409 `TELEGRAM_NOT_CONNECTED`; observer second chat → 403 `PLAN_LIMIT_SOURCES`; DELETE → 204 and gone from list, capture rows remain; **foreign user: a second registered account hitting the first account's `/chats/{id}` → 404 `CHAT_NOT_FOUND`**.
- [ ] **Step 5:** Ownership + plan guards in `api/deps.py`:

```python
def require_user_channel(chat_id: str, request: Request,
                         user: UserAccount = Depends(get_current_user)) -> UserChannelRow:
    with request.app.state.session_factory() as session:
        subscription = read_subscription(session, user.id, int(chat_id))
    if subscription is None:
        raise ApiError(404, "CHAT_NOT_FOUND", "Chat not found")   # foreign == nonexistent
    return subscription
```

Every `/chats/{id}/…` router (Tasks 10–17) takes `Depends(require_user_channel)` — no router resolves `chat_id` on its own.

```python
# services/accounts/plans.py
@dataclass(frozen=True)
class PlanLimits: sources: int | None; signals_per_month: int | None; exchanges: int | None
PLAN_LIMITS = {Plan.OBSERVER: PlanLimits(1, 200, 0),
               Plan.OPERATOR: PlanLimits(10, None, 1),
               Plan.DESK:     PlanLimits(None, None, None)}
```

`require_source_capacity(user, session)` → `ApiError(403, "PLAN_LIMIT_SOURCES", …)` when `count_subscriptions >= limit`.
- [ ] **Step 6:** `uv run pytest tests/unit/test_chat_projection.py tests/api/test_chats.py -v` → PASS. Commit `feat(backend): chat subscriptions with plan limits and projection`.

### Task 10: Backfill job + progress + auto-rescan

**Files:** Modify `services/ingestion/backfill.py` (progress callback), `services/ingestion/candidate_derivation.py` (explicit rules param), `src/verasig/cli.py` (pass rules explicitly), Create `api/routers/chats.py` additions, `tests/api/test_backfill.py`; Modify `tests/integration/test_backfill.py`, `tests/integration/test_candidate_derivation.py`

- [ ] **Step 1:** Failing service test: `backfill(..., on_batch=cb)` invokes `cb(inserted_total, oldest_posted_at)` per batch (extend existing integration test with a recording callback; default `on_batch=None` keeps old call sites green).
- [ ] **Step 2:** Add optional `on_batch: Callable[[int, datetime], None] | None` to the backfill loop.
- [ ] **Step 2b:** D16 enforcement — `derive_candidates` currently calls `read_filter_rules` internally, which would materialize user rules into global `raw_signal_event` rows. Change the signature to take rules explicitly: `derive_candidates(session_factory, channel_id, exchange, *, filter_rules: Sequence[FilterRule] = (), batch_size=200)` (drop the internal read; tuple default — never a mutable `[]`). The backfill job passes no rules (seed-only); the CLI `candidates` command reads + passes rules itself until Task 19. Adjust `test_candidate_derivation.py` call sites.
- [ ] **Step 3:** Failing API tests (FakeSource with 3 batches): POST `/chats/{id}/backfill` → 202, status `backfilling`; SSE stream yields `progress` events shaped `{fetched, lastDate, phase}` with phases cycling the six §4 strings, terminal `done`; after done status `backfilled` and **rescan ran** (FakeSource `live_message_ids` missing one captured candidate id → CONFIRMED evidence exists, chat shows `signalDeletion`); second POST while running → 409 `JOB_ALREADY_RUNNING`; `POST …/backfill/cancel` → 204, status `cancelled`, SSE terminal `error: cancelled`; foreign user POST → 404 `CHAT_NOT_FOUND`.
- [ ] **Step 4:** Job body (in `api/routers/chats.py` calling services only):

```python
async def _run_backfill(publisher, source, user_id, channel_id, session_factory, settings):
    phases = itertools.cycle(BACKFILL_PHASES)
    def on_batch(fetched, oldest):
        publisher.progress({"fetched": fetched, "lastDate": format_long(oldest), "phase": next(phases)})
    result = await backfill(source, channel_id, session_factory, settings.backfill_batch_size, on_batch=on_batch)
    await rescan(source, channel_id, session_factory)          # auto deletion sweep
    derive_candidates(session_factory, channel_id, StaticExchange())
    # no filter_rules → SEED_HEURISTIC only: candidates stay global + user-independent (D16);
    # user FilterRules apply at read time (verify samples, rule match), never materialized
    with session_factory() as session:
        set_status(session, user_id, channel_id, "backfilled")
        session.commit()
    return {"fetched": result.inserted}
```

- [ ] **Step 5:** `uv run pytest tests/api/test_backfill.py tests/integration/test_backfill.py -v` → PASS. Commit `feat(backend): backfill job with sse progress and auto-rescan`.

### Task 11: Labeling endpoints

**Files:** Create `services/labeling/service.py`, `api/routers/labels.py`, `api/schemas/message.py`, `tests/unit/test_labeling.py`, `tests/api/test_labels.py`

- [ ] **Step 1:** Failing unit tests: `labeling_sample(session, user_id, channel_id, limit)` returns candidate-event messages without a golden label, oldest first, projected to `{id, time, date, author, text, media, replyTo}` (media from `raw_payload`: photo→`image`, document→`doc`, else null; `replyTo` resolved from stored reply target, truncated to 80 chars); `record_label` upserts `golden_label` with `label` enum + `user_id`; `label_counts` returns the four counts.
- [ ] **Step 2:** Implement service; author = channel title (channels post as themselves; `sender_id` kept for groups later).
- [ ] **Step 3:** API tests: GET messages; POST label twice (re-label) keeps one row; GET counts reflects upserts; label value outside enum → 422; foreign user on all three routes → 404 `CHAT_NOT_FOUND`.
- [ ] **Step 4:** `uv run pytest tests/unit/test_labeling.py tests/api/test_labels.py -v` → PASS. Commit `feat(backend): labeling sample and golden-label endpoints`.

### Task 12: Anthropic runner + distill job + rules

**Files:** Create `foundation/anthropic_runner.py`, `services/projection/rules.py`, `api/routers/distill.py`, `api/schemas/rule.py`, `tests/unit/test_anthropic_runner.py`, `tests/api/test_distill.py`; Modify `services/extraction/llm_fallback.py`, `services/distillation/rule_distiller.py`, `src/verasig/cli.py` (rewire call sites — CLI lives until Task 19), affected unit tests

- [ ] **Step 1:** Failing runner test (mock `anthropic.Anthropic`): runner concatenates text blocks; passes model + max_tokens.

```python
# foundation/anthropic_runner.py
def make_anthropic_runner(api_key: str, model: str) -> Callable[[str], str]:
    client = anthropic.Anthropic(api_key=api_key)
    def run(prompt: str) -> str:
        message = client.messages.create(model=model, max_tokens=4096,
                                         messages=[{"role": "user", "content": prompt}])
        return "".join(block.text for block in message.content if block.type == "text")
    return run
```

- [ ] **Step 2:** Remove `_subprocess_runner` from `llm_fallback.py` + `rule_distiller.py`; rename `ClaudeCliExtractor → AnthropicExtractor`, `ClaudeCliDistiller → AnthropicDistiller`; constructor takes `runner: Callable[[str], str]` (required — wiring injects `make_anthropic_runner(...)`). Canned-runner unit tests only change class names. Rewire `cli.py` `_resolve_fallback` (and any distiller construction) to inject `make_anthropic_runner(settings.anthropic_api_key, settings.anthropic_model)` so CLI commands and their tests stay green until Task 19.
- [ ] **Step 3:** Extend `_filter_prompt` to request per-pattern `display: {label, detail}` in the JSON; `parse_distiller_output` carries it into `FilterRule.display` (new optional field, default `[]`); persist via `filter_rule.display` JSONB. `parse_distiller_output` also gains `user_id: UUID | None` and stamps the user-scoped `rule_id`s from Task 3 (`f"{user_id}:{channel_id}-filter-v{version}"`); CLI passes `None` → legacy stamp unchanged.
- [ ] **Step 4:** `services/projection/rules.py`: `present_rules(session, user_id, channel_id)` → per include-pattern `{id, label, detail, match}` where `match` = share of golden `signal` labels whose text matches that single pattern (reuse `apply_filter_rule` with a one-pattern rule).
- [ ] **Step 5:** API tests (FakeDistiller via `app.state.distiller_factory`): POST distill with < 5 signal labels → 409 `LABELS_INSUFFICIENT`; with ≥ 5 → 202, SSE emits the five §4 phase strings around real work (phases 1–4 before/after corpus read + distill calls, phase 5 before persist), `done`; GET `/chats/{id}/rules` returns display rules with computed match.
- [ ] **Step 6:** `uv run pytest tests/unit -k "anthropic or distiller or llm" tests/api/test_distill.py -v` → PASS. Commit `feat(backend): anthropic sdk runner and distill job with rule display`.

### Task 13: Verify endpoints

**Files:** Create `services/verification/service.py`, `api/routers/verify.py`, `api/schemas/verify.py`, `tests/unit/test_verification.py`, `tests/api/test_verify.py`

- [ ] **Step 1:** Failing unit tests: `verification_samples` = up to 20 unlabeled candidate messages + `predicted` from the user's current `FilterRule` (`signal`/`noise`); `apply_verdicts` with a `wrong` verdict writes a corrected `golden_label` (prediction flipped) and a `FilterDriftWarning(miss_discovered_by=HUMAN_AUDIT)` when a predicted-noise was flagged wrong, bumps `verify_attempt`, returns `(False, [ids])`; all-correct returns `(True, [])` and sets status `verified`; fewer than 6 verdicts raises `TooFewVerdictsError`.
- [ ] **Step 2:** Implement service with micro-steps `predict_sample`, `flip_wrong_predictions_into_labels`, `emit_drift_for_missed_signals`, `decide_pass`.
- [ ] **Step 3:** API tests: GET samples carries `attempt`; POST mixed verdicts → `{passed: false, misclassified: […]}`; follow-up all-correct POST → `{passed: true}` and chat status `verified`; 5 verdicts → 400 `VERIFY_TOO_FEW_VERDICTS`; foreign user → 404 `CHAT_NOT_FOUND`.
- [ ] **Step 4:** `uv run pytest tests/unit/test_verification.py tests/api/test_verify.py -v` → PASS. Commit `feat(backend): verify step with human-audit feedback loop`.

### Task 14: Exchanges

**Files:** Create `foundation/bybit_account.py`, `services/exchanges/catalog.py`, `services/exchanges/service.py`, `api/routers/exchanges.py`, `api/schemas/exchange.py`, `tests/unit/test_bybit_account.py`, `tests/api/test_exchanges.py`

- [ ] **Step 1:** Failing unit test for HMAC verifier (httpx `MockTransport`): correct signature headers (`X-BAPI-API-KEY`, `X-BAPI-TIMESTAMP`, `X-BAPI-RECV-WINDOW`, `X-BAPI-SIGN` = HMAC-SHA256 of `timestamp+key+recv_window` over the secret) on `GET https://api.bybit.com/v5/user/query-api`; `retCode == 0` → valid; non-zero → `KeyVerificationError`.
- [ ] **Step 2:** Implement `async verify_api_keys(api_key, api_secret, transport=None) -> None`.
- [ ] **Step 3:** `catalog.py` = static list mirroring frontend seed (bybit `available`, kind `Derivatives · Spot`, brand/tint/initials; others `soon`). Service: `connect` (verify → mask `f"{key[:4]}…{key[-2:]} · trade-only"` → encrypt+store), `disconnect`, `present_exchanges` (catalog ⨝ user connections).
- [ ] **Step 4:** API tests (fake verifier via `app.state.exchange_verifier`): GET catalog shows `connected: false`; observer connect → 403 `PLAN_LIMIT_EXCHANGES`; operator connect → connected + masked account, secret absent from response and stored encrypted (assert ciphertext ≠ plaintext in DB); bad keys → 400 `EXCHANGE_KEYS_INVALID`; disconnect flips flag.
- [ ] **Step 5:** `uv run pytest tests/unit/test_bybit_account.py tests/api/test_exchanges.py -v` → PASS. Commit `feat(backend): bybit key verification and exchange connections`.

### Task 15: Risk config endpoints

**Files:** Create `api/routers/risk.py`, `api/schemas/risk.py`, `tests/api/test_risk.py`

- [ ] **Step 1:** Failing tests: GET without stored config → defaults from `RiskConfig()`; PUT persists and echoes; `levels` outside 2–5 / unknown `entryMode` → 422; foreign user GET/PUT → 404 `CHAT_NOT_FOUND`.
- [ ] **Step 2:** Schema validates enums + `levels: int = Field(ge=2, le=5)`; router delegates to `risk_repository`.
- [ ] **Step 3:** `uv run pytest tests/api/test_risk.py -v` → PASS. Commit `feat(backend): chat risk config endpoints`.

### Task 16: Risk-config execution policy

**Files:** Create `services/scoring/risk_policy.py`, `tests/unit/test_risk_policy.py`; Modify `services/scoring/policies.py` (extract shared helpers)

`ProviderStatedPolicy` only simulates provider-stated entry/stop/first-TP — it cannot express entry modes, laddering, custom exits, or leverage. The RiskConfig semantics need their own `ExecutionPolicy`.

- [ ] **Step 1:** Failing unit tests over hand-built klines, one behavior each:
  - `entry_mode=first`: fills the full position at the near edge of the entry range on first touch
  - `entry_mode=mid`: fills at the range midpoint when price trades through it
  - `entry_mode=ladder` + `weighting=equal`: `levels` evenly spaced across the range; average entry = mean of **filled** levels (untouched levels never fill)
  - `weighting=martingale`: level weights double down the ladder (1, 2, 4 …); average entry is weight-adjusted
  - `exit_source=signal`: provider-stated stop/first-TP (same semantics as `ProviderStatedPolicy`)
  - `exit_source=custom`: stop = avg_entry × (1 ∓ stop_pct/100), tp = avg_entry × (1 ± tp_pct/100) (sign by side)
  - **every filled outcome sets `pct_return`**, already scaled by `leverage` × `risk_pct` position sizing (R_MULTIPLE outcomes carry both `r_multiple` and the sized `pct_return` — downstream PnL compounds `pct_return` only, Task 17); no level touched → `UNFILLED`
  - same-candle stop+target tie resolves **stop-first** (conservative, ADR 0003 / existing `TIE_BREAK`)
- [ ] **Step 2:** Implement `RiskConfigPolicy(ExecutionPolicy)` with `__init__(config: RiskConfig)`; micro-steps `_entry_levels`, `_filled_levels`, `_average_entry`, `_exit_prices`, `_outcome`. Extract the shared candle helpers (`_touches_stop`, `_touches_target`, `_mfe`, `_mae`, `_risk`) from `policies.py` for reuse — do not duplicate them.
- [ ] **Step 3:** `uv run pytest tests/unit/test_risk_policy.py tests/unit/test_simulation_policy.py -v` → PASS (existing policy tests untouched). Commit `feat(backend): risk-config execution policy`.

### Task 17: Backtest job

**Files:** Create `services/backtesting/service.py`, `api/routers/backtest.py`, `api/schemas/backtest.py`, `tests/unit/test_backtesting.py`, `tests/api/test_backtest.py`

- [ ] **Step 1:** Failing unit test with fixture klines (`tests/fixtures/klines/`) + seeded extracted signals: `run_backtest(session_factory, user_id, channel_id, market_data, risk_config, now)` extracts candidates if missing (user-scoped outcomes, Task 3) → folds → simulates each folded signal under `RiskConfigPolicy(risk_config)` (Task 16) → `build_provider_score` → returns `BacktestSummary(score: int, win_rate: float, pnl: float, outcomes: list[SimOutcome])` and persists `backtest_result` **including per-signal `outcomes` JSONB** (`[{rootSignalId, kind, rMultiple, pctReturn, exitReason}]` — requirements D15; /signals reads these instead of refetching klines) + status `analyzed`.
- [ ] **Step 2:** Implement with micro-steps `load_folded_signals`, `simulate_outcomes`, `compose_score`, `persist_result`. `win_rate` = wins/tested × 100 (1 dp); `pnl` = (∏(1 + pct_return/100) − 1) × 100 over tested outcomes — compounds `SimOutcome.pct_return` directly (leverage × risk sizing already applied by `RiskConfigPolicy`, Task 16; never re-derive from `r_multiple`).
- [ ] **Step 3:** API tests (market data faked via `app.state.market_data_factory`): POST → 202; SSE: four §4 phase strings (emitted before load / simulate / score / persist) then `done: {score, winRate, pnl}`; chat now `analyzed` with metrics; stored `backtest_result.outcomes` carries one entry per folded signal; chat with `signalDeletion` projects score 0 regardless of stored result; foreign user POST → 404 `CHAT_NOT_FOUND`.
- [ ] **Step 4:** `uv run pytest tests/unit/test_backtesting.py tests/api/test_backtest.py -v` → PASS. Commit `feat(backend): backtest job producing provider score`.

### Task 18: Signals view + orphan mod linking

**Files:** Create `services/projection/signals.py`, `api/routers/signals.py`, `api/schemas/signal.py`, `tests/unit/test_signal_projection.py`, `tests/api/test_signals.py`; Modify `services/lifecycle/fold.py` (accept manual links)

- [ ] **Step 1:** Failing fold test: `fold(signals, events, messages, manual_links={message_id: root_signal_id})` treats a manually linked message as part of that signal's chain (same as a `reply_to` hit); existing calls unchanged via default `manual_links=None`.
- [ ] **Step 2:** Failing projection tests covering the full Signal shape (requirements §4): root NEW_ENTRY signals → rows; `mods[]` from timeline steps (kind via `classify_patch` mapping: breakeven/stop→`move_stop`, add→`avg_down|avg_up` by price vs entry, reduce→`partial`, close→`close`), `via = reply` when `reply_to` evidence else `inferred` (manual link); `effective{}` from final timeline step (avg entry + note `"avg of N fills"`, moved stop + note, closedBy `author`, effective pnl from the stored outcome); `status/outcome/pnl` from the latest `backtest_result.outcomes` per channel (no kline refetch on read — requirements D15; no backtest yet → all `untested`); `deleted` from evidence; orphan mods = modifier-labeled messages with no linkage, `suggestId` = latest open same-symbol signal; observer truncation to 200/month + `limitReached`.
- [ ] **Step 3:** Implement `present_signals(session, user_id, feed_id=None, status=None, plan=…)` assembling per-channel folds across the user's subscriptions; `present_signal(session, user_id, signal_id)`.
- [ ] **Step 4:** API tests: GET list + filters; GET detail; POST `/signals/{id}/link-mod {modId}` writes `lifecycle_link`, response now contains the mod with `via: "inferred"`; unknown ids → 404; **foreign user: another account's signal id on GET detail / link-mod → 404** (signals resolve only within the requester's subscriptions).
- [ ] **Step 5:** `uv run pytest tests/unit/test_signal_projection.py tests/api/test_signals.py -v` → PASS. Commit `feat(backend): signals projection with manual mod linking`.

### Task 19: Teardown — delete CLI, ship runtime

**Files:** Delete `src/verasig/cli.py`, `tests/integration/test_cli_*.py`, `tests/unit/test_cli_telegram.py`, `tests/unit/test_telegram_session.py`, `tests/unit/test_deletions_format.py`, `tests/unit/test_lifecycle_format.py` (CLI formatting); Modify `pyproject.toml`, `src/verasig/config.py`, `foundation/telegram_session.py`, `src/verasig/api/app.py`, `Makefile`, `Dockerfile`, `../../docker-compose.yml` (repo root), `README.md`, `tests/unit/test_config.py`, `tests/integration/test_migrations.py`

- [ ] **Step 1:** Audit each to-be-deleted CLI test for unique coverage; port anything not already covered by Tasks 9–18 API tests into the matching `tests/api/` module (known: `test_cli_score.py` traceability assertions → extend `test_backtest.py`; `test_migrations.py` drops `CliRunner` and calls `alembic.command.upgrade` directly).
- [ ] **Step 2:** Delete `cli.py` + CLI tests; `uv remove typer` and delete `[project.scripts]` from `pyproject.toml`; remove the legacy global-session helpers from `foundation/telegram_session.py` (`load_session_string`, `save_session_string`, `make_client(settings)`, `run_login`) — only the Task 7 per-user functions remain; delete CLI-era `Settings` fields (`session_path`, `telegram_api_id/hash/phone`, `distiller_command`, `extractor_command`) and fix `test_config.py`; drop the `user_id=None` branches the transitional CLI writes needed (repos now require a real user id). `make format && make lint` clean.
- [ ] **Step 3:** Add module-level `def create_app_from_env() -> FastAPI` in `api/app.py` (reads `Settings()`, calls `create_app`). Makefile: replace `cli` target with `serve` = `uv run uvicorn verasig.api.app:create_app_from_env --factory --reload`; `migrate` → `uv run alembic upgrade head`; `health` → `curl -fsS localhost:8000/health`.
- [ ] **Step 4:** Dockerfile `ENTRYPOINT ["uv", "run", "--no-sync", "uvicorn", "verasig.api.app:create_app_from_env", "--factory", "--host", "0.0.0.0", "--port", "8000"]`. Root `docker-compose.yml`: **remove `command: ["health"]`** (it would override the new entrypoint), add `ports: ["8000:8000"]`, remove the `tgsession` named volume + `/session` mount (sessions live in the DB now; keep the `secrets` mount). Update README (run, env, API summary table linking requirements.md).
- [ ] **Step 5:** Full suite: `make test` → all green; `make lint` clean; `docker compose up --build` serves `/health` on :8000. Commit `refactor(backend)!: remove cli delivery layer, serve fastapi`.

### Task 20: Final review gate

- [ ] **Step 1:** Sweep requirements.md §4 endpoint-by-endpoint against routers; §5 table-by-table against `models.py`; §6 limits against guards. Fix gaps.
- [ ] **Step 2:** `make test && make lint` → green. Request code review (superpowers:requesting-code-review if available), then finish the branch per repo flow: squash broken commits, merge to `develop` (superpowers:finishing-a-development-branch if available).

---

## Task dependency order

```
1 → 2 → 3 → 4 → 5 → 6
              5 → 7 → 9 → 10 → 11 → 12 → 13
              5 → 8 ─┘                  (8 before 10: backfill job needs registry)
              5 → 14                    (exchanges)
              5 → 15 → 16 → 17          (risk endpoints → risk policy → backtest job)
              10, 11, 17 → 18           (signals projection reads capture, labels, outcomes)
              all → 19 → 20
```

Parallelizable after Task 5: {6}, {7+9+10…13}, {8}, {14}, {15+16}.
