# Project 1: deploy, CI/CD, and the E2E harness

Date: 2026-10-29. Revised 2026-10-30 for the mac-server and `verasig.io`.
Status: revision approved by the user 2026-10-30.
Parent: `2026-10-29-launch-architecture-design.md` (project 1 of 7).

## 1. Goal

Put the current app on `https://verasig.io`, deployed automatically from `main`,
with CI on every pull request. Later projects ship through this path and add their
own E2E steps.

Done means:

1. `https://verasig.io` serves the web app, and `https://verasig.io/api/*` serves the API.
2. A pull request to `develop` or `main` runs `make check` and the CI E2E suite.
3. A merge to `main` builds one image, deploys it to the mac-server, runs
   migrations, and then passes a live-site check. A failed live check fails the
   workflow run.
4. Production refuses to start with development secrets: the dev JWT secret, the
   dev encryption keyring, or the default DB password.
5. The service is onboarded to the mac-server platform with all six artifacts that
   `SERVICE_ONBOARDING.md` requires.

## 2. Decisions

| Decision | Status |
|---|---|
| Host: the mac-server, through its platform (`serverctl`, Tailscale deploy, Cloudflare Tunnel) | DECIDED |
| Domain `verasig.io` (Cloudflare Registrar, zone active 2026-10-30); site on the apex | DECIDED (apex: my call) |
| Deploy from `main`; the temporary site is the only environment (`production`) | DECIDED |
| One image holds the backend and the built web app; one process serves both | my call |
| Migrations run when the app container starts, before the server starts | my call |
| Image in GHCR, public package (the repo is already public) | my call |
| Loopback port `18093` | my call |

Why one image: the platform catalog has one image per service (`image` in
`service-catalog.json`), and `serverctl deploy` takes one `image@sha256:digest`.

Why migrations at start: `serverctl` verifies that every Compose service is
`running` and `healthy` (`scripts/serverctl`, `verify_loaded_target`). A one-shot
`migrate` container exits, so it fails that check.

Why one process: the tunnel maps one hostname to one loopback port and does not
strip paths. FastAPI serving the web files removes the need for a second
process or a proxy.

## 3. Runtime layout on the mac-server

```
Internet -> Cloudflare (HTTPS) -> Tunnel -> 127.0.0.1:18093 -> app container :8000
app container (one uvicorn process):
  /api/*  -> the existing FastAPI app (prefix stripped by the mount)
  /*      -> built web app files; unknown paths return index.html
app -> db (postgres, named volume, same Compose project network)
```

- A new site entrypoint mounts the existing API app at `/api` and serves the
  built web app at `/`. The API routes and the local `make dev` setup do not change.
- The web app is built with `VITE_VERASIG_API_URL=/api`. `createApiUrl` already
  joins a base and a path, so relative URLs work.
- The container command runs `alembic upgrade head`, then starts uvicorn. A failed
  migration stops the container, so `serverctl` rolls back to the previous image.
  `serverctl rollback` does not undo a migration (platform rule, `SERVICES.md`).
- `VERASIG_ENV=production`. The existing guard rejects `dev-secret` and JWT secrets
  under 32 characters outside `local`. This project adds the same rule for the dev
  keyring and the default DB password `verasig`.
- Secrets reach the container as files in `/run/secrets`, set with
  `serverctl secret set`: `jwt_secret`, `secret_keys`, `postgres_password`. Settings
  read them through `*_FILE` variables or pydantic-settings `secrets_dir`
  (chosen in the plan).
- Non-secret settings live in the platform config file (`config.env`), including
  `VERASIG_CORS_ORIGINS='["https://verasig.io"]'`.
- SSE requests carry the JWT as `?token=`. The existing access-log filter already
  redacts it (`foundation/http/access_logging.py`).
- Compose follows `services/mediancode-app/` in the mac-server repo: images pinned
  by digest, `restart: unless-stopped`, health checks, CPU, memory and PID limits,
  loopback-only port, read-only app filesystem, named volume for Postgres.

## 4. mac-server onboarding (pull request to `evgesha9400/mac-server`)

The six artifacts from `SERVICE_ONBOARDING.md`:

1. Catalog entry `verasig`: image `ghcr.io/evgesha9400/verasig`, source label
   `https://github.com/evgesha9400/Verasig`, secrets above, environment
   `production` with `APP_PORT=18093`, health URL
   `http://127.0.0.1:18093/api/health`, watchdog `running` / `automatic`,
   restart service `app`.
2. `services/verasig/compose.yml` with `app` and `db`.
3. `services/verasig/README.md`.
4. `CHANGES.md` entry.
5. `ROLLBACK.md` additions.
6. Operator runbook in the pull request description.

Plus the tunnel route `verasig.io -> http://127.0.0.1:18093` in
`services/cloudflared/config.yml`, and a proxied DNS record for `verasig.io` that
points at the tunnel (outside the repo, named in the runbook).

The mac-server repo is PR-only with rebase merges. A merge to `main` that touches
`services/**` runs its Apply workflow.

## 5. CI (GitHub Actions)

`.github/workflows/ci.yml`, on pull requests and pushes to `develop` and `main`:

1. `make check` (format, lint, test, build). The runner needs Docker: backend tests
   start Postgres with testcontainers.
2. CI E2E: build the production image, start it with Postgres, and run
   `npm run e2e` against it. This tests the same image the server runs. The setup
   project registers a throwaway user through `POST /api/auth/register`
   (`first_name`, `last_name`, `email`, `password`) and logs in.

`.github/workflows/deploy.yml`, on push to `main` only, in a GitHub environment
named `production`:

1. Build and push `ghcr.io/evgesha9400/verasig:<sha>` for `linux/amd64`, with the
   OCI source label. Read the pushed digest.
2. Join the tailnet with the Tailscale OIDC credential, then SSH with the forced
   command: `deploy production ghcr.io/evgesha9400/verasig@sha256:<digest>`.
   `serverctl` pulls, starts, verifies, and rolls back on failure.
3. Live-site check: `npm run e2e -- --grep @smoke` with `E2E_BASE_URL` and
   `E2E_API_URL` set to the site, logged in as the smoke account.

Repository secrets and variables come from `scripts/onboard-deploy-repo.sh`:
`DEPLOY_KEY`, `DEPLOY_HOST`, `TS_OAUTH_CLIENT_ID`, `TS_AUDIENCE`, plus
`MAC_SERVER_SSH_KNOWN_HOSTS` and the kill switch `ENABLE_MAC_SERVER_DEPLOY`.
This project adds `SMOKE_EMAIL` and `SMOKE_PASSWORD`. Workflows from forks never
see secrets. After onboarding, check that the deploy job ran, not only that the
run is green (a skipped job leaves the run green).

## 6. E2E scope in this project

| Spec | Runs in CI | Runs on live site (`@smoke`) |
|---|---|---|
| Landing page loads | yes | yes |
| Register through the sign-up form, land in the app | yes | no (would create users) |
| Logged-in user reaches the app and the feeds view renders | yes | yes |
| A deep link such as `/app` loads the web app, not a 404 | yes | yes |

The live site never registers users. The smoke account is created once through
the sign-up page. Specs that run against the live site stay read-only.
`feeds.spec.js` needs a Telegram-connected account, so it skips in CI.

## 7. Risks

| Risk | Handling |
|---|---|
| Home internet or power outage takes the site down | Accepted for the temporary site. Revisit before real-money live trading. |
| The host is shared with other production services | Measured 2026-10-30: all containers use about 1.4 GB of the 7.75 GB Colima VM. Memory and CPU limits on both Verasig containers. |
| A backtest uses about 1.2 GB (measured) | App memory limit 2 GB until project 2. The live check does not run a backtest. |
| A bad migration | The container fails to start and `serverctl` restores the previous image. Schema changes stay backward compatible. |
| The DB lives in a Docker named volume; the host backup copies `/Users/Shared/server/` only (INFERRED from `backup-to-mega.sh`) | Accepted for test data. The `secret_keys` value is also kept in the user's password manager, because losing it makes stored Telegram sessions and Bybit keys unreadable. |

## 8. Out of scope

Price-data fix (project 2), Telegram picker (4), payments (7), a second
environment, `www.verasig.io`, off-host database backups, monitoring beyond the
platform watchdog and health check.

## 9. Unknowns to settle in the plan

- Whether SSE progress streams pass through Cloudflare and the tunnel without
  buffering. Checked with a real stream in project 4; project 1 checks one SSE
  route returns `text/event-stream` through the site.
- Whether the API token in this machine's `CLOUDFLARE_API_TOKEN` can write DNS for
  `verasig.io`. If not, the user adds the record in the dashboard.
