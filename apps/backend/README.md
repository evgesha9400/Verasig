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
- `cd ../.. && make up`

## Environment

- `.env.example` is the tracked backend runtime template.
- `.env` is local, gitignored, and read by backend commands run from this directory.
- Root `make env` creates `.env` from `.env.example` when missing.
