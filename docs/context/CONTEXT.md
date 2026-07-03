# Verasig

Proof-first signal-provider verification. This context covers ingesting Telegram trading signals, extracting them into a canonical form, and scoring the providers by evidence. Terms below are the canonical vocabulary; use them exactly.

## Language

### Sources & capture

The capture layer is **user-owned and provider-agnostic**. A user connects a **Source** (a provider account — Telegram is the only one today) and follows **Feed**s through it; a feed's captured messages are **raw_message**s. Everything a user captures is keyed by `user_id`, so deleting a feed — or the source above it — removes that user's capture and derived rows, and a re-add starts clean from a NULL cursor. "Telegram" lives only in the single adapter and in opaque `config`/`metadata`, never in a table or column name; provider ids are stored generically as `external_id` / `external_message_id`. In code the Telegram adapter still speaks the domain objects below (`TelegramChannel`, `RawTelegramMessage`); the **repository layer is the only place that translates** them to that generic storage. See [ADR 0012](../adr/0012-user-owned-generic-source-feed-model.md).

**Source**:
A user's connection to a signal provider — Telegram today (`name` is constrained to it). Holds connection `status` (`pending` → `connected`) and an encrypted `config` (the provider secrets). A user has at most one source per provider; deleting it cascades every feed beneath it.
_Avoid_: account, integration, channel.

**Feed**:
A stream a user follows through a `Source` — **user-owned**, keyed by `user_id` + the provider stream id. Collapses what used to be a shared channel record plus a separate membership row into one entity that also carries the backfill cursor and provider `metadata` (handle, private flag, subscriber count). The API and UI call this a **feed**; in code its resolved form is a `TelegramChannel`.
_Avoid_: subscription, chat, channel cache.

**Fetch new messages**:
Resume capture for a `Feed` from its current cursor. It updates captured messages and deletion evidence, but does **not** invalidate existing labels, verification, or analysis by default; re-labeling and re-verification are user-initiated through **Review labels**. Contrast **Re-fetch full history**, which starts capture over from scratch.
_Avoid_: re-label, re-verify, reset.

**Re-fetch full history**:
Start a `Feed`'s capture over as a new generation ([ADR 0014](../adr/0014-full-refetch-wipes-and-recaptures.md)). It first secures deletion evidence (a mandatory pre-wipe `Rescan`, aborting on an empty live snapshot), then atomically wipes the feed's captured messages and cascaded derived rows and clears the cursor, then recaptures at the chosen **History depth**. The message counter restarts at zero. `DeletedSignalEvidence`, distilled/mined rules, and backfill-run history survive; golden labels (tied to the wiped messages) do not. This is the only way to deepen a shallow capture. Append-only capture ([ADR 0001](../adr/0001-two-layer-raw-capture.md)) still holds **within** a generation.
_Avoid_: reset (that is feed delete), rebackfill-as-no-op (the old FULL semantics).

**History depth**:
How far back a fresh capture reaches: `6m`, `1y` (default), or `all`. Applied only to a fresh capture (NULL cursor) — a resume is cursor-bound and ignores it. Deepening later is a **Re-fetch full history**, not a resume. Stored per `Feed`.
_Avoid_: range, window, lookback (unqualified).

**TelegramChannel**:
The Telegram adapter's domain view of a `Feed` — a monitored public or private channel a provider posts signals to, identified by its Telegram channel id. Persisted as a user-owned `feed` row (`external_id`); the in-code object keeps `channel_id`.
_Avoid_: group, chat.

**RawTelegramMessage**:
One captured message exactly as received, stored immutably and append-only. The 100%-capture layer. Carries provenance, text, sender, timestamps, `reply_to`, and media-present flags. Persisted user-owned as a `raw_message` row (`external_id` / `external_message_id`).
_Avoid_: message record, raw event (that is something else — see below).

**RawSignalEvent**:
A `RawTelegramMessage` the candidate filter flagged as a signal candidate, plus the exact text slice handed to extraction. An **advisory** subset — it sets priority/triage for later review and LLM use, not eligibility; deterministic parsing may still run over all messages, and a `RawSignalEvent` may be **late-materialized** when a background parse or audit finds a missed signal ([ADR 0005](../adr/0005-distilled-filter-and-advisory-gate.md)).
_Avoid_: signal, raw message. Note: this **supersedes** the old definition where `RawSignalEvent` meant "original source content" — that role now belongs to `RawTelegramMessage`.

**Candidate filter**:
The recall-first, **advisory** step that flags a `RawTelegramMessage` as a `RawSignalEvent`. Over-includes on purpose; precision is recovered downstream. It runs a cheap hand-coded **seed heuristic** for cold start, then provider-specific `FilterRule`s distilled from the golden corpus. Not a hard gate ([ADR 0005](../adr/0005-distilled-filter-and-advisory-gate.md)).

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
A declarative, versioned, provider-specific **inclusion** rule (recall-first include/exclude patterns) deciding whether a `RawTelegramMessage` is a `RawSignalEvent`. Produced by **Mining confirm** (from accepted `Template family`s) or the legacy `Distillation loop` (from signal `GoldenLabel.label`s); mined rules carry an empty `distilled_from_label_ids`. Shares a regex engine with `ParserRule` but is a distinct entity — it decides inclusion, the parser maps fields.
_Avoid_: candidate regex, keyword list (those are the cold-start seed, not the persisted rule).

**ParserRule**:
A declarative, versioned, provider-specific **extraction** rule (ordered patterns + field map + normalization), with an optional named Python extractor as an escape hatch (server-side only — never accepted from the Mining wire). Produced by **Mining confirm** or the legacy `Distillation loop`; `GoldenLabel.expected` fields tighten deterministic validation when present.
_Avoid_: parser, regex, grammar.

**Distillation loop**:
The **legacy** human-assisted labeling cycle: operator classifies messages → AI distills both a `FilterRule` (from labels) and `ParserRule`s (from labelled signal text, tightened by `expected` fields when present) → backend validation applies the rules against the golden corpus. One labeling pass, two objectives; the human labels become the golden corpus. Superseded in the product by **Template mining** ([ADR 0013](../adr/0013-mining-wizard-replaces-label-distill-verify-frontend.md)); both write the same rule tables.

**Template mining**:
The parser-first alternative to the `Distillation loop`: the browser runs the deterministic parser over a `Feed`'s captured messages, groups them into `Template family`s, and lets the operator accept or reject each family. Replaced the Label/Distill/Verify screens ([ADR 0013](../adr/0013-mining-wizard-replaces-label-distill-verify-frontend.md)).
_Avoid_: distillation, labeling (that is the legacy loop).

**Template family**:
A group of a `Feed`'s messages sharing one normalized format (a signal template), mined by **Template mining**. Accepting a family validates every message in it at once; one decision, not per-message labels.
_Avoid_: cluster, group (unqualified).

**Mining confirm**:
Committing the accepted `Template family`s: the browser compiles them into a `FilterRule` + `ParserRule`s and POSTs them; the backend persists the ruleset (replacing the feed's prior version), re-derives candidates and extraction, recomputes deletion-evidence candidacy from the rules, and marks the `Feed` **verified** ([ADR 0015](../adr/0015-mining-confirm-persists-rules-and-rederives.md)). This is when Mining decisions become authoritative for live extraction and scoring.
_Avoid_: verify, distill, save.

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
Re-reading a `TelegramChannel`'s **current** live message set and comparing it to what we captured, to find `DeletedSignalEvidence`. The capture layer is append-only, so a deletion is only visible by this live comparison — never by re-reading our own store. A **Re-fetch full history** runs a Rescan first, to secure evidence before it wipes.
_Avoid_: refetch (capture re-reads its own store only as part of **Re-fetch full history**).

### Scoring

**ProviderScore**:
A re-weightable, normalized composite quality score per provider/channel, **recomputed on demand from durable evidence and never stored** (like a `FoldedSignal`). Components: simulated expectancy, drawdown, deletion behaviour, signal frequency, completeness, parser confidence, evidence availability, active-user proxy. A plain weighted-normalized sum over only the components currently backed by evidence, so it is **honestly partial** until simulation supplies expectancy + drawdown. v0 weights are a placeholder, not claimed optimal.
_Avoid_: rating, rank, grade.

**ProviderScoreExplanation**:
The breakdown tracing every `ProviderScore` component, weight, and input back to the evidence that produced it — each measured component carries `evidence_refs` to the exact rows used to measure it (numerator and denominator). Every score change must be reconstructable from it. Recomputed alongside the score, not stored.
_Avoid_: report, summary.

**Active-user proxy**:
The best available stand-in for provider audience size, since Telegram exposes no true active-user count: subscriber count, median post views, and forwards (**reactions are not captured**). Always labelled a proxy, never a quality claim.
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
- **chat vs feed vs channel**: the user-followed stream is a `Feed` (the API/UI term + the storage row); its in-code domain object is `TelegramChannel` (keeps `channel_id`); a `Source` is the connection above it. "chat" is retired from the wire — the old `/chats` API is now `/feeds`.
- **`signals` vs `failure_signal`**: `signals` always means trade signals; `failure_signal` (operational failure indication) is out of Verasig's scope.
- **"Demo outcome" (value-proposition.md)**: there is no demo execution. "Outcome" means `Simulated outcome` from historical klines.
- **"Local-only"**: means everything runs in Docker via `docker compose` on any machine with Docker — not "no servers." A Postgres container is in scope.

## Design references

Frontend and execution-engine design specs live in [`docs/design/`](../design/):

- [execution-adaptivity.md](../design/execution-adaptivity.md) — how the Execution step adapts its controls to what a feed actually posts: corpus-driven display gates plus the per-signal engine matrix. Visual companion: `execution-adaptivity-decision-tree.html`.

## Example dialogue

> **Operator:** This channel posted "BTC long, 65k" with no stop. Is that a bad signal?
> **Domain expert:** It's an incomplete `ExtractedSignal` — `symbol` and `side` are present, so it's recognized, not an `UnrecognizedSignal`. But check the `Signal lifecycle`: if a later message replied to it adding a stop, the folded signal is complete.
> **Operator:** And if they deleted the original after it went against them?
> **Domain expert:** If we'd captured it first, the re-scan produces `CONFIRMED` `DeletedSignalEvidence` with the original text retained — that feeds the deletion-behaviour component of their `ProviderScore`. If we never captured it, the best we get is a `SUSPECTED` id-gap.
> **Operator:** How do we know it actually made money?
> **Domain expert:** We don't claim that. We compute a `Simulated outcome` against Bybit klines under the `ProviderStatedPolicy`, conservative on ties, and show the `R-multiple`. Every number traces back through the `ProviderScoreExplanation`.
