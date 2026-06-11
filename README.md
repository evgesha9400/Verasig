# Verasig

Proof-first signal provider intelligence.

## Repo structure

- `apps/backend/` — Python backend service (logic, migrations, CLI, tests).
- `apps/frontend/` — React/Vite frontend shell for future production UI.
- `libs/contracts/` — shared API contract definitions (reserved for phase 2+).
- `docs/` — architecture docs and design references.

## Backend (current behavior preserved)

- `cd apps/backend`
- `uv sync`
- `uv run pytest`
- `uv run verasig health`
- `uv run verasig migrate`

Backend package remains `verasig` and CLI command remains `verasig`.

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
- [Design artifacts](docs/design/prototypes/Verasig)
