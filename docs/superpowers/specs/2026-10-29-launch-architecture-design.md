# Launch architecture: temporary-site launch and capability redesign

Date: 2026-10-29. Status: approved by the user 2026-10-29. Hosting revised and approved 2026-10-30.

This is the umbrella design. It records the decisions that every launch project shares
and splits the work into seven projects. Each project gets its own spec, plan, and
build cycle. This doc does not replace those specs.

Vocabulary follows `docs/context/CONTEXT.md`: a **Feed** is a followed Telegram
channel (the UI may say "channel" in marketing copy). New terms this design adds
(Reader, Scam check, Trading plan, Destination) go into `CONTEXT.md` in project 3.

## 1. Goal

Ship Verasig to a public site (`verasig.io`, revised 2026-10-30), and prove the
whole paid journey works there with real services and no real money.

Done means all of these hold on the temporary site:

1. A visitor sees a landing page with the plans, prices, and what each plan gets.
2. The visitor signs up, starts a paid trial through Stripe, and logs in.
3. The user connects Telegram and picks feeds from a searchable list with avatars.
4. The Reader extracts signals from each picked feed.
5. The scam check, the backtest, and live trading each work on their own.
6. The user connects Bybit and live trading places and manages real orders on a
   Bybit demo account.
7. CI runs the full journey on every pull request; every merge to `main` deploys and
   then runs a live-site check.

## 2. Current state (facts from the repo, 2026-10-29)

- No CI exists (no `.github/`). The local gate is `make check`
  (format, lint, test, build).
- No order placement code exists. Bybit connect verifies keys with
  `/v5/user/query-api` and rejects keys with withdraw permission
  (`foundation/market_data/bybit_account.py`).
- Bybit base URLs are hard-coded to `https://api.bybit.com`
  (`bybit_market_data.py`, `bybit_account.py`).
- Live ingestion code exists (`features/feeds/live.py` `ingest_live`), but only a
  test calls it. Nothing runs it.
- `run_backtest` (`features/simulation/backtesting.py`) simulates each signal on its
  own, compounds the PnL, builds the ProviderScore, and sets the feed to ANALYZED.
  So the backtest and the scam score are one step today.
- The simulator fetches 1-minute klines for each symbol from that symbol's first
  signal to now and holds them all in memory, with no cache.
- The frontend pipeline is a fixed step list (`pipelineSteps.js`: backfill, mine,
  review, verify, exchange, backtest, execution). Exchange, backtest, and execution
  render a "coming soon" placeholder.
- The Signals view imports demo seed data (it uses backend data when signed in).
  The mailer only logs.
- A landing page exists (`features/marketing/MarketingView.jsx`).
- Plans: enum in `domain/account.py`, limits in `features/accounts/plans.py`
  (OBSERVER, OPERATOR, DESK), and frontend
  `stepAccess.js` / `SettingsView.jsx` (Observer $0, Operator $49, Desk $190).
- Feeds are added by typing a channel tag.

## 3. Measurements (local, 2026-10-29)

One feed: 4,486 messages, 643 signals, 79 symbols, 2025-07-07 to 2026-07-08. DB 26 MB.

| What | Result |
|---|---|
| API process idle (Linux image, imports loaded) | 196 MB |
| Postgres idle | 22 MB |
| Mining preview | 1.6 s, +263 MB peak |
| Backtest | 359 s, +1,190 MB peak, failed with Bybit error 10016, about 1 GB kept after, nothing saved |
| Telegram connect (real session, Linux) | 0.13 to 0.18 s |
| List dialogs | 168 dialogs, 104 channels or groups, 0.4 s |
| Avatars | about 4 s for 104 chats, 41 had photos, 2.4 MB |
| Live listen 180 s | 1 feed 0.12% of one core; 10 feeds 0.24%; under 1 MB per client |

Each Telegram run logged "Server closed the connection" once. Cause: UNKNOWN.

## 4. Capability model (the core redesign)

### 4.1 One core, independent consumers

```
Telegram feed -> Reader -> signal stream (stored, timestamped) -> consumers
                                                             |-> Scam check
                                                             |-> Backtest
                                                             |-> Live trading
                                                             '-> Webhook (later)
```

- **Reader**: capture plus extraction (today's backfill, live ingestion, template
  mining, and mining confirm). Its only output is the stored signal stream: signals
  and their modifications, each with a timestamp.
- **Consumers** read the stream. No consumer depends on another consumer. A user can
  turn on live trading without running a backtest.
- **Scam check**: deleted-signal evidence plus the ProviderScore. The score moves
  out of `run_backtest` into the scam check.
- **Backtest**: a simulation of results, nothing else.
- **Live trading**: places and manages orders on a destination.
- **Webhook**: deferred. It will be a destination type, so the model needs no change.

### 4.2 Trading plan

- One trading plan per feed. The backtest and live trading use the same plan, so a
  backtest shows what live trading would have done.
- The plan grows from today's `RiskConfig` (entry mode, levels, weighting, exit
  source, stop, take profit, risk %, leverage).
- Risk per trade is either a fixed USDT amount or a % of total account value
  (equity, not free balance). Risk is the loss at the stop. Position size equals
  risk divided by the stop distance.
- Author updates ("move stop to entry", "close half") change the live position
  automatically. The backtest applies them at their timestamps. They apply even when
  the plan uses a custom stop or take profit.

### 4.3 Destinations

- A destination is one Bybit account or subaccount (later also a webhook).
- Many feeds can send trades to one destination. Each feed with live trading on
  picks one destination.
- Launch supports one Bybit destination per user (Trader plan). The model allows
  many, for Desk subaccounts later.
- The destination holds the limit on total open risk.
- A signal that does not fit the limits (risk, open-risk cap, balance) is skipped.
  The skip and its reason are recorded and shown to the user.
- Live trading on a feed is the user's choice alone. No score or backtest gates it.

### 4.4 Backtest

- The backtest becomes a one-account simulation: one balance, overlapping trades,
  the same sizing and skip rules as live trading.
- Starting balance: the user sets it on the backtest. It defaults to the destination's
  account value when a destination is connected (my call).
- MUST-HAVE price-data fix:
  - one shared price-history store, reused across backtests and users;
  - each signal fetches only its own time window;
  - a bad symbol is skipped and recorded, and the run continues;
  - heavy jobs run in a separate process from the API.

## 5. Frontend

- Feed page: an overview of feature cards (option B). Each card opens a detail
  page. Cards: Live trading, Backtest, Scam check, Trading plan, Reader, Webhooks
  (shown as coming soon).
- Mobile-first: cards stack in one column at phone width.
- The fixed step list (`pipelineSteps.js`, `PaidFeaturePlaceholder`) is replaced by
  the card model. Plan access gates each card, not a step number.
- Adding feeds: pick from the account's Telegram channels and groups, with search and
  avatars. Typing a tag goes away.

## 6. Plans and pricing

| Plan | Price | Includes |
|---|---|---|
| Free check | $0 | 1 feed: Reader, scam check, backtest on the latest 200 signals |
| Trader | $49/month, or $39/month billed yearly | 10 feeds, full backtests, live trading to 1 Bybit destination; 7-day trial, card required |
| Desk | $149/month | Unlimited feeds, many subaccount destinations, webhook later |

Desk at launch: OPEN, decided before project 7. Launch supports one destination per
user (section 4.3), and the Bybit subaccount API is unverified.

- Yearly billing is about 20% off.
- Before the prices are published, check competitor prices on the official sites.
  The research used third-party pages that disagree.
- After launch, test a higher Trader price (for example $69) on new signups.
- The plan names and limits replace OBSERVER, OPERATOR, and DESK in
  `domain/account.py`, `plans.py`, and the frontend.
- Project 7 reworks the existing landing page (`MarketingView.jsx`); it does not
  add a second one.

## 7. Payments

- Stripe hosted Checkout, the Stripe customer portal, and one webhook that sets the
  user's plan. Card data never reaches our server.
- Paddle prohibits "trading signals and strategies". Lemon Squeezy excludes crypto
  products. Stripe lists neither; "other financial services" may need review, so
  apply early.
- Stripe is not the merchant of record. Verasig owes VAT and sales tax itself.
  Stripe Tax (0.5%) calculates it.
- The temporary site uses Stripe test mode until launch.

## 8. Hosting

- Revised 2026-10-30: the temporary site runs on the user's mac-server through its
  existing platform (`serverctl`, Tailscale deploy, Cloudflare Tunnel). This
  replaces the earlier Lightsail plan. Revisit before real-money live trading,
  because the server depends on home internet and power.
- Domain `verasig.io` (Cloudflare). Cloudflare ends HTTPS; the tunnel forwards to
  one loopback port.
- One image holds the backend and the built web app. One process serves the web
  app at `/` and the API at `/api`. Postgres runs in the same Compose project.
  Project 1 has the details.
- Capacity: measured 2026-10-30, other services use about 1.4 GB of the 7.75 GB
  Colima VM. Until project 2, one backtest at a time.

## 9. CI/CD

- GitHub Actions. The repo `evgesha9400/Verasig` is public; the default branch is
  `develop`.
- Every pull request and push: `make check`, then the CI E2E suite (section 10).
- Every merge to `main`: build one image, push it to GitHub Container Registry,
  deploy it with `serverctl` on the mac-server, then run the live-site check.
- One environment. The temporary site is production.

## 10. End-to-end tests

**CI suite (every pull request, no outside services):** the full journey with fakes.
Project 1 builds the harness and the steps the current app supports. Each later
project adds its own step (2 and 3 by project 7, 3 by project 4, 5 and 6 by
projects 3 and 6).

1. Landing page shows plans and prices.
2. Sign up; a simulated Stripe webhook moves the user to Trader.
3. Connect Telegram with fake dialogs; the feed picker shows search and avatars.
4. The Reader extracts signals from fixture messages.
5. The backtest runs on fixture price data.
6. The user saves a trading plan and turns on live trading against a fake exchange.

**Live-site check (after each deploy, real services, no real money):**

- Stripe test mode with the 4242 test card.
- A dedicated Telegram test account, read-only. Its session is a GitHub secret.
- Bybit demo trading (`https://api-demo.bybit.com`): place one order, then cancel it.

Specs stay read-only on real accounts except the demo order. Credentials live only
in git-ignored files and GitHub secrets.

## 11. Projects and order

Each project gets its own spec, plan, and build cycle.

| # | Project | Depends on |
|---|---|---|
| 1 | Deploy, CI/CD, and the E2E test setup: the current app on the temporary site | none |
| 2 | Backtest price-data fix and the separate job process | 1 |
| 3 | Core redesign: signal stream, trading plan, destinations, one-account backtest, scam check split, `CONTEXT.md` terms | 2 |
| 4 | Telegram feed picker with search and avatars | 1 |
| 5 | Feed page with feature cards | 3 |
| 6 | Live trading on Bybit: order placement, author updates, demo option, live ingestion runner | 3 |
| 7 | Stripe, landing page, and plan limits | 1 (the destination limit needs 3) |

Projects 4 and 7 can run in parallel with project 3.

## 12. Unknowns to settle in the named project

| Unknown | Project |
|---|---|
| SSE streams through Cloudflare without buffering | 1 (checked fully in 4) |
| Sell Desk at launch, or show it as coming soon | before 7 |
| Whether Stripe accepts the product | 7 (apply during 1) |
| Legal entity country (decides tax duties) | 7 |
| Whether Bybit demo supports `/v5/user/query-api` (used by connect) | 6 |
| Bybit subaccount API for trading | 6 |
| Cause of the "Server closed the connection" Telegram log line | 4 |
