# Verasig Frontend

## Layout

- `web/` owns the Vite runtime for marketing, auth, and product routes.
- `web/src/app/` owns the app entrypoint, routing, shell composition, and local session state.
- `web/src/domain/` owns UI-independent demo data and workflow constants.
- `web/src/features/` owns auth, marketing, product screens, sources, pipeline, signals, exchanges, and settings.
- `design-system/` owns reusable runtime UI modules.
- `design-system/src/` owns UI implementation files.
- `design-system/index.js`, `design-system/styles.css`, and `design-system/tokens/*` remain package public API.

## Commands

- `cd ../.. && make up`
- `cd apps/frontend`
- `npm ci`
- `npm run dev --workspace verasig-web`
- `npm run test`
- `npm run lint`
- `npm run build`
- `npm run format:check`

Root `make up` starts Postgres, migrations, the backend API, and the Vite
frontend. The workspace dev command is useful when the backend stack is already
running.
