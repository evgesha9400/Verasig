# Value Proposition

## Product

- Name: `Verasig`.
- Category: signal performance operating system.
- First surface: web dashboard.
- First source: Telegram.
- First exchange mode: observe-only (simulated outcomes; no execution). [docs/adr/0003]

## Customer

- Primary buyer: crypto trader using Telegram or Discord signal groups.
- Secondary buyer: signal channel owner.
- Excluded buyer: institutional quant team.
- Excluded buyer: generic SRE team.
- Excluded buyer: non-technical retail investor seeking financial advice.

## Pain

- Signal groups make performance claims without clean proof.
- Traders cannot reconstruct every raw message.
- Traders cannot measure missed, late, malformed, or rejected signals.
- Traders cannot compare signal providers with the same execution rules.
- Traders cannot safely move from social signals to automated execution.

## Promise

- Capture every raw signal.
- Parse every recognized trade signal.
- Simulate outcomes against historical market data only; no execution.
- Log every order intent and gateway decision.
- Score each channel by simulated outcome (conservative, evidence-backed). [docs/adr/0003]
- Preserve data for later strategy research.

## Non-Promise

- No guaranteed returns.
- No investment advice.
- No black-box live autonomy at MVP.
- No exchange credential handling at MVP.
- No channel quality claims without stored evidence.

## First Pricing Hypotheses

- Self-serve trader: USD 29-99 per month.
- Power trader: USD 149-299 per month.
- Signal seller dashboard: USD 199-499 per month.
- Usage meters: channels, raw events, parsed signals, backtesting runs, exchanges.
- Initial validation metric: paid intent before live trading support.

## Strongest Differentiator

- Competitors execute signals.
- Deltalytic should prove signals.
