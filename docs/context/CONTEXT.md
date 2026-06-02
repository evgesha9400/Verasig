# Verasig

Proof-first signal-provider verification. This context covers ingesting Telegram trading signals, extracting them into a canonical form, and scoring the providers by evidence. Terms below are the canonical vocabulary; use them exactly.

## Language

### Sources & capture

**TelegramChannel**:
A monitored Telegram public or private channel that a provider posts signals to. Identified by its Telegram channel id.
_Avoid_: group, chat, feed.

**RawTelegramMessage**:
One captured message exactly as received, stored immutably and append-only. The 100%-capture layer. Carries provenance, text, sender, timestamps, `reply_to`, and media-present flags.
_Avoid_: message record, raw event (that is something else — see below).

**RawSignalEvent**:
A `RawTelegramMessage` that a cheap candidate filter flagged as a signal candidate, plus the exact text slice handed to extraction. A subset of messages — chatter never becomes one.
_Avoid_: signal, raw message. Note: this **supersedes** the old definition where `RawSignalEvent` meant "original source content" — that role now belongs to `RawTelegramMessage`.

**Candidate filter**:
The cheap, recall-first heuristic that decides whether a `RawTelegramMessage` becomes a `RawSignalEvent`. Over-includes on purpose; precision is recovered downstream.

### Extraction

**ExtractedSignal**:
The canonical, flexible trading intent parsed from a `RawSignalEvent`. Required fields: `symbol` and `side` only. Everything else (entry, stop, targets, leverage, confidence) is optional. Replaces the docs' old term `Signal`.
_Avoid_: Signal, parsed signal, trade.

**UnrecognizedSignal**:
The outcome when extraction (deterministic + fallback) fails to produce an `ExtractedSignal` from a `RawSignalEvent`. Evidence of a parser gap.
_Avoid_: failed signal, error.

**side**:
Trade direction, normalized to `LONG` or `SHORT`. `buy` maps to `LONG`, `sell` maps to `SHORT`.

**Signal lifecycle**:
The ordered chain of an entry `ExtractedSignal` plus later modification/close events that reference it (via Telegram `reply_to`). A signal is multi-message **only when explicit linking evidence exists** — no phantom lifecycles. A complete one-shot signal stays single.

**SignalModification**:
A later extracted event that patches an earlier signal (e.g. add stop, move to breakeven, close). Classified as `modify` or `close`; references the original message.

### Parsing rules

**ParserRule**:
A declarative, versioned, provider-specific extraction rule (ordered patterns + field map + normalization), with an optional named Python extractor as an escape hatch. Hand-authored via human-assisted distillation, never autonomously mined.
_Avoid_: parser, regex, grammar.

**Distillation loop**:
The human-assisted UI cycle: operator highlights signal messages → AI distills `ParserRule`s from the examples → rules applied and matched messages filtered → residue re-presented → repeat until the operator is satisfied. The human labels become the golden corpus.

**Golden corpus**:
The operator-labeled set of messages (signal / not-signal + expected fields) used as ground truth for parser precision and recall.

**ParserDriftWarning**:
A record emitted whenever deterministic parsing misses but LLM fallback succeeds — signalling the deterministic rules have fallen behind a provider's format. One warning per fallback success.
_Avoid_: parser error, fallback log.

### Deletion

**DeletedSignalEvidence**:
Proof that a message a provider posted later disappeared. Two confidence tiers:
- `CONFIRMED` — a previously-captured message is now absent (snapshot-diff); original content is retained.
- `SUSPECTED` — an id-gap heuristic flagged a likely deletion; content was never captured.
_Avoid_: deletion, removed message.

### Scoring

**ProviderScore**:
A re-weightable, normalized composite score per provider/channel. Components: simulated expectancy, drawdown, deletion behaviour, signal frequency, completeness, parser confidence, evidence availability, active-user proxy. v0 weights are a placeholder, not claimed optimal.
_Avoid_: rating, rank, grade.

**ProviderScoreExplanation**:
The stored breakdown tracing every `ProviderScore` component, weight, and input back to the evidence that produced it. Every score change must be reconstructable from it.

**Active-user proxy**:
The best available stand-in for provider audience size, since Telegram exposes no true active-user count: subscriber count + median post views + reactions/forwards. Always labelled a proxy.
_Avoid_: active users, audience (unqualified).

### Simulation

**Simulated outcome**:
The result of replaying an `ExtractedSignal` (or folded lifecycle) against Bybit public historical klines under an `ExecutionPolicy`. No real or demo orders — observe-only. Conservative: same-candle stop+target ties resolve stop-first.

**ExecutionPolicy**:
The pluggable rule set that turns a signal into a simulated trade (entry fill, stop, targets, sizing, exit). v0 = `ProviderStatedPolicy` (uses the provider's own risk management). A future policy may override it with our own risk management.

**R-multiple**:
Trade outcome expressed as multiples of initial risk, where entry-to-stop distance = 1R. Used when a stop exists; otherwise outcome is mark-to-market % at hold-window expiry.

**MFE / MAE**:
Maximum favorable / adverse excursion over a signal's simulated life. MAE drives the drawdown component of the score.

## Flagged ambiguities

- **Signal**: ambiguous in older docs (raw vs parsed). Resolved: the canonical parsed object is `ExtractedSignal`; raw capture is `RawTelegramMessage`. The bare word "Signal" is retired.
- **`signals` vs `failure_signal`**: `signals` always means trade signals; `failure_signal` (operational failure indication) is out of Verasig's Stage 0 scope entirely.
- **"Demo outcome" (value-proposition.md)**: there is no demo execution at Stage 0. "Outcome" means `Simulated outcome` from historical klines.
- **"Local-only"**: means everything runs in Docker via `docker compose` on any machine with Docker — not "no servers." A Postgres container is in scope.

## Example dialogue

> **Operator:** This channel posted "BTC long, 65k" with no stop. Is that a bad signal?
> **Domain expert:** It's an incomplete `ExtractedSignal` — `symbol` and `side` are present, so it's recognized, not an `UnrecognizedSignal`. But check the `Signal lifecycle`: if a later message replied to it adding a stop, the folded signal is complete.
> **Operator:** And if they deleted the original after it went against them?
> **Domain expert:** If we'd captured it first, the re-scan produces `CONFIRMED` `DeletedSignalEvidence` with the original text retained — that feeds the deletion-behaviour component of their `ProviderScore`. If we never captured it, the best we get is a `SUSPECTED` id-gap.
> **Operator:** How do we know it actually made money?
> **Domain expert:** We don't claim that. We compute a `Simulated outcome` against Bybit klines under the `ProviderStatedPolicy`, conservative on ties, and show the `R-multiple`. Every number traces back through the `ProviderScoreExplanation`.
