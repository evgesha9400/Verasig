# Project 1: deploy, CI/CD, and the E2E harness

Date: 2026-10-29. Status: approved by the user 2026-10-29.
Parent: `2026-10-29-launch-architecture-design.md` (project 1 of 7).

## 1. Goal

Put the current app on a public HTTPS address, deployed automatically from `main`,
with CI on every pull request. Later projects ship through this path and add their
own E2E steps.

Done means:

1. `https://<static-ip-with-dashes>.sslip.io` serves the web app and the API.
2. A pull request to `develop` or `main` runs `make check` and the CI E2E suite.
3. A merge to `main` builds images, deploys them, runs migrations, and then passes a
   live-site check. A failed live check fails the workflow run.
4. Production refuses to start with development secrets: the dev JWT secret, the
   dev encryption keyring, or the default DB password.
5. Recreating the server from scratch is one documented command plus restoring
   secrets.

## 2. Decisions

| Decision | Status |
|---|---|
| AWS account `personal`, region eu-west-1 | DECIDED |
| One Lightsail instance, 2 GB bundle ($12/month), Postgres on the same server | DECIDED |
| Daily automatic snapshots (Lightsail auto-snapshot add-on) | DECIDED |
| Deploy over SSH with a key stored as a GitHub secret, usable only from `main` | DECIDED |
| Deploy from `main`; the temporary site is the only environment | DECIDED |
| Caddy as the reverse proxy and HTTPS end | my call |
| Images in GitHub Container Registry (GHCR), public, so the server pulls without credentials | my call |
| The server is defined in one CloudFormation template (no extra tool to install) | my call |
| Production secrets live in one `.env` on the server, with a copy in SSM Parameter Store (SecureString) | my call |

Why keep a copy of secrets: `VERASIG_SECRET_KEYS` encrypts stored Telegram sessions
and Bybit keys. Losing it makes that data unreadable, so it must survive the server.

## 3. Runtime layout on the server

```
Internet :443/:80 -> caddy (static web app + reverse proxy)
                       |- /            -> built web app files
                       '- /api/*       -> app:8000 (prefix stripped)
app (backend image)  -> db (postgres:16, volume on the instance disk)
migrate (backend image, runs `alembic upgrade head`, then exits)
```

- One compose file for production at `deploy/compose.yml`. It reuses the services
  in the root `docker-compose.yml` shape but has no dev defaults:
  `VERASIG_SECRET_KEYS` and the DB password use `${VAR:?}` so compose fails if they
  are missing.
- Postgres and the app are not published on host ports. Only Caddy listens.
- `VERASIG_ENV=production`. The existing guard in `config.py` rejects `dev-secret`
  and JWT secrets shorter than 32 characters outside `local`. This project adds the
  same rule for the dev keyring (the all-`A` key in `.env.example` and compose) and
  the default DB password `verasig`. `${VAR:?}` alone only catches a missing value.
- Caddy keeps certificates in a named volume `caddy_data` (`/data`), so a redeploy
  does not request a new certificate.
- Memory limits on `db` and `app` keep one process from starving the others on 2 GB.
  Exact values are set in the plan.
- The web app image is a multi-stage build from `apps/frontend` (the npm workspace
  root, since `web` depends on `design-system`): `npm ci` and `vite build` with
  `VITE_VERASIG_API_URL=https://<host>/api`, then the files are copied into a Caddy
  image with the `Caddyfile`. The API URL is fixed at build time, so the host name is
  a build input from CI.
- `VERASIG_CORS_ORIGINS` is set to the site origin, written as JSON
  (`'["https://<host>"]'`). The web app and API share one
  origin, so CORS is not needed in practice; the setting stays correct anyway.
- SSE requests carry the JWT as `?token=`. Caddy access logs are off or drop the
  query string, so tokens never reach logs. SSE responses are not buffered.

## 4. Server definition

`deploy/server.yaml` (CloudFormation):

- `AWS::Lightsail::StaticIp` and `AWS::Lightsail::Instance` (Ubuntu LTS, 2 GB
  bundle), attached.
- Firewall: 22, 80, 443 open.
- Auto-snapshot add-on, daily.
- User data installs Docker and the compose plugin, creates a `deploy` user in the
  `docker` group, and adds the deploy public key to that user only.

`deploy/README.md` documents: create the stack, read the static IP, write the `.env`
(and its SSM copy), make the two GHCR packages public after the first push, create
the smoke account once through the site's register page, add GitHub secrets, and
restore from a snapshot.

## 5. CI (GitHub Actions)

`.github/workflows/ci.yml`, on pull requests and pushes to `develop` and `main`:

1. `make check` (format, lint, test, build). The runner needs Docker: backend tests
   start Postgres with testcontainers, and `build-image` builds the backend image.
   The `env` target creates `apps/backend/.env` from `.env.example`.
2. CI E2E: start the stack with the root `docker-compose.yml`, then run `npm run e2e`.
   The setup project registers a throwaway user through `POST /auth/register`
   (`first_name`, `last_name`, `email`, `password`) and logs in.

`.github/workflows/deploy.yml`, on push to `main` only, in a GitHub environment
named `production` that only `main` may use:

1. Build and push `ghcr.io/evgesha9400/verasig-backend:<sha>` and
   `ghcr.io/evgesha9400/verasig-web:<sha>`.
2. SSH as `deploy`: copy `deploy/compose.yml`, set the image tag, `docker compose
   pull`, run `migrate`, `up -d`, then wait for `/api/health`.
3. Live-site check: run `npm run e2e -- --grep @smoke` with `E2E_BASE_URL` and
   `E2E_API_URL` pointing at the site, logged in as the smoke account.

Secrets in the `production` environment: `DEPLOY_SSH_KEY`, `DEPLOY_HOST`,
`SMOKE_EMAIL`, `SMOKE_PASSWORD`. Workflows from forks never see them.

## 6. E2E scope in this project

The harness and the steps the current app supports:

| Spec | Runs in CI | Runs on live site (`@smoke`) |
|---|---|---|
| Landing page loads | yes | yes |
| Register through the sign-up form, land in the app | yes | no (would create users) |
| Logged-in user reaches the app and the feeds view renders | yes | yes |

In CI the setup project registers its user through the API. The sign-up form is
covered by its own spec. The live site never registers users.

The existing `feeds.spec.js` needs a Telegram-connected account, so it skips in CI.
Later projects add their steps as the parent design lists.

Specs that run against the live site stay read-only.

## 7. Risks

| Risk | Handling |
|---|---|
| sslip.io shares one Let's Encrypt limit with all users (not on the Public Suffix List) | Caddy falls back to ZeroSSL, then retries. Buying a domain removes it. |
| A bad migration breaks the live site | Lightsail snapshot restore. The deploy stops before `up` if `migrate` fails. |
| The 2 GB server runs out of memory during a backtest | Known until project 2. The live check does not run a backtest. |
| Disk fills with old images | The deploy runs `docker image prune` after a good deploy. |

## 8. Out of scope

Price-data fix (project 2), Telegram picker (4), payments (7), a second environment,
a custom domain, monitoring beyond the health check.

## 9. Unknowns to settle in the plan

- Whether `AWS::Lightsail::Instance` supports the auto-snapshot add-on in
  CloudFormation; if not, enable it with one CLI call in the README.
- Whether Caddy's `handle_path /api/*` strip matches every backend route,
  including the SSE progress streams (needs flush settings checked).
