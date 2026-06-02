# Business Decomposition

## Core Thesis

- Deltalytic should be a platform end-state.
- The first business should not be the platform.
- Each wedge must survive as a product on its own.
- Shared contracts must make later integration cheap.

## Product Wedges

| Order | Wedge | Status | Reason |
|---:|---|---|---|
| 1 | `Verasig` | build first | narrow pain, direct current docs fit, proprietary dataset |
| 2 | `StrategyOps` | internal first | needed for safe operation, weak standalone wedge |
| 3 | `Research Lab` | later | crowded, stronger after Signal Lake exists |
| 4 | `PortfolioOps` | later | only valuable after multiple profitable strategies exist |
| 5 | `InfraOps` | internal only | strong incumbents, not trading-specific enough |
| 6 | Unified GUI | integration layer | not a business without a wedge |

## Verasig

- Job: convert social trading signals into audited data and measured demo outcomes.
- Buyer: signal trader.
- Seller angle: signal channel owner with verifiable scorecard.
- Differentiator: raw-message provenance plus performance attribution.
- Integration path: Signal Lake feeds Research Lab.

## StrategyOps

- Job: monitor strategy runtime health and repair safe operational failures.
- Buyer: internal operator first.
- Seller angle: advanced managed trading user later.
- Differentiator: trading-specific control states, kill switch, gateway caps, audit.
- Integration path: incident events trigger strategy operations agents.

## Research Lab

- Job: turn hypotheses and stored data into tested strategy candidates.
- Buyer: quant builder.
- Seller angle: signal trader graduating from passthrough to filtered strategies.
- Differentiator: includes historical social signals as an alternative dataset.
- Integration path: promoted strategy plugs into existing execution runtime.

## PortfolioOps

- Job: allocate capital across strategies based on risk and performance.
- Buyer: user with multiple live strategies.
- Seller angle: managed multi-strategy account.
- Differentiator: allocation uses live execution and research evidence.
- Integration path: StrategyOps supplies health state and Research Lab supplies candidates.

## InfraOps

- Job: keep Deltalytic infrastructure healthy.
- Buyer: internal operator.
- Seller angle: none initially.
- Differentiator: trading-specific remediation constraints.
- Integration path: infra incidents feed agent orchestration.

## Unified GUI

- Job: present ingestion, strategies, incidents, research, and portfolio state.
- Buyer: every product user.
- Seller angle: none independently.
- Differentiator: coherent control surface after wedges validate.
- Integration path: one UI shell over shared contracts.
