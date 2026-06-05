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
A `RawTelegramMessage` the candidate filter flagged as a signal candidate, plus the exact text slice handed to extraction. An **advisory** subset — it sets priority/triage (what the LLM and the operator UI see), not eligibility; deterministic parsing may still run over all messages, and a `RawSignalEvent` may be **late-materialized** when a background parse or audit finds a missed signal ([ADR 0005](../adr/0005-distilled-filter-and-advisory-gate.md)).
_Avoid_: signal, raw message. Note: this **supersedes** the old definition where `RawSignalEvent` meant "original source content" — that role now belongs to `RawTelegramMessage`.

**Candidate filter**:
The recall-first, **advisory** stage that flags a `RawTelegramMessage` as a `RawSignalEvent`. Over-includes on purpose; precision is recovered downstream. It runs a cheap hand-coded **seed heuristic** for cold start, then provider-specific `FilterRule`s distilled from the golden corpus. Not a hard gate ([ADR 0005](../adr/0005-distilled-filter-and-advisory-gate.md)).

### Extraction

**TradeIntent**:
The provider's trade as parsed from message text — direction and price levels, independent of which message it came from. Required: `symbol` and `side`; optional: entry, stop, targets, leverage, provider-stated confidence. This is what **both** the deterministic parser and the LLM fallback produce; it carries **no** event linkage and **no** extraction provenance.
_Avoid_: signal, order, trade (bare).

**ExtractedSignal**:
A `TradeIntent` **recorded against** a `RawSignalEvent` — the canonical extraction output. Adds the event linkage (`event_id`, `channel_id`), the lifecycle role (`event_type`, defaulting `NEW_ENTRY` at extraction), and the provenance (`extraction_method`, `rule_id`). The extractors supply only the `TradeIntent`; the `ExtractService` attaches everything else. Replaces the docs' old term `Signal`.
_Avoid_: Signal, parsed signal, trade.

**UnrecognizedSignal**:
The outcome when extraction (deterministic + fallback) fails to produce an `ExtractedSignal` from a `RawSignalEvent`. Evidence of a parser gap.
_Avoid_: failed signal, error.

**side**:
Trade direction, normalized to `LONG` or `SHORT`. `buy` maps to `LONG`, `sell` maps to `SHORT`.

**Signal lifecycle**:
The ordered chain of an entry `ExtractedSignal` plus later modification/close messages that reference it (via Telegram `reply_to`). A signal is multi-message **only when explicit linking evidence exists** — no phantom lifecycles. A complete one-shot signal stays single. Folded into a `FoldedSignal` by the lifecycle service.

**SignalModification**:
A later message in a signal's reply chain that patches the live position — move stop (incl. to breakeven), set/move take-profits, **scale in (average) or reduce by a stated multiplier**, or fully close. Classified `MODIFY` or `CLOSE`. A modification need **not** be an `ExtractedSignal` (a reply like "move SL to BE" carries no `side`); it is recognized at fold-time from the `reply_to` chain, not by the parser.
_Avoid_: edit, correction.

**FoldedSignal**:
The folded view of a `Signal lifecycle`: the entry plus its applied modifications as a time-ordered timeline of the **effective** stop, take-profits, position size, and average entry (after any averaging-in or reduction). Derived and recomputable from durable inputs — never stored. A standalone complete signal folds to a single-step timeline.
_Avoid_: merged signal, final signal.

### Parsing rules

**FilterRule**:
A declarative, versioned, provider-specific **inclusion** rule (recall-first include/exclude patterns) deciding whether a `RawTelegramMessage` is a `RawSignalEvent`. Distilled from `GoldenLabel.is_signal`; shares a regex engine with `ParserRule` but is a distinct entity — it decides inclusion, the parser maps fields.
_Avoid_: candidate regex, keyword list (those are the cold-start seed, not the distilled rule).

**ParserRule**:
A declarative, versioned, provider-specific **extraction** rule (ordered patterns + field map + normalization), with an optional named Python extractor as an escape hatch. Distilled from `GoldenLabel.expected` fields via human-assisted distillation, never autonomously mined.
_Avoid_: parser, regex, grammar.

**Distillation loop**:
The human-assisted UI cycle: operator highlights signal messages → AI distills both a `FilterRule` (from `is_signal`) and `ParserRule`s (from `expected` fields) from the examples → rules applied and matched messages filtered → residue re-presented → repeat until the operator is satisfied. One labeling pass, two objectives; the human labels become the golden corpus.

**Golden corpus**:
The operator-labeled set of messages (signal / not-signal + expected fields) used as ground truth for parser precision and recall.

**ParserDriftWarning**:
A record emitted whenever deterministic parsing misses but LLM fallback succeeds — signalling the deterministic rules have fallen behind a provider's format. One warning per fallback success.
_Avoid_: parser error, fallback log.

**FilterDriftWarning**:
A record emitted whenever the candidate filter missed a message that later proved to be a signal — a background deterministic parse, an operator audit, or the LLM found a signal the filter did not flag. Surfaces filter false negatives so they feed back into the next distillation; symmetric to `ParserDriftWarning`.
_Avoid_: filter error, missed-candidate log.

### Deletion

**DeletedSignalEvidence**:
Proof that a message a provider posted later disappeared — typically a losing signal erased to clean up a track record. Two confidence tiers:
- `CONFIRMED` — a message we had **captured** is now absent from the channel; its original content is **retained** as proof.
- `SUSPECTED` — a gap in the message numbering, absent from **both** our capture and the channel now; a likely pre-capture deletion whose content we never had.
Only deletions of **signal** messages feed a provider's `ProviderScore`; deleting non-signal chatter counts for nothing. `SUSPECTED` evidence is reported per `TelegramChannel`.
_Avoid_: deletion, removed message.

**Rescan**:
Re-reading a `TelegramChannel`'s **current** live message set and comparing it to what we captured, to find `DeletedSignalEvidence`. The capture layer is append-only, so a deletion is only visible by this live comparison — never by re-reading our own store.
_Avoid_: re-backfill (that is capture, which never re-reads), refetch.

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
