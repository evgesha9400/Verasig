# Project Structure Protocol

## Business Docs

```text
docs/business/
|-- README.md
|-- market-research.md
|-- business-decomposition.md
|-- value-proposition.md
|-- requirements.md
|-- core-features.md
|-- validation-roadmap.md
|-- architecture-decisions.md
`-- project-structure.md
```

## Product Layers

```text
Verasig/
|-- docs/
|   |-- business/                 # product thesis and validation records
|   |-- context/                  # domain glossary
|   |-- adr/                      # architecture decisions
|   `-- work/                     # implementation plans
|-- backend/
|   |-- app/foundation/           # config, database, auth, Telegram session, Bybit metadata
|   `-- app/services/             # ingestion, extraction, scoring, promotion, dashboard APIs
|-- frontend/
|   `-- app/                      # signed-up-user provider performance dashboard
|-- containers/
|   `-- extractor-agent/          # history mining and parser-rule generation
`-- workers/
    |-- telegram-ingestion/       # public/private channel history and live capture
    |-- signal-extraction/        # deterministic parser plus LLM fallback
    `-- provider-scoring/         # PnL, active users, drawdown, deleted-signal behaviour
```

## Future Verasig Service Shape

```text
backend/app/services/signals/
|-- api.py                        # signed-up-user signal and provider endpoints
|-- models.py                     # RawSignalEvent, Signal, ProviderScore, PromotionState
|-- schemas.py                    # request and response contracts
|-- telegram_ingestion_service.py # channel history and live event capture
|-- extractor_service.py          # raw event to canonical Signal
|-- parser_rule_service.py        # provider-specific deterministic parser rules
|-- llm_fallback_service.py       # unsupported-format extraction
|-- lake_service.py               # append-only persistence
|-- promotion_service.py          # observe, demo, live state transitions
|-- scorecard_service.py          # provider and channel metrics
`-- __init__.py
```

## Naming Rules

- `signals` means trade signals.
- `failure_signal` means operational failure indication.
- `RawTelegramMessage` stores original source content (every message, append-only). [docs/adr/0001]
- `RawSignalEvent` stores a signal-candidate message plus the text slice fed to extraction. [docs/adr/0001]
- `ExtractedSignal` stores canonical extracted trading intent (was `Signal`).
- `PromotionState` stores observe, demo, or live status for a provider source.
- `ExecutionDecision` stores no-op, demo action, live action, or rejection.
- `SignalScore` stores channel or provider performance.
