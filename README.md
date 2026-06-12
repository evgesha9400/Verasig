# Verasig

Proof-first signal provider intelligence.

## Repo structure

- `apps/backend/` — Python backend service (logic, migrations, CLI, tests).
- `apps/frontend/` — frontend workspace: unified web app, design system, and JS tooling.
- `libs/contracts/` — shared API contract definitions (reserved for phase 2+).
- `docs/` — architecture docs, domain language, product docs, and design references.
- `graphify-out/` — canonical project graph outputs; cache/state files are ignored.

## Backend (current behavior preserved)

- `cd apps/backend`
- `uv sync`
- `uv run pytest`
- `uv run verasig health`
- `uv run verasig migrate`

Backend package remains `verasig` and CLI command remains `verasig`.

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

## Database migrations and app container

- `make env`
- `make up`

Compose uses `apps/backend/.env`, `apps/backend/Dockerfile`, and `apps/backend/alembic.ini`.

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
- [Design system](docs/DESIGN.md)
- [Current project structure](docs/business/project-structure.md)
