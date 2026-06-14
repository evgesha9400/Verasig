# Pipeline flow — feed onboarding

The core workflow takes a Telegram feed from "connected" to "live-ready" through a fixed pipeline. The stepper shows: **Backfill → Label → Distill → Verify → Exchange → Execution → Backtest**.

## Screens & transitions

```
Sources ──connect──▶ Telegram setup ──▶ Chats (feed list)
                                          │ start backfill
                                          ▼
                                       Backfill ──cancel──▶ Chats (status: cancelled, resumable)
                                          │ complete (status: backfilled)
                                          ▼
                                        Label  ◀──────────────┐
                                          │ distill           │ refine loop
                                          ▼                   │ (verifyAttempt++)
                                        Distill               │
                                          │ complete          │
                                          ▼                   │
                                        Verify ──loop─────────┘
                                          │ pass                  │ stop here
                                          ▼                       ▼
                                        Exchange            Chats (status: verified)
                                          │ Bybit connected
                                          ▼
                                        Execution  (screen id: `risk` — kept for state compat)
                                          │ run backtest
                                          ▼
                                        Backtest ──complete──▶ Chats (status: analyzed, scored)
```

## Feed statuses

| Status        | Meaning                                      | Available actions                         |
| ------------- | -------------------------------------------- | ----------------------------------------- |
| `new`         | Listed, never processed                      | Start backfill                            |
| `backfilling` | History pull in progress                     | Cancel (saves progress)                   |
| `cancelled`   | Backfill paused mid-pull                     | Resume / restart                          |
| `backfilled`  | History complete, not yet labeled            | Continue to Label                         |
| `verified`    | Rules verified, user stopped before backtest | Backtest any time (re-enters at Exchange) |
| `analyzed`    | Backtested, scored                           | View results, re-analyze, go live         |

## Step-back rules

- Going back to **Label** from any step past Verify requires confirmation: changing labels invalidates the distilled ruleset; Distill and Verify re-run. **Exchange and Execution settings are kept.**
- The Execution screen keeps the internal id `risk` so persisted localStorage state survives the rename.

## Naming

The step was renamed **Risk → Execution** (Jun 2026). Rationale: the step configures the full trade lifecycle (sizing, entry, exit), of which classic "risk management" is only one part. See `execution-step.md`.
