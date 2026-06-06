# Architecture Decisions

## ADR-BIZ-001 - Platform Is End-State, Not MVP

- Decision: build `Verasig` first.
- Reason: the full platform is too broad to validate.
- Consequence: every other wedge is internal until observe-only scoring proves value.

## ADR-BIZ-002 - Signal Is A First-Class Dataset

- Decision: store raw events and canonical Signals append-only.
- Reason: performance truth depends on reconstructable evidence.
- Consequence: auto-research can later use Signals like market data.

## ADR-BIZ-003 - Execution Stays Outside The MVP

- Decision: first validation uses observe-only provider scoring.
- Reason: business value is proof before any execution.
- Consequence: demo and live trading become later regulated and risk-controlled features.

## ADR-BIZ-004 - Execution Lifecycle Is Future-Compatible

- Decision: future signal sources move through observe -> demo -> live.
- Reason: Verasig must prove provider quality before any execution.
- Consequence: promotion and demotion must be programmatic so UI and agents can manage it later.

## ADR-BIZ-005 - InfraOps Is Internal

- Decision: agentic infrastructure management is not an external product first.
- Reason: AI incident management is already contested by incident.io, PagerDuty, Datadog, Rootly, and others.
- Consequence: Deltalytic keeps InfraOps as internal reliability capability.

## ADR-BIZ-006 - Research Lab Follows Signal Lake

- Decision: auto-research comes after Verasig.
- Reason: QuantConnect and Capitalise already cover generic research and automation.
- Consequence: Deltalytic Research Lab differentiates by using historical social signals.

## ADR-BIZ-007 - PortfolioOps Requires Multiple Proven Strategies

- Decision: portfolio allocation stays outside the MVP.
- Reason: allocation has no value until multiple strategies have real performance history.
- Consequence: portfolio agent starts as analysis-only.

## ADR-BIZ-008 - Compliance Copy Is Conservative

- Decision: product copy avoids profit guarantees and investment advice.
- Reason: regulators flag AI trading bots and signal schemes as scam vectors when returns are promised.
- Consequence: marketing language centers audit, controls, and evidence.
