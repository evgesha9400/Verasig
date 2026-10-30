# Verasig

**Proof-first intelligence on trading signal providers.**

Verasig reconstructs a signal provider's *real* track record — including the losing
calls they quietly deleted — so you can judge who to trust before you follow a
single trade. It captures every signal as it is published, scores each provider on
manipulation-resistant metrics, and presents the verdict in one dashboard.

## Why Verasig

- **Providers curate their history.** Screenshots are cherry-picked and losing
  calls get deleted, inflating advertised win rates.
- **Proof, not promises.** Every score traces back to signals Verasig captured
  first-hand, not to the provider's marketing.
- **One dashboard.** Connect a channel, let Verasig capture and score it, and read
  an evidence-backed verdict — no spreadsheets, no manual tallying.

## What it does

- **Capture** — ingests every message from public *and* private (paid) Telegram
  channels via a user-account session, so bot-blocking channels are still covered.
- **Parse** — turns each raw message into a canonical signal (symbol, side, entry,
  stop, targets, confidence), deterministic rules first with an LLM fallback for
  new formats.
- **Score** — rates each provider on PnL, active-user count, drawdown, and
  deleted-signal behaviour, so a single number is hard to game.
- **Dashboard** — a provider performance view for subscribers to inspect signals
  before trusting a source.

## Who it's for

- **Traders** vetting paid signal groups before they subscribe.
- **Signal sellers** who want an evidence-backed performance page that subscribers
  can independently verify.

## Status

Observe-only scoring on Bybit (tooling-only stance; live execution stays out of
scope until observe-only scoring proves its value). First source is Telegram.

---

The rest of this document is the developer guide.

## Repo structure

- `apps/backend/` — Python backend service (logic, migrations, API entrypoint, tests).
- `apps/frontend/` — frontend workspace: unified web app, design system, and JS tooling.
- `libs/contracts/` — shared API contract definitions (reserved for phase 2+).
- `docs/` — architecture docs, domain language, product docs, and design references.
- `graphify-out/` — canonical project graph outputs; cache/state files are ignored.

## Backend

Backend source is feature-owned under `apps/backend/src/verasig/features/`.
`domain/` keeps pure contracts and Protocol seams, while `foundation/` owns
concrete adapters, database setup, HTTP helpers, LLM adapters, security, market
data, and Telegram integration.

- `cd apps/backend`
- `uv sync`
- `uv run pytest`
- `uv run alembic upgrade head`
- `uv run uvicorn verasig.entrypoints.api:create_app_from_env --factory --reload`

Backend package remains `verasig`.

## Frontend

- `cd apps/frontend`
- `npm ci`
- `make format-check`
- `make lint`
- `make test`
- `make build`

Frontend package management stays inside `apps/frontend/`.

The unified frontend app serves marketing, auth, and product routes from one Vite
runtime:

- `/` — public marketing landing.
- `/login` — public login view.
- `/signup` — public registration view.
- `/app` — authenticated product shell.

Web source is organized as:

- `web/src/app/` — entrypoint, routing, shell composition, and local session state.
- `web/src/domain/` — UI-independent demo data and workflow constants.
- `web/src/features/` — auth, marketing, product screens, sources, pipeline, signals, exchanges, and settings.
- `design-system/src/` — reusable UI implementation; root `index.js`, `styles.css`, and `tokens/*` remain public entrypoints.

## Local stack

- `make env`
- `make up`
- open `http://localhost:5173`
- check `http://localhost:8000/health`
- stop with `make down`

Compose starts Postgres, runs migrations, starts the backend API, waits for API
health, and then starts the Vite frontend.

Compose uses `apps/backend/.env`, `apps/backend/Dockerfile`,
`apps/backend/alembic.ini`, and the frontend workspace under `apps/frontend/`.

## Environment

- Keep backend runtime values in `apps/backend/.env`.
- Create local values with `make env`.
- Keep environment variable names unchanged (`VERASIG_*`) in this phase.
- Keep the tracked template at `apps/backend/.env.example`.

### Stripe billing

Stripe is the only source of a paid plan: hosted Checkout, the customer portal,
and one webhook (`POST /billing/webhook`) that writes the plan. Billing requests
answer `503 BILLING_NOT_CONFIGURED` while a value below is blank.

| Variable | Meaning |
|---|---|
| `VERASIG_STRIPE_SECRET_KEY` | Stripe secret key (`sk_test_...` until launch). Site: `VERASIG_STRIPE_SECRET_KEY_FILE`. |
| `VERASIG_STRIPE_WEBHOOK_SECRET` | Signing secret of the webhook endpoint (`whsec_...`). Site: `VERASIG_STRIPE_WEBHOOK_SECRET_FILE`. |
| `VERASIG_STRIPE_PRICE_TRADER_MONTHLY` | Price id of Trader, $49 per month. |
| `VERASIG_STRIPE_PRICE_TRADER_YEARLY` | Price id of Trader, $468 per year ($39 per month). |
| `VERASIG_SITE_URL` | Public web origin that Checkout and the portal return to. Default `http://localhost:5173`; the site is `https://verasig.io`. |

Local webhook: `stripe listen --latest --forward-to localhost:8000/billing/webhook`,
then put the `whsec_...` it prints into `VERASIG_STRIPE_WEBHOOK_SECRET`. `--latest`
matters: the webhook only reads events of the Stripe API release the `stripe` SDK is
pinned to (`endive`) and answers `400 BILLING_WEBHOOK_API_VERSION` to others; an
account's default version can be older (the sandbox default was `2022-08-01`). A
dashboard webhook endpoint must likewise use an `endive` API version and send:
`checkout.session.completed`, `customer.subscription.created`,
`customer.subscription.updated`, `customer.subscription.deleted`, `invoice.paid`,
`invoice.payment_failed`.

## Documents

- [Graphify protocol](docs/GRAPHIFY.md)
- [Product requirements](docs/business/requirements.md)
- [Architecture decisions](docs/business/architecture-decisions.md)
- [Design and domain language](docs/context/CONTEXT.md)
- [Design system source](apps/frontend/design-system)
- [Current project structure](docs/business/project-structure.md)
