# Verasig Backend

## Layout

- `src/`: Python package source (`verasig`).
- `migrations/`: Alembic migration scripts.
- `tests/`: backend unit and integration tests.
- `Dockerfile`: production container build.
- `alembic.ini`: migration config.

## Commands

- `cd apps/backend`
- `uv sync`
- `uv run pytest`
- `uv run verasig health`
- `uv run verasig migrate`
- `cd ../.. && docker compose up --build`
