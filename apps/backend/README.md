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
- `uv run alembic upgrade head`
- `uv run uvicorn verasig.api.app:create_app_from_env --factory --reload`
- `curl -fsS localhost:8000/health`
- `cd ../.. && make up`

## Environment

- `.env.example` is the tracked backend runtime template.
- `.env` is local, gitignored, and read by backend commands run from this directory.
- Root `make env` creates `.env` from `.env.example` when missing.

## API

| Area | Endpoints |
|---|---|
| Health | `GET /health` |
| Auth/User | `/auth/*`, `/user/*` |
| Telegram | `/telegram/connect`, `/telegram/verify`, `/telegram/status` |
| Chats | `/chats`, `/chats/{id}/backfill`, `/chats/{id}/messages` |
| Verify/Rules | `/chats/{id}/verify/*`, `/chats/{id}/distill`, `/chats/{id}/rules` |
| Exchanges/Risk/Backtest | `/exchanges`, `/chats/{id}/risk`, `/chats/{id}/backtest` |
| Signals | `/signals`, `/signals/{id}`, `/signals/{id}/link-mod` |

See `docs/rewrite/requirements.md` for the full contract.
