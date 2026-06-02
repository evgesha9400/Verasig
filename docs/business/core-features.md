# Core Features

## MVP Scope

- Telegram app user-account session ingestion.
- Public and private Telegram channel history capture.
- RawSignalEvent append-only storage.
- Text extractor.
- Canonical Signal schema.
- Provider-specific deterministic parser rules.
- LLM fallback extraction for unsupported formats.
- Parser drift warning log.
- Signal Lake writer.
- Deleted-signal evidence capture.
- Channel performance scorecard.
- Signed-up-user provider dashboard.

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

- Ingestion contract: Telegram channel message in, RawSignalEvent out.
- Extractor contract: RawSignalEvent in, Signal out.
- Parser-rule contract: provider history in, deterministic parser rule out.
- LLM fallback contract: unsupported raw event in, extracted Signal or unrecognized Signal out.
- Store contract: Signal in, append-only persisted record out.
- Deleted-signal contract: historical message state in, deletion evidence out.
- Scorecard contract: raw events, signals, PnL, active-user estimates, drawdown, and deletion evidence in, provider metrics out.

## MVP Metrics

- Raw message capture completeness: 100 percent of Telegram messages available to the authorized user-account session.
- Signal extraction precision: target 95 percent before demo execution support.
- Signal extraction recall: target 70 percent before demo execution support.
- Parser drift warning coverage: 100 percent of LLM fallback extractions.
- Provider score explainability coverage: 100 percent of score changes trace to stored evidence.
- Pilot signal sources: at least 3.
- Pilot users or channel owners: at least 3.
- Paid-intent threshold: at least 2 buyers willing to pay for proof.
