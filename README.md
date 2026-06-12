# Verasig

Proof-first signal provider intelligence.

## Repo structure

- `apps/backend/` — Python backend service (logic, migrations, CLI, tests).
- `apps/frontend/` — frontend workspace: product app, marketing app, design system, and JS tooling.
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

## Database migrations and app container

- `docker compose up --build`

Compose uses `apps/backend/Dockerfile` and `apps/backend/alembic.ini`.

## Environment

- Keep the root `.env` for local compose/runtime.
- Keep environment variable names unchanged (`VERASIG_*`) in this phase.
- `.env.example` remains at repository root.

## Documents

- [Graphify protocol](docs/GRAPHIFY.md)
- [Product requirements](docs/business/requirements.md)
- [Architecture decisions](docs/business/architecture-decisions.md)
- [Design and domain language](docs/context/CONTEXT.md)
- [Design system](docs/DESIGN.md)
- [Current project structure](docs/business/project-structure.md)
