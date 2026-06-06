# Conservative, observe-only simulation behind a pluggable ExecutionPolicy

Provider outcomes are computed by replaying signals against Bybit public historical klines — never via demo or live orders. The model is deliberately conservative: when a 1m candle spans both stop and target, the tie resolves stop-first (worst case), and outcome is an R-multiple when a stop exists, else mark-to-market at a hold-window expiry. The simulator separates the immutable signal from a pluggable `ExecutionPolicy`; v0 ships `ProviderStatedPolicy` (uses the provider's own risk management).

We chose conservatism because Verasig is a *proof* product: a slightly pessimistic, clearly-stated model is defensible and resists "you inflated my numbers" disputes, whereas an optimistic tie-break would systematically flatter providers and undermine the value proposition. We made the policy pluggable so a future strategy can ignore the provider's risk management and apply our own without reworking the engine.

## Consequences

- Reported outcomes may slightly under-rate providers on ambiguous candles — stated openly in the explanation.
- Klines are public REST data: no exchange credentials, fully local, no order placement.
- "Score by realized demo outcome" (value-proposition.md) is reinterpreted as "score by simulated outcome".
