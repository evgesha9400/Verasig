# Project Structure Protocol

## Root

```text
Verasig/
|-- apps/
|   |-- backend/
|   `-- frontend/
|-- docs/
|   |-- adr/
|   |-- business/
|   |-- context/
|   `-- work/
|-- libs/
|   `-- contracts/
|-- graphify-out/
|-- docker-compose.yml
|-- Makefile
`-- README.md
```

## Root Ownership

- `apps/backend/` owns backend runtime code, migrations, API entrypoints, and tests.
- `apps/frontend/` owns all frontend code, frontend package management, and runtime design-system modules.
- `docs/` owns product, architecture, domain, and implementation records.
- `libs/contracts/` is reserved for shared backend/frontend payload contracts.
- `graphify-out/` owns local generated graph outputs and remains gitignored.
- `apps/backend/secrets/` is local runtime input and must stay ignored.

## Backend

```text
apps/backend/
|-- src/
|   `-- verasig/
|       |-- domain/
|       |-- entrypoints/
|       |-- features/
|       |   |-- accounts/
|       |   |-- exchanges/
|       |   |-- feeds/
|       |   |-- mining/
|       |   |-- parser_overlay/
|       |   |-- provider_scores/
|       |   |-- risk/
|       |   |-- signals/
|       |   |-- simulation/
|       |   `-- sources/
|       |-- foundation/
|       |-- shared/
|       |-- storage/
|       `-- config.py
|-- migrations/
|   `-- versions/
|       |-- 0001_init.py
|       `-- 0002_revisioned_mining_review.py
|-- tests/
|   |-- accounts/
|   |-- api/
|   |-- exchanges/
|   |-- feeds/
|   |-- fixtures/
|   |-- foundation/
|   |-- integration/
|   |-- lab/
|   |-- mining/
|   |-- provider_scores/
|   |-- risk/
|   |-- signals/
|   |-- simulation/
|   `-- sources/
|-- Dockerfile
|-- .dockerignore
|-- .env.example
|-- .python-version
|-- Makefile
|-- alembic.ini
|-- pyproject.toml
`-- uv.lock
```

## Backend Module Rules

- `domain/` owns pure contracts, enums, value objects, and Protocol seams.
- `domain/*_ports.py` owns focused pure Protocol seams.
- `features/` owns feature routes, schemas, workflows, views, and repositories.
- `foundation/` owns concrete external adapters, database/session setup, HTTP helpers, security, market data, Telegram integration, and job coordination.
- `shared/` owns generic parsing, number, and time helpers.
- `storage/models.py` owns the centralized SQLAlchemy row registry.
- `entrypoints/api.py` owns FastAPI composition and should stay thin over feature routes and foundation adapters.
- `.env.example`, `.python-version`, and `pyproject.toml` are backend-owned runtime/tooling contracts.
- `.env` is backend-local, gitignored, and copied from `.env.example` by `make env`.
- `.dockerignore` must exclude `.env` from backend container build context.
- No `application/` layer exists; ADR 0010 explicitly defers that split.
- Feature packages use names such as `routes`, `schemas`, `workflow`, `repository`, `views`, and focused pure module names.
- Legacy `api/`, `services/`, and focused `storage/*_repository.py` wrapper surfaces must not be recreated.
- Legacy rule, label, drift, and fallback-extractor feature surfaces must not be recreated; `mining/` is the extractor and `signals/` owns its persisted projection.
- No backend tests live under `src/`.

## Frontend

```text
apps/frontend/
|-- web/
|   |-- src/
|   |   |-- app/
|   |   |-- assets/
|   |   |-- domain/
|   |   |-- features/
|   |   `-- shared/
|   |-- e2e/
|   |-- index.html
|   |-- package.json
|   `-- vite.config.js
|-- design-system/
|   |-- src/
|   |   |-- components/
|   |   |-- icons/
|   |   `-- theme/
|   |-- tokens/
|   |-- index.js
|   |-- package.json
|   `-- styles.css
|-- Makefile
|-- package.json
`-- package-lock.json
```

## Frontend Module Rules

- `apps/frontend/package.json` owns frontend workspaces and frontend-only tooling.
- `web/` owns the single Vite runtime for marketing, auth, and product routes.
- `design-system/` owns reusable runtime UI modules and tokens.
- `web/src/app/` owns the entrypoint, route constants, route-level auth decisions, product composition root, shell layout, and local session state.
- `web/src/domain/` owns UI-independent demo data and workflow constants.
- `web/src/shared/` owns cross-feature API clients, hooks, and presentation helpers.
- `web/src/features/auth/` owns public login and registration views.
- `web/src/features/marketing/` owns the public landing page.
- `web/src/features/pipeline/` owns workflow step screens.
- `web/src/features/template-mining/` owns Mine, Review, and Verify views over server-produced reviews.
- `web/src/features/sources/`, `signals/`, `exchanges/`, and `settings/` own product capability screens.
- `design-system/src/` owns implementation files.
- `design-system/index.js`, `styles.css`, and `tokens/*` are stable public package entrypoints.

## Contract Library

- `libs/contracts/` stays shallow until backend/frontend payloads are coupled.
- Shared contracts must include exported schemas, versioning, and tests before callers depend on them.
- Backend `domain/` remains the active canonical contract source until then.

## Graphify Outputs

```text
graphify-out/
|-- GRAPH_REPORT.md
|-- graph.html
`-- graph.json
```

- Keep all Graphify outputs local and ignored; updates must remain unstaged.
- `GRAPH_REPORT.md`, `graph.html`, and `graph.json` are the review surfaces inside that ignored directory.

## Generated Artifact Rules

- Track lockfiles in the owning workspace.
- Do not track `node_modules/`.
- Do not track Python virtual environments.
- Do not track Graphify cache/state files.
- Do not track local secrets or Telegram sessions.

## Naming Rules

- `Feed` means the user-owned provider stream exposed by the API and UI.
- `TelegramChannel` means the Telegram adapter's domain view of a `Feed`.
- `RawTelegramMessage` means immutable captured source content.
- `TradeIntent` means parsed trade intent without event linkage.
- `Signal` means the persisted, recomputable `TradeIntent` projection keyed directly to its source message.
- `MiningReview` means immutable reviewed input and mined output addressed by `reviewId` and guarded by `inputRevision`.
- `FoldedSignal` means the recomputed lifecycle view.
- `DeletedSignalEvidence` means durable non-recomputable deletion proof.
- `ProviderScore` means the recomputed provider quality score.
- Misses are absent `signal` rows; confirmed miss evidence belongs to the addressed `MiningReview`.

## Deferred Splits

- `workers/` is not an active root.
- `containers/extractor-agent/` is not an active root.
- A full `application/` package is deferred by ADR 0010.
- Future deployable splits require concrete growth pressure.
