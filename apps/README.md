# Apps Workspace

## Boundaries

- `apps/backend/`: backend application and runtime surface.
- `apps/frontend/`: frontend workspace and runtime UI surface.
- `libs/contracts/`: shared contracts when backend/frontend communicate over DTOs.

## Ownership

- `apps/backend` owns data models, CLI, and persistence behavior.
- `apps/frontend` owns product UI, marketing UI, design-system code, and frontend tooling.
- `libs/contracts` owns cross-layer payload shapes and versioned API types.

## Environment loading

- Backend uses `VERASIG_*` variables.
- Backend still reads `.env` when run from `apps/backend`.
- Runtime values are usually injected via compose from repository root `.env`.
