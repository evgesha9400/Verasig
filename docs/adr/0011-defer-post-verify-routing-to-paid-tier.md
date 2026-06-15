# Defer the post-verify routing chain to a higher subscription tier

We will not wire the Exchange (connect/route), Execution (risk configuration), or
Backtest steps to the backend in this pass. They remain frontend placeholders and
become advanced features reserved for a higher subscription plan. Label, Distill,
and Verify are wired to the backend now; the wired core flow ends at a verified
source.

We chose this because the immediate goal is a working, honest end-to-end flow on
real data, and the entire chain after verification — route signals to an exchange,
size execution, backtest — is where the most product and engineering risk sits for
the least near-term value:

- Exchange access is already plan-gated in `features/accounts/plans.py`
  (`exchanges`: `OBSERVER` 0 / `OPERATOR` 1 / `DESK` unlimited), so connecting an
  exchange is by definition a paid capability.
- The backend `RiskConfigBody` stores eight fields, but `ExecutionView` exposes
  many more controls (take-profit split mode, fallback stop/target, follow-author
  updates, break-even-after-TP1, the ladder preview). Wiring only the eight would
  ship a UI that silently drops the rest.
- The Backtest `done` payload returns only `score`, `winRate`, and `pnl`, while
  the results screen also shows max drawdown and average latency, which have no
  backend source.
- Backtest depends on a configured risk model and a connected exchange, so it sits
  at the end of the value chain where correctness matters most and is hardest to
  verify quickly.

Treating the whole post-verify routing chain as one higher-tier upsell keeps the
core flow — learn the rules, verify the source — clean and shippable on real data.

## Considered options

- **Wire Exchange now, defer only Execution + Backtest**: rejected. Exchange is
  the entry point to the deferred chain and is already plan-gated, so wiring it in
  isolation would dangle a connected exchange with no execution or backtest behind
  it.
- **Wire only the persistable risk subset**: rejected. Persisting eight of many
  controls produces a misleading UI and invites bug reports about settings that do
  not take effect.
- **Extend the backend to cover every control + drawdown/latency, then wire the
  whole chain**: viable but deferred. It is the most complete option and is the
  intended path for the paid-tier build, but it grows backend scope and a migration
  before the core flow is proven on real data.
- **Remove the steps from the UI entirely**: rejected. The placeholder preserves
  the flow's shape and doubles as the upsell surface.

## Consequences

- `ProductApp` renders a shared upsell placeholder for the `exchange`, `risk`,
  `backtest`, and `backtest-result` screens.
- `ExchangeView`, `ExecutionView`, and `BacktestView` are retained unchanged as the
  starting point for the future paid-tier implementation; they are simply not
  mounted in the flow.
- Verify's pass screen no longer promises exchange routing or backtesting. Its
  primary action keeps the source verified; the routing path points at the
  placeholder.
- When Backtest is eventually built, its drawdown and latency cards stay marked as
  "sample" until the backend computes them.
- Future continuation: wire Exchange behind the plan gate, extend `RiskConfigBody`
  + storage to cover the remaining Execution controls, extend the backtest summary
  with drawdown/latency, then wire all three views behind the plan gate.
