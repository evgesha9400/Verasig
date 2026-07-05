# Verasig — Claude working notes

Monorepo:

- `apps/backend` — FastAPI + Postgres (SQLAlchemy, Alembic, `uv`).
- `apps/frontend` — npm workspaces: `web` (the React/Vite app) + `design-system`.

Local stack: `make dev` (repo root) → Postgres in Docker (`:5432`) + backend & frontend on the **host**
with hot reload (API `:8000`, Web `:5173`; Ctrl-C stops both). `make up` is the all-Docker alternative.

## Driving authenticated views in a real browser (Playwright)

The web app stores its session as a **bare JWT in `localStorage['vrs-auth-token-1']`** (no cookie),
validated on boot by `GET /auth/me`. To reach authenticated views (e.g. the feeds view) in a real
browser, **never type the login form** — use the committed harness at `apps/frontend/web/`, which
logs in via the API and reuses the session.

### One-time setup (per dev)

- `cp apps/frontend/web/e2e/.env.example apps/frontend/web/e2e/.env`
- Set `E2E_EMAIL` / `E2E_PASSWORD` to a **local** dev account. Use one with Telegram connected +
  feeds so the feed specs run (a fresh account renders an empty feeds view → those specs skip).
- `e2e/.env` and `e2e/.auth/` are git-ignored — the token is a real credential; never commit them.

### Run

- Terminal 1 — `make dev` (repo root): DB in Docker + backend (`:8000`) + frontend (`:5173`) on the host.
- Terminal 2 — from `apps/frontend/web`: `npm run e2e` (reuses the running `:5173`, logs in at `:8000`).
  - The `setup` project `POST`s `/auth/login` and writes `e2e/.auth/state.json`. A fresh token is
    minted every run, so expiry never bites.
  - Specs then run **already authenticated**, against the real backend + your real feeds.
  - The backend just needs to be up on `:8000`; `make dev` is simplest, but `make serve` works too.
- `npm run e2e:ui` — interactive runner. `npm run e2e:report` — open the last HTML report.

### Ad-hoc (agent driving the Playwright MCP)

1. Mint a token:
   `curl -s localhost:8000/auth/login -H 'content-type: application/json' -d '{"email":"…","password":"…"}'`
   → copy the `token`.
2. In the MCP browser: navigate to `http://localhost:5173`, run
   `localStorage.setItem('vrs-auth-token-1', '<token>')`, then navigate to `/app`.

### Guardrails

- `e2e/.env` and `e2e/.auth/state.json` = live credentials → git-ignored, never committed.
- Specs act **as that account** → keep them read-only (hover, layout, screenshots); nothing destructive.
- The backend must be up on `:8000` or the `setup` project fails with a clear message.

## Git

- Branch off `develop` for any feature/fix; merge back with a `Merge: …` commit. `main` = production.
- Conventional-commit messages; lint before committing.
