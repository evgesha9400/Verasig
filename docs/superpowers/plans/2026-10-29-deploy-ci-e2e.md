# Deploy, CI/CD, and E2E Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve the current app at `https://verasig.io` from the mac-server, deployed from `main`, with CI on every pull request.

**Architecture:** One image holds the backend and the built web app. One uvicorn process serves the API at `/api` and the web app at `/`, and runs migrations before it starts. The mac-server platform (`serverctl`) runs it with Postgres in one Compose project on loopback port `18093`. The Cloudflare Tunnel routes `verasig.io` to that port. GitHub Actions runs `make check` and E2E on pull requests. On `main` it pushes the image to GHCR, asks the mac-server to deploy that digest over Tailscale SSH, and runs `@smoke` E2E against the live site.

**Tech Stack:** GitHub Actions, Docker, FastAPI/Starlette, pydantic-settings, Alembic, Vite, Playwright, mac-server `serverctl`, Tailscale, Cloudflare Tunnel.

**Spec:** `docs/superpowers/specs/2026-10-29-deploy-ci-e2e-design.md` (parent: `2026-10-29-launch-architecture-design.md`).

## Global Constraints

- Branch off `develop` (`feat/deploy-ci-e2e`); conventional commits; no attribution lines; push only when the user says so.
- mac-server repo (`~/projects/97-support/mac-server`, `evgesha9400/mac-server`): PR only, rebase merge; never edit `~/server-admin` on the host.
- Image: `ghcr.io/evgesha9400/verasig`, `linux/amd64`, label `org.opencontainers.image.source=https://github.com/evgesha9400/Verasig`.
- Service `verasig`, environment `production`, port `18093`, health `http://127.0.0.1:18093/api/health`.
- Secret file names: `jwt_secret`, `secret_keys`, `postgres_password`. Never print their values.
- Production: `VERASIG_ENV=production`; `VERASIG_CORS_ORIGINS='["https://verasig.io"]'`.
- Live-site specs are read-only and never register users.
- Test artifacts and scratch output go in the session scratchpad, never the repo.

## Review Focus

1. A deep link such as `/app` on a fresh load returns `index.html`, while an unknown `/api/...` path still returns the API's JSON 404, not `index.html`. Pinned in Task 2.
2. A failed migration leaves the previous image running: the start script exits non-zero before uvicorn, so the container never turns healthy and `serverctl` rolls back. Pinned in Task 3, Step 4.
3. Health-check access lines stay quiet: the filter matches `HEALTH_PATH = "/health"`, but under the mount the logged path may be `/api/health`. Pinned in Task 2.
4. `?token=` stays redacted under the mount (existing filter). Pinned in Task 2.
5. SSE through Cloudflare: one progress route returns `text/event-stream` through `https://verasig.io` (status and header only; a real stream is checked in project 4). Pinned in Task 7, Step 7.

---

### Task 1: Production refuses development secrets

**Files:**
- Modify: `apps/backend/src/verasig/config.py` (`secret_key_spec`, `database_url`)
- Test: `apps/backend/tests/foundation/test_config.py`

**Interfaces:**
- Produces: `Settings.secret_key_spec() -> str` raises `SettingsError` when `env != "local"` and any keyring entry's base64 key decodes to 32 zero bytes. `Settings.database_url` raises `SettingsError` when `env != "local"`, there is no `database_url_override`, and `db_password == "verasig"`. Alembic (`migrations/env.py:29`) reads `database_url`, so migrations are covered too.

- [ ] **Step 1: Write the failing tests** (reuse the file's `isolate_settings_environment` fixture)

```python
DEV_KEYRING = "dev:" + base64.b64encode(bytes(32)).decode()

def test_secret_key_spec_rejects_dev_keyring_outside_local():
    with pytest.raises(SettingsError, match="VERASIG_SECRET_KEYS"):
        Settings(_env_file=None, env="production", secret_keys=DEV_KEYRING).secret_key_spec()

def test_secret_key_spec_rejects_dev_key_anywhere_in_keyring():
    real = "k2:" + base64.b64encode(b"\x01" * 32).decode()
    with pytest.raises(SettingsError):
        Settings(_env_file=None, env="production", secret_keys=f"{real},{DEV_KEYRING}").secret_key_spec()

def test_secret_key_spec_accepts_dev_keyring_locally():
    assert Settings(_env_file=None, secret_keys=DEV_KEYRING).secret_key_spec() == DEV_KEYRING

def test_database_url_rejects_default_password_outside_local():
    with pytest.raises(SettingsError, match="VERASIG_DB_PASSWORD"):
        Settings(_env_file=None, env="production").database_url

def test_database_url_allows_override_outside_local():
    s = Settings(_env_file=None, env="production", database_url_override="postgresql+psycopg://u:p@h/d")
    assert s.database_url == "postgresql+psycopg://u:p@h/d"
```

- [ ] **Step 2: Run** `cd apps/backend && uv run pytest tests/foundation/test_config.py -v`: expect the 3 rejection tests to FAIL.
- [ ] **Step 3: Implement** both checks in `config.py` through one private helper `_is_local() -> bool` that reuses `jwt_secret_spec`'s normalisation (`self.env.strip().lower() or "local"`). A keyring entry that fails to decode is left for `SecretCipher.from_spec` to reject, as today.
- [ ] **Step 4: Run** `make backend-test backend-lint backend-format-check` from the repo root: expect PASS.
- [ ] **Step 5: Commit** `fix(backend): reject dev keyring and default db password outside local`

---

### Task 2: Site entrypoint (API at `/api`, web app at `/`)

**Files:**
- Create: `apps/backend/src/verasig/entrypoints/site.py`
- Modify: `apps/backend/src/verasig/config.py` (field `web_dist_dir: Path | None = None`, env `VERASIG_WEB_DIST_DIR`)
- Modify: `apps/backend/src/verasig/foundation/http/access_logging.py` only if the health test below fails
- Test: `apps/backend/tests/entrypoints/test_site.py`

**Interfaces:**
- Consumes: `create_app(settings, session_factory=None) -> FastAPI` from `entrypoints/api.py`.
- Produces: `create_site(settings: Settings, session_factory: sessionmaker | None = None) -> Starlette` and `create_site_from_env() -> Starlette`. Requires `settings.web_dist_dir` (raise `SettingsError` if unset or missing `index.html`). Mount order: `/api` → API app, then `/` → static files with an `index.html` fallback for paths that match no file.

- [ ] **Step 1: Write the failing tests** with a `tmp_path` dist (`index.html` containing `<div id="root"></div>`, `assets/app.js`), the existing test session factory, and `TestClient`:
  - `test_api_is_served_under_api_prefix`: `GET /api/health` → 200.
  - `test_static_asset_is_served`: `GET /assets/app.js` → 200, body equals the file.
  - `test_deep_link_returns_index`: `GET /app` and `GET /app/feeds/x` → 200, body contains `<div id="root">`.
  - `test_unknown_api_path_is_not_index`: `GET /api/no-such-route` → 404, JSON body, no `<div id="root">`.
  - `test_site_requires_web_dist_dir`: `create_site(Settings(_env_file=None, web_dist_dir=None))` raises `SettingsError`.
  - `test_health_access_line_is_debug_under_mount` and `test_token_query_redacted_under_mount`: build a `LogRecord` as uvicorn would for path `/api/health` and `/api/feeds/x/backfill/progress?token=abc`, pass it through `HealthCheckAccessLogFilter`; expect level DEBUG for the first and no `abc` in the second.
- [ ] **Step 2: Run** `uv run pytest tests/entrypoints/test_site.py -v`: expect FAIL (module missing).
- [ ] **Step 3: Implement** `site.py` with `starlette.routing.Mount` and a `StaticFiles(directory=..., html=True)` subclass whose `get_response` falls back to `index.html` on a 404. Make the health filter match a path that ends with `/health` if its test fails.
- [ ] **Step 4: Run** `make backend-test backend-lint backend-format-check`: expect PASS.
- [ ] **Step 5: Commit** `feat(backend): serve api under /api and the web app from one site entrypoint`

---

### Task 3: Site image and local site service

**Files:**
- Create: `Dockerfile.site` (repo root; build context is the repo root), `.dockerignore` entries for `**/node_modules`, `**/dist`, `apps/frontend/web/e2e/.env`, `apps/frontend/web/e2e/.auth`, `**/test-results`, `**/playwright-report`, `apps/backend/.env`
- Create: `apps/backend/scripts/start-site.sh`
- Modify: root `docker-compose.yml` (service `site`, profile `site`)

**Interfaces:**
- Consumes: Task 2 `create_site_from_env`.
- Produces: image that listens on `8000`, reads `VERASIG_*_FILE` variables, migrates, then serves. Root compose: `docker compose --profile site up -d --wait site` serves on `http://localhost:8080`.

- [ ] **Step 1: Write `start-site.sh`** (`#!/bin/sh`, `set -eu`): for each of `VERASIG_JWT_SECRET`, `VERASIG_SECRET_KEYS`, `VERASIG_DB_PASSWORD`, if `<NAME>_FILE` is set, export `<NAME>` from that file; then `uv run --no-sync alembic upgrade head`; then `exec uv run --no-sync uvicorn verasig.entrypoints.site:create_site_from_env --factory --host 0.0.0.0 --port 8000`. Never echo values.
- [ ] **Step 2: Write `Dockerfile.site`**: stage `web` from `node:22-slim`: copy `apps/frontend`, `npm ci`, `VITE_VERASIG_API_URL=/api npm run build --workspace verasig-web`. Stage 2 copies the backend `Dockerfile`'s two `uv sync` layers (same `uv==0.9.17`), copies `web/dist` to `/app/web`, sets `VERASIG_WEB_DIST_DIR=/app/web`, `LABEL org.opencontainers.image.source=https://github.com/evgesha9400/Verasig`, `ENTRYPOINT ["/app/scripts/start-site.sh"]`. The container must run with a read-only root filesystem and `/tmp` as tmpfs (the platform sets both); check `uv run --no-sync` writes nothing outside `/tmp` (set `UV_CACHE_DIR=/tmp/uv` if it does).
- [ ] **Step 3: Add compose service `site`** (profile `site`): build `Dockerfile.site`, `depends_on: db: service_healthy`, the same `VERASIG_DB_*` and secret env as `app`, `VERASIG_ENV=local`, ports `8080:8000`, healthcheck with Python `urllib` on `/api/health`, `read_only: true`, `tmpfs: /tmp`.
- [ ] **Step 4: Verify locally**:
  - `docker compose --profile site up -d --wait site` succeeds; `curl -fsS localhost:8080/api/health` → 200; `curl -s localhost:8080/app | grep -c 'id="root"'` → `1`.
  - Failed migration stops the start: run the image once with `VERASIG_DB_PASSWORD=wrong` → container exits non-zero, and the logs show no uvicorn start line.
  - Guard: run with `VERASIG_ENV=production` and the dev keyring → exits non-zero with `VERASIG_SECRET_KEYS` in the log.
  - `docker build --platform linux/amd64 -f Dockerfile.site .` succeeds.
- [ ] **Step 5: Tear down** `docker compose --profile site down` (keep the dev DB volume).
- [ ] **Step 6: Commit** `feat(deploy): add single site image with migrate-then-serve start`

---

### Task 4: E2E harness for CI and live site

**Files:**
- Modify: `apps/frontend/web/e2e/auth.setup.js` (register mode)
- Modify: `apps/frontend/web/e2e/feeds.spec.js` (tag the session test `@smoke`)
- Create: `apps/frontend/web/e2e/landing.spec.js`, `apps/frontend/web/e2e/signup.spec.js`
- Modify: `apps/frontend/web/e2e/.env.example` (document `E2E_REGISTER`)

**Interfaces:**
- Produces: `E2E_REGISTER=1` makes setup `POST ${E2E_API_URL}/auth/register` with a unique email (`e2e-<Date.now()>@example.test`, random 24-char password, `first_name: 'E2E'`, `last_name: 'Runner'`) and use the returned `token`; otherwise setup logs in with `E2E_EMAIL`/`E2E_PASSWORD` as today. `--grep @smoke` selects the live-site specs.

- [ ] **Step 1: Write the specs**
  - `landing.spec.js`, `test('landing page loads @smoke')`: `goto('/')`; `getByRole('heading', { level: 1 })` contains `Verify the signal`; a `link` named `/sign up/i` has `href` `/signup`.
  - `landing.spec.js`, `test('deep link loads the web app @smoke')`: `goto('/app')` responds 200 and `#root` is attached.
  - `signup.spec.js`, `test.use({ storageState: { cookies: [], origins: [] } })`, `test('sign-up form creates an account and opens the app')`: `goto('/signup')`; fill `/full name/i` = `E2E Runner`, `/email/i` = unique email, `/password/i` = random; click `Create account`; expect URL `/app` and `getByRole('button', { name: /sources/i })` visible. No `@smoke` tag.
  - `feeds.spec.js`: rename the first test to `'reuses the session and reaches the app without a login form @smoke'`.
- [ ] **Step 2: Run against the site service** (Task 3): `E2E_REGISTER=1 E2E_BASE_URL=http://localhost:8080 E2E_API_URL=http://localhost:8080/api npm run e2e` → landing, deep link, signup, session PASS; the feed-row test SKIPS.
- [ ] **Step 3: Run smoke selection** with the local `e2e/.env` account against `make dev`: `npm run e2e -- --grep @smoke` → 3 PASS plus setup.
- [ ] **Step 4: Commit** `test(e2e): add register mode, landing, deep-link and signup specs, smoke tags`

---

### Task 5: CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: `make check`; root compose `site` profile; Task 4's `E2E_REGISTER`.

- [ ] **Step 1: Write `ci.yml`**: triggers `pull_request` and `push` on `develop`, `main`; `permissions: contents: read`; `concurrency` per ref with cancel-in-progress.
  - Job `check` (`ubuntu-latest`): `actions/checkout@v4`, `actions/setup-node@v4` (node 22, npm cache on `apps/frontend/package-lock.json`), `astral-sh/setup-uv@v6` (uv 0.9.17, Python 3.12), `make install`, `make check`.
  - Job `e2e` (needs `check`): `make env`; `docker compose --profile site up -d --wait site`; `npx playwright install --with-deps chromium` in `apps/frontend/web`; `npm run e2e` with `E2E_REGISTER=1`, `CI=1`, `E2E_BASE_URL=http://localhost:8080`, `E2E_API_URL=http://localhost:8080/api`. Upload `playwright-report` on failure.
- [ ] **Step 2: Lint** `docker run --rm -v "$PWD":/repo -w /repo rhysd/actionlint:latest` → no output.
- [ ] **Step 3: Commit** `ci: add check and e2e workflow`

---

### Task 6: mac-server onboarding pull request

Work in `~/projects/97-support/mac-server` on branch `feat/verasig-service`. Copy shapes from `services/mediancode-app/` (database + app) and `services/winnow-post/README.md`.

**Files (mac-server repo):**
- Modify: `service-catalog.json` (service `verasig`)
- Create: `services/verasig/compose.yml`, `services/verasig/README.md`, `services/verasig/config/production.env.example`
- Modify: `services/cloudflared/config.yml` (route above the 404 fallback), `CHANGES.md`, `ROLLBACK.md`

**Interfaces:**
- Consumes: Task 3 image contract (port `8000`, `/api/health`, `VERASIG_*_FILE`).
- Produces: catalog entry with `image.environment_variable: APP_IMAGE`, `repository: ghcr.io/evgesha9400/verasig`, `source_label: https://github.com/evgesha9400/Verasig`, `configuration_file: config.env`, secrets `jwt_secret`, `secret_keys`, `postgres_password` (mode `640`, group `staff`), environment `production` (`compose_project: verasig-production`, `variables: {DEPLOY_ENVIRONMENT: production, APP_PORT: "18093"}`, `health_urls: ["http://127.0.0.1:18093/api/health"]`, watchdog `running` / `automatic` / `["app"]`).

- [ ] **Step 1: Write `compose.yml`**: `db` from `postgres:16-alpine` pinned by digest (read it with `docker buildx imagetools inspect postgres:16-alpine`; 16 matches the local dev DB), `POSTGRES_PASSWORD_FILE`, named volume `verasig-${DEPLOY_ENVIRONMENT}-postgres-data`, `pg_isready` healthcheck, `cpus: 0.5`, `mem_limit: 512m`, `pids_limit: 256`. `app` from `${APP_IMAGE:?}`, `env_file: ${CONFIG_FILE:?}`, `VERASIG_DB_HOST=db`, `VERASIG_*_FILE=/run/secrets/<name>`, port `127.0.0.1:${APP_PORT:?}:8000`, Python `urllib` healthcheck on `/api/health` with `start_period: 60s` (migrations run first), `read_only: true`, `tmpfs /tmp`, `cap_drop: ALL`, `no-new-privileges`, `cpus: 2.0`, `mem_limit: 2g`, `pids_limit: 256`. Both `restart: unless-stopped`, labels `com.verasig.environment` and `com.verasig.role`, one network `verasig-${DEPLOY_ENVIRONMENT}`.
- [ ] **Step 2: Write `production.env.example`** (names only): `VERASIG_ENV=production`, `VERASIG_DB_NAME`, `VERASIG_DB_USER`, `VERASIG_CORS_ORIGINS='["https://verasig.io"]'`.
- [ ] **Step 3: Add the tunnel route** `- hostname: verasig.io` / `service: http://127.0.0.1:18093` above `http_status:404`.
- [ ] **Step 4: Write README, CHANGES and ROLLBACK entries** per `SERVICE_ONBOARDING.md` items 3 to 5. ROLLBACK covers stopping without deleting the volume, removing the tunnel route and DNS record, and revoking the deploy key (cite `DEPLOY_REPO_ONBOARDING.md`).
- [ ] **Step 5: Validate** `scripts/serverctl catalog validate` and `scripts/rehearse-server-watchdog.sh` (run where the repo's README says they run; ask before running anything on the host).
- [ ] **Step 6: Commit** `feat(verasig): onboard verasig service and tunnel route`. The PR description carries the operator runbook (Task 7 Steps 2 to 5). Open the PR only after the user approves.

---

### Task 7: Deploy workflow and go-live (ask the user before each step)

**Files (Verasig repo):**
- Create: `.github/workflows/deploy.yml`

- [ ] **Step 1: Write `deploy.yml`** from `winnow-post/.github/workflows/release.yml`: on push to `main`; `concurrency: deploy` (no cancel). Job `build_and_push` (`packages: write`): build `Dockerfile.site` for `linux/amd64`, push `ghcr.io/evgesha9400/verasig:${{ github.sha }}`, output the digest. Job `deploy` (`id-token: write`, `if: vars.ENABLE_MAC_SERVER_DEPLOY == 'true'`): `tailscale/github-action` pinned by SHA as in winnow-post, pinned `known_hosts` from `vars.MAC_SERVER_SSH_KNOWN_HOSTS` with `StrictHostKeyChecking yes`, then `ssh … "deploy production ghcr.io/evgesha9400/verasig@${DIGEST}"`. Job `smoke` (needs `deploy`): `npm run e2e -- --grep @smoke` with `E2E_BASE_URL=https://verasig.io`, `E2E_API_URL=https://verasig.io/api`, `E2E_EMAIL`/`E2E_PASSWORD` from `SMOKE_*`. Lint with actionlint. Commit `ci: add deploy workflow for mac-server`.
- [ ] **Step 2:** User approves the push; PR `feat/deploy-ci-e2e` → `develop` passes CI.
- [ ] **Step 3:** User approves; open and merge the mac-server PR (rebase). Its Apply workflow runs.
- [ ] **Step 4:** On the host, the operator (user, or me with approval) sets `jwt_secret`, `secret_keys`, `postgres_password` with `serverctl secret set` and the config with `serverctl config set`. The user stores `secret_keys` in their password manager.
- [ ] **Step 5:** Ingress: reinstall the tunnel config (`install-cloudflared-service.sh` per `services/cloudflared/README.md`, needs sudo, so the user runs it) and create the proxied DNS record `verasig.io` → `<tunnel-id>.cfargotunnel.com` (API if the token can write DNS, else the dashboard).
- [ ] **Step 6:** Run `scripts/onboard-deploy-repo.sh onboard evgesha9400/Verasig verasig production --deploy-host 100.107.191.2` (needs the user's `TS_BOOTSTRAP_*` credentials); set `MAC_SERVER_SSH_KNOWN_HOSTS` and `ENABLE_MAC_SERVER_DEPLOY=true`.
- [ ] **Step 7:** Merge `develop` → `main` with a `Merge: …` commit. Make the GHCR package public if the host pull fails, then re-run. Check the deploy job ran, not only the run. Create the smoke account at `https://verasig.io/signup`, set `SMOKE_*`, re-run. SSE check: `curl -sN -o /dev/null -w '%{http_code} %{content_type}' "https://verasig.io/api/<a progress route>?token=<smoke token>"` with `--max-time 5` → `200 text/event-stream` (any route the smoke account can open; a 404 for no feed is recorded and deferred to project 4).
- [ ] **Step 8: Done check** against spec section 1: open `https://verasig.io` in the browser (landing, sign up, app), `curl https://verasig.io/api/health`, `serverctl status verasig production` and `serverctl verify verasig production` pass, workflows green. Close the browser.
