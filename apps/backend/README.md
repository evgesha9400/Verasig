# Verasig Backend

## Layout

- `src/verasig/features/`: feature-owned backend routes, schemas, workflows, views, and repositories.
- `src/verasig/domain/`: pure contracts, enums, value objects, and Protocol seams.
- `src/verasig/foundation/`: concrete adapters, database/session setup, HTTP helpers, security, market data, LLM, Telegram, and job coordination.
- `src/verasig/entrypoints/api.py`: FastAPI composition root.
- `src/verasig/shared/`: generic helpers with no feature ownership.
- `src/verasig/storage/models.py`: centralized SQLAlchemy row registry.
- `migrations/`: Alembic migration scripts.
- `tests/`: backend tests mirrored by owner plus API and integration workflow tests.
- `Dockerfile`: production container build.
- `alembic.ini`: migration config.

## Commands

- `cd apps/backend`
- `uv sync`
- `uv run pytest`
- `uv run alembic upgrade head`
- `uv run uvicorn verasig.entrypoints.api:create_app_from_env --factory --reload`
- `curl -fsS localhost:8000/health`
- `cd ../.. && make up` starts Postgres, migrations, API, and frontend

## Environment

- `.env.example` is the tracked backend runtime template.
- `.env` is local, gitignored, and read by backend commands run from this directory.
- Root `make env` creates `.env` from `.env.example` when missing.

## API

| Area | Endpoints |
|---|---|
| Health | `GET /health` |
| Auth/User | `/auth/*`, `/user/*` |
| Billing | `POST /billing/checkout`, `POST /billing/portal`, `POST /billing/webhook` (Stripe-signed, no auth) |
| Telegram | `/telegram/connect`, `/telegram/verify`, `/telegram/status` |
| Feeds | `/feeds`, `/feeds/{id}/backfill`, `/feeds/{id}/messages` |
| Mining | `/feeds/{id}/mine`, `/feeds/{id}/mine/progress`, `/feeds/{id}/mining/confirm` |
| Exchanges/Risk/Backtest | `/exchanges`, `/feeds/{id}/risk`, `/feeds/{id}/backtest` |
| Signals | `/signals`, `/signals/{id}`, `/signals/{id}/link-mod` |

See `tests/api/` for executable API behavior.
