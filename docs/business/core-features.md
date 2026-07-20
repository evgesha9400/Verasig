# Core Features

## MVP Scope

- User-owned Telegram source sessions and public/private feed capture.
- Immutable raw-message history with resumable and full-history capture modes.
- Server-side template mining over the captured corpus and parser overlay.
- Immutable, revisioned `MiningReview` snapshots for Mine, Review, and Verify.
- Atomic confirmation of accepted templates into the feed's `signal` projection.
- Durable confirmed and suspected deleted-signal evidence.
- Historical signal simulation against public Bybit market data.
- Recomputable, evidence-referenced provider scorecards.
- Signed-up-user feed, signal, and provider dashboard views.

## MVP Exclusions

- Live execution.
- Demo execution.
- Programmatic observe -> demo -> live promotion state.
- Discord.
- Image extraction.
- Multimodal extraction.
- AI-generated trading strategies.
- Portfolio allocation.
- Fully autonomous incident repair.
- Multi-user production tenancy.
- Public marketplace.

## Feature Contracts

- Capture contract: provider messages become immutable, user-owned `raw_message` rows.
- Mining contract: captured messages plus the parser overlay produce an immutable `MiningReview` with `reviewId` and `inputRevision`.
- Confirmation contract: the addressed current review plus accepted template keys atomically replaces `signal`, records confirmed review evidence, and marks the feed verified.
- Signal contract: every persisted `Signal` is keyed directly to its source message; a miss is the absence of a signal row.
- Deletion contract: a live snapshot compared with durable capture produces retained deletion evidence; only confirmed signal deletions affect quality.
- Simulation contract: a signal or folded lifecycle plus historical klines produces an observe-only outcome under an explicit execution policy.
- Scorecard contract: durable capture, confirmed review misses, signals, simulations, audience proxies, and deletion evidence produce a recomputable explanation with evidence references.

## MVP Metrics

- Raw-message capture completeness: 100 percent of messages available to the authorized user session within the selected history depth.
- Confirmed-review precision: target 95 percent before any execution expansion.
- Confirmed-review recall: target 70 percent before any execution expansion.
- Provider-score explainability: every measured component traces to durable evidence.
- Pilot signal sources: at least 3.
- Pilot users or channel owners: at least 3.
- Paid-intent threshold: at least 2 buyers willing to pay for proof.
