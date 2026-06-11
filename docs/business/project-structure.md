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
|-- secrets/
|-- docker-compose.yml
|-- Makefile
`-- README.md
```

## Root Ownership

- `apps/backend/` owns backend runtime code, migrations, CLI, and tests.
- `apps/frontend/` owns production UI code and runtime design-system modules.
- `docs/` owns product, architecture, domain, and implementation records.
- `libs/contracts/` is reserved for shared backend/frontend payload contracts.
- `graphify-out/` owns canonical graph outputs only.
- `secrets/` is local runtime input and must stay ignored.

## Backend

```text
apps/backend/
|-- src/
|   `-- verasig/
|       |-- domain/
|       |-- services/
|       |-- foundation/
|       |-- storage/
|       |-- cli.py
|       `-- config.py
|-- migrations/
|-- tests/
|   |-- unit/
|   |-- integration/
|   `-- fixtures/
|-- Dockerfile
|-- alembic.ini
|-- pyproject.toml
`-- uv.lock
```

## Backend Module Rules

- `domain/` owns pure contracts, enums, value objects, and Protocol seams.
- `services/` owns feature logic and thin orchestration that changes with that logic.
- `foundation/` owns concrete external adapters and runtime setup.
- `storage/` owns SQLAlchemy rows and repository modules.
- `cli.py` owns the Typer entrypoint and should stay thin over services.
- No `application/` layer exists; ADR 0010 explicitly defers that split.
- Pure modules use names such as `diff`, `fold`, `hygiene`, and `scorecard`.
- IO orchestration modules use names such as `backfill`, `live`, `rescan`, and `extract_service`.

## Frontend

```text
apps/frontend/
|-- src/
|   |-- assets/
|   |-- data/
|   |-- design-system/
|   |   |-- components/
|   |   |-- icons/
|   |   `-- tokens/
|   |-- features/
|   |   |-- auth/
|   |   |-- exchanges/
|   |   |-- pipeline/
|   |   |-- settings/
|   |   |-- signals/
|   |   `-- sources/
|   |-- layout/
|   |-- App.jsx
|   |-- app.css
|   `-- main.jsx
|-- public/
|-- index.html
|-- package.json
`-- package-lock.json
```

## Frontend Module Rules

- `design-system/` owns reusable runtime UI modules and tokens.
- `features/` owns user workflow screens grouped by product capability.
- `layout/` owns shell-level navigation and page chrome.
- `data/` owns prototype seed data until backend payload contracts exist.
- `App.jsx` is the composition root and should not absorb feature internals.

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

- Track `GRAPH_REPORT.md`, `graph.html`, and `graph.json` when the project graph is intentionally refreshed.
- Ignore Graphify cache, manifests, cost trackers, and transient `.graphify_*.json` files.

## Generated Artifact Rules

- Track lockfiles.
- Do not track `node_modules/`.
- Do not track Python virtual environments.
- Do not track Graphify cache/state files.
- Do not track local secrets or Telegram sessions.

## Naming Rules

- `TelegramChannel` means a monitored Telegram source.
- `RawTelegramMessage` means immutable captured source content.
- `RawSignalEvent` means an advisory signal candidate.
- `TradeIntent` means parsed trade intent without event linkage.
- `ExtractedSignal` means a `TradeIntent` recorded against a `RawSignalEvent`.
- `FoldedSignal` means the recomputed lifecycle view.
- `DeletedSignalEvidence` means durable non-recomputable deletion proof.
- `ProviderScore` means the recomputed provider quality score.
- Do not use the bare word `Signal` for persisted domain objects.

## Deferred Splits

- `workers/` is not an active root.
- `containers/extractor-agent/` is not an active root.
- A full `application/` package is deferred by ADR 0010.
- Future deployable splits require concrete growth pressure.
