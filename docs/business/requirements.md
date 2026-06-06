# Requirements

## Assumptions

- The first product line is `Verasig`.
- The first source is Telegram app ingestion.
- The first Telegram targets are public channels and private channels.
- The first operating mode is observe-only.
- The first buyer is a trader, not an enterprise.
- The first validation target is proof of signal quality, not live profit.
- The first market-data venue is Bybit.
- The first symbol scope is every Bybit-supported trading pair for scoring.
- The first global market stance is tooling-only.
- The tooling-only stance requires jurisdiction research before paid launch.
- Demo and live execution stay outside scope until observe-only scoring proves value.
- Future execution promotion and demotion must be programmatic.
- Signed-up users should get a provider performance dashboard.

## User Stories

- As a trader, I want every Telegram signal captured so I can audit what happened.
- As a trader, I want public Telegram channels captured so I can assess open signal providers.
- As a trader, I want private Telegram channels captured so I can assess paid signal providers.
- As a trader, I want Telegram app ingestion so channels that reject bots are still supported.
- As a trader, I want historical channel messages extracted so provider history can be evaluated before live monitoring.
- As a trader, I want each raw message parsed into a canonical Signal so I can compare sources consistently.
- As a trader, I want unrecognized messages stored so parsing gaps are visible.
- As a trader, I want unsupported signal formats extracted by an LLM fallback so new provider formats are not silently missed.
- As a trader, I want unsupported signal formats logged as warnings so parser drift is visible.
- As a trader, I want observe-only provider scorecards so I can judge signal sources before any execution.
- As a trader, I want every extraction warning logged so I can separate provider drift from parser defects.
- As a trader, I want channel-level performance metrics so I can decide which source deserves attention.
- As a trader, I want provider scores so I can compare signal providers with one primary metric.
- As a signed-up user, I want a provider performance dashboard so I can inspect signals before trusting a source.
- As a signed-up user, I want provider scores based on PnL, active user count, drawdown, and deleted-signal behaviour so score manipulation is harder.
- As a trader, I want symbol, side, entry, stop, targets, and confidence extracted so I can review trade structure.
- As a trader, I want any Bybit-supported pair recognized so provider scoring is not limited to BTC or ETH.
- As a signal seller, I want an evidence-backed performance page so subscribers can inspect results.
- As an operator, I want raw and canonical signal storage so future research can reuse the dataset.
- As an operator, I want a human-assisted distillation loop to mine historical messages so I can confirm provider-specific signal formats. [see docs/adr/0002]
- As an operator, I want the distillation loop to turn my labeled examples into deterministic parser rules.
- As an operator, I want deterministic parser rules used before LLM extraction so normal processing is cheap and reproducible and fast.
- As an operator, I want parser drift warnings so agentic parser updates can be queued.
- As an operator, I want Telegram API and content-licensing compliance checked before paid public launch.

## Resolved Decisions

- Telegram channel scope: public channels and private channels.
- Telegram ingestion method: Telegram app user-account session first.
- Market-data venue scope: Bybit only first.
- Symbol scope: all Bybit-supported trading pairs for scoring.
- Signal grammar scope: structured text with provider-specific variation.
- Parser strategy: deterministic parser first.
- Parser generation: human-assisted distillation — operator labels examples, LLM distills declarative rules (not autonomous). [docs/adr/0002]
- Parser fallback: LLM extraction for unsupported formats.
- Parser drift handling: log warning and queue parser improvement.
- Primary outcome metric: provider score.
- Provider-score inputs: PnL, active user count, drawdown, and deleted-signal behaviour.
- First buyer: trader paying for proof.
- Geography: global crypto users.
- Compliance stance: tooling-only until research disproves it.
- Execution lifecycle: outside scope until observe-only scoring proves value.
- Promotion control: outside scope.
- Promotion UI: outside scope.
- Promotion agents: outside scope.
- Signed-up user dashboard: included.

## Open Research Questions

- Does Telegram's Content Licensing and AI Scraping Terms allow LLM extraction over user-authorized channel history?
- Does Telegram's Content Licensing and AI Scraping Terms allow agentic parser-rule generation from channel history?
- Which Telegram API rate and behaviour limits apply to user-account session history extraction?
- Which jurisdictions create risk when a paid SaaS scores crypto signal providers?
- Which jurisdictions create risk when a paid SaaS enables live signal execution?
- Which user geographies should be blocked or delayed before paid launch?
- Which provider-score formula best predicts future signal usefulness?
