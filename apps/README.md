# Apps Workspace

## Boundaries

- `apps/backend/`: backend application and runtime surface.
- `apps/frontend/`: frontend workspace and runtime UI surface.
- `libs/contracts/`: shared contracts when backend/frontend communicate over DTOs.

## Ownership

- `apps/backend` owns data models, CLI, and persistence behavior.
- `apps/frontend` owns the unified web UI, design-system code, and frontend tooling.
- `libs/contracts` owns cross-layer payload shapes and versioned API types.

## Environment loading

- Backend uses `VERASIG_*` variables.
- Backend reads `apps/backend/.env` when run from `apps/backend`.
- Compose injects runtime values from `apps/backend/.env`.
