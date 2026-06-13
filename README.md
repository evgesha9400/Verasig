# Verasig

Proof-first signal provider intelligence.

## Repo structure

- `apps/backend/` — Python backend service (logic, migrations, API entrypoint, tests).
- `apps/frontend/` — frontend workspace: unified web app, design system, and JS tooling.
- `libs/contracts/` — shared API contract definitions (reserved for phase 2+).
- `docs/` — architecture docs, domain language, product docs, and design references.
- `graphify-out/` — canonical project graph outputs; cache/state files are ignored.

## Backend

Backend source is feature-owned under `apps/backend/src/verasig/features/`.
`domain/` keeps pure contracts and Protocol seams, while `foundation/` owns
concrete adapters, database setup, HTTP helpers, LLM adapters, security, market
data, and Telegram integration.

- `cd apps/backend`
- `uv sync`
- `uv run pytest`
- `uv run alembic upgrade head`
- `uv run uvicorn verasig.entrypoints.api:create_app_from_env --factory --reload`

Backend package remains `verasig`.

## Frontend

- `cd apps/frontend`
- `npm ci`
- `make format-check`
- `make lint`
- `make test`
- `make build`

Frontend package management stays inside `apps/frontend/`.

The unified frontend app serves marketing, auth, and product routes from one Vite
runtime:

- `/` — public marketing landing.
- `/login` — public login view.
- `/signup` — public registration view.
- `/app` — authenticated product shell.

Web source is organized as:

- `web/src/app/` — entrypoint, routing, shell composition, and local session state.
- `web/src/domain/` — UI-independent demo data and workflow constants.
- `web/src/features/` — auth, marketing, product screens, sources, pipeline, signals, exchanges, and settings.
- `design-system/src/` — reusable UI implementation; root `index.js`, `styles.css`, and `tokens/*` remain public entrypoints.

## Local stack

- `make env`
- `make up`
- open `http://localhost:5173`
- check `http://localhost:8000/health`
- stop with `make down`

Compose starts Postgres, runs migrations, starts the backend API, waits for API
health, and then starts the Vite frontend.

Compose uses `apps/backend/.env`, `apps/backend/Dockerfile`,
`apps/backend/alembic.ini`, and the frontend workspace under `apps/frontend/`.

## Environment

- Keep backend runtime values in `apps/backend/.env`.
- Create local values with `make env`.
- Keep environment variable names unchanged (`VERASIG_*`) in this phase.
- Keep the tracked template at `apps/backend/.env.example`.

## Documents

- [Graphify protocol](docs/GRAPHIFY.md)
- [Product requirements](docs/business/requirements.md)
- [Architecture decisions](docs/business/architecture-decisions.md)
- [Design and domain language](docs/context/CONTEXT.md)
- [Design system source](apps/frontend/design-system)
- [Current project structure](docs/business/project-structure.md)
