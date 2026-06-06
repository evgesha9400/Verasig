# Observer Data Contracts

Canonical Pydantic contracts (`domain/`) + service interfaces. **Contracts are frozen before implementation** (TDD writes tests against these). SQLAlchemy ORM rows in `storage/models.py` mirror these 1:1. **Raw capture** tables (`raw_telegram_message`, `raw_signal_event`) are append-only (insert-only; no UPDATE/DELETE). **Derived extraction-outcome** tables (`extracted_signal`, `unrecognized_signal`, `parser_drift_warning`) are **recomputable per-event projections**: a re-extract upserts the outcome keyed on `event_id` (one-of enforced by a single `record_outcome` write) — see [ADR 0006](../../adr/0006-extraction-outcomes-shape-and-lifecycle.md), which amends [ADR 0001](../../adr/0001-two-layer-raw-capture.md).

Notation: `?` = optional, `[]` = list, enums in `UPPER`.

## 1. Enums

```python
Side          = LONG | SHORT                         # buy→LONG, sell→SHORT
EntryType     = MARKET | LIMIT_SINGLE | LIMIT_RANGE   # MARKET = no price given
SignalEventType = NEW_ENTRY | MODIFY | CLOSE | UNRECOGNIZED
ExtractionMethod = DETERMINISTIC | LLM_FALLBACK
DeletionConfidence = CONFIRMED | SUSPECTED
DeletionMethod = SNAPSHOT_DIFF | ID_GAP | LIVE_EVENT
SimOutcomeKind = R_MULTIPLE | MARK_TO_MARKET | UNFILLED
DeliveryMode  = PUSH | POLL | CATCH_UP               # live message delivery path (latency provenance)
MatchReason   = DIRECTIONAL_KEYWORD | SYMBOL_TOKEN | PRICE_SHAPED   # seed candidate heuristic, recall-first
MaterializationPath = SEED_HEURISTIC | FILTER_RULE | PARSER_BACKFILL | HUMAN_AUDIT  # how a RawSignalEvent was flagged
MissDiscoveredBy = PARSER_BACKFILL | HUMAN_AUDIT | LLM_FALLBACK     # who found a filter false negative (FilterDriftWarning)
```

## 2. Sources & capture

```python
TelegramChannel:
    channel_id: int                 # Telegram id (PK)
    handle: str?                     # @name if public
    title: str
    is_private: bool
    subscriber_count: int?           # GetFullChannel.participants_count
    first_seen_at: datetime
    captured_through_message_id: int?  # backfill cursor

RawTelegramMessage:                  # immutable, append-only, 100% capture
    channel_id: int
    message_id: int                  # (channel_id, message_id) unique
    text: str?
    sender_id: int?
    posted_at: datetime
    captured_at: datetime
    reply_to_message_id: int?        # ties lifecycle events
    edit_date: datetime?
    has_media: bool
    views: int?                      # active-user proxy input
    forwards: int?
    raw_payload: json                # full Telethon dict, verbatim

RawSignalEvent:                      # ADVISORY signal candidate (priority/triage, not a hard gate); may be late-materialized — ADR 0005
    id: uuid
    channel_id: int
    message_id: int                  # → RawTelegramMessage; (channel_id, message_id) unique
    candidate_text: str              # exact slice fed to extraction (verbatim message text)
    materialized_by: MaterializationPath   # SEED_HEURISTIC | FILTER_RULE | PARSER_BACKFILL | HUMAN_AUDIT
    matched_reasons: list[MatchReason]     # seed heuristics that fired (audit); may be empty when materialized by a rule/path
    filter_rule_id: str?             # the FilterRule that flagged it, if any (null for seed/backfill/audit)
    created_at: datetime
```

## 3. Extraction

```python
TradeIntent:                         # the trade parsed FROM TEXT; provenance-free; required = symbol+side
    symbol: str                      # REQUIRED, normalized e.g. "BTCUSDT"
    side: Side                       # REQUIRED
    entry_type: EntryType?
    entry_low: Decimal?              # single → low==high
    entry_high: Decimal?
    stop_loss: Decimal?
    take_profits: list[Decimal]      # ordered, may be empty
    leverage: Decimal?
    confidence: Decimal?             # provider-stated, if any

ExtractedSignal(TradeIntent):        # a TradeIntent RECORDED against an event (adds linkage + provenance)
    id: uuid
    event_id: uuid                   # → RawSignalEvent
    channel_id: int
    event_type: SignalEventType      # NEW_ENTRY | MODIFY | CLOSE (lifecycle; defaults NEW_ENTRY at extraction)
    references_message_id: int?      # reserved; lifecycle linkage is computed in FoldStep.source_message_id, not on this row (ADR 0007)
    extraction_method: ExtractionMethod   # DETERMINISTIC | LLM_FALLBACK — also the parse-reliability signal (work item 8)
    rule_id: str?                    # which ParserRule matched (null for LLM_FALLBACK)
    extracted_at: datetime

UnrecognizedSignal:                  # extraction produced nothing usable
    id: uuid
    event_id: uuid
    reason: str                      # no_symbol | no_side | no_match | fallback_failed
    attempted_methods: list[ExtractionMethod]
    created_at: datetime
```

**Shape vs linkage ([ADR 0006](../../adr/0006-extraction-outcomes-shape-and-lifecycle.md)):** the extractors (`parse`, `extract`) produce only a `TradeIntent` from text; the `ExtractService` attaches event linkage + `extraction_method` (one `_link` site for both the deterministic and fallback paths). `parser_confidence` is **dropped** — `extraction_method` (DETERMINISTIC vs LLM_FALLBACK) is the honest, non-fabricated parse-reliability signal; work item 8 derives its scorecard component from the `extraction_method` distribution + the unrecognized rate.

**Invariant:** every `RawSignalEvent` yields **exactly one** of `{ExtractedSignal, UnrecognizedSignal}`. The candidate filter is advisory ([ADR 0005](../../adr/0005-distilled-filter-and-advisory-gate.md)): deterministic parsing may also run over non-candidate `RawTelegramMessage`s; a hit there **late-materializes** a `RawSignalEvent` (`materialized_by=PARSER_BACKFILL`) and emits a `FilterDriftWarning`. The 1:1 invariant binds each materialized event, not each raw message.

## 4. Parser rules & drift

```python
FilterRule:                          # declarative INCLUSION rule (recall-first); distilled from is_signal labels — ADR 0005
    rule_id: str                     # stable id (PK)
    channel_id: int?                 # null = global / seed
    version: int
    include_patterns: list[str]      # ordered regexes; ANY match → candidate (OR-joined, recall-first)
    exclude_patterns: list[str]      # optional carve-outs (rare; precision is recovered downstream)
    matched_reason_template: str     # audit label written to RawSignalEvent.matched_reasons / filter_rule_id
    recall_target: float             # recall the distillation aims to hold on labeled positives
    python_filter: str?              # dotted path; escape hatch (mirrors ParserRule.python_extractor)
    created_at: datetime
    distilled_from_label_ids: list[uuid]   # provenance → golden corpus

ParserRule:                          # declarative EXTRACTION rule + escape hatch
    rule_id: str                     # stable id (PK)
    channel_id: int?                 # null = global
    version: int
    patterns: list[str]              # ordered regexes
    field_map: dict[str,str]         # named group → ExtractedSignal field
    side_aliases: dict[str,Side]     # "buy"→LONG, "ОТКРЫЛ ЛОНГ"→LONG ...
    python_extractor: str?           # dotted path; escape hatch
    created_at: datetime
    distilled_from_label_ids: list[uuid]   # provenance → golden corpus

FilterDriftWarning:                  # candidate filter missed a message that proved to be a signal — ADR 0005
    id: uuid
    channel_id: int
    message_id: int                  # → RawTelegramMessage the filter did not flag
    filter_rule_version: int?        # the FilterRule version that missed it (null = seed heuristic)
    miss_discovered_by: MissDiscoveredBy   # PARSER_BACKFILL | HUMAN_AUDIT | LLM_FALLBACK
    event_id: uuid?                  # the late-materialized RawSignalEvent, if one was created
    source_label_id: uuid?           # the GoldenLabel that proved it a signal, if any
    created_at: datetime

ParserDriftWarning:                  # det miss + fallback success
    id: uuid
    event_id: uuid
    channel_id: int
    deterministic_result: str        # "no_match"
    fallback_result: str             # "extracted"
    fallback_signal_id: uuid         # the ExtractedSignal the CLI produced
    created_at: datetime

GoldenLabel:                         # operator ground truth from distillation
    id: uuid
    channel_id: int
    message_id: int
    is_signal: bool
    expected: ExtractedSignal?       # expected fields when is_signal
    labeled_at: datetime
```

## 5. Lifecycle (folded view)

```python
FoldedSignal:                        # derived; recomputable from durable inputs, NEVER stored (ADR 0007)
    root_signal_id: uuid             # the NEW_ENTRY ExtractedSignal id == SimOutcome.folded_signal_id
    symbol: str
    side: Side
    timeline: list[FoldStep]         # entry + each applied modification, time-ordered by posted_at
    closed_at: datetime?             # set when a CLOSE applied or effective_size reached 0
    fold_version: int                # lifecycle-logic version (reproducibility of a past fold)

FoldStep:                            # the effective position state AFTER this step
    at: datetime                     # the source message's posted_at (the true timeline)
    source_signal_id: uuid           # = root_signal_id (the durable entry signal)
    source_message_id: int           # the message that caused this step (entry or reply)
    event_type: SignalEventType      # NEW_ENTRY | MODIFY | CLOSE
    effective_stop_loss: Decimal?
    effective_take_profits: list[Decimal]
    effective_size: Decimal          # cumulative position size (stated multipliers; entry = 1)
    effective_entry: Decimal?        # size-weighted avg of PRICED legs; None ⇒ a market leg is unresolved
    leg_size: Decimal?               # this step's size delta (+average-in / −reduce); None for SL/TP-only modifies
    leg_price: Decimal?              # this step's leg price; None ⇒ market-at-`at` (work item 9 fills from klines)
```

**Rules ([ADR 0007](../../adr/0007-lifecycle-fold-pure-recomputable.md)):**
- A `FoldedSignal` is multi-step **only** when ≥1 `MODIFY`/`CLOSE` is in its `reply_to` chain. A standalone complete `NEW_ENTRY` folds to a single-step timeline (no phantom lifecycle).
- Modifications are **not** `ExtractedSignal`s — they are recognized at fold-time from the `reply_to` chain (transitive, symbol-guarded), so `event_type`/`references_message_id` live in the **folded view**, never written back to `extracted_signal`.
- Effective state carries forward cumulatively; `move SL to BE` ⇒ `effective_stop_loss := effective_entry` (unresolved if a market leg is unresolved); a reduce lowers `effective_size` without moving `effective_entry`; a full close (or `effective_size → 0`) sets `closed_at`.
- Market-price legs (`leg_price = None`) and the resulting `effective_entry = None` are resolved by work item 9 sim against klines — the existing `EntryType.MARKET` fill pattern.

## 6. Deletion

```python
DeletedSignalEvidence:
    id: uuid
    channel_id: int
    message_id: int
    confidence: DeletionConfidence   # CONFIRMED | SUSPECTED
    method: DeletionMethod           # SNAPSHOT_DIFF | ID_GAP | LIVE_EVENT
    original_text: str?              # retained iff CONFIRMED/LIVE_EVENT
    first_seen_at: datetime?
    detected_at: datetime
    was_signal_candidate: bool       # was a RawSignalEvent?
```

**Detection ([ADR 0008](../../adr/0008-deletion-evidence-durable-projection.md)):** a deletion is found by **re-fetching the channel's current live message-id set** (`TelegramSource.live_message_ids`, §9) and diffing it against the durable **stored** set. Raw capture is insert-only, so a deleted message never leaves our DB — two *stored* backfills can never reveal it. Over `range = [min..max]` of `stored ∪ live`:
- `CONFIRMED` / `SNAPSHOT_DIFF` = `stored − live` — we captured it, it is gone now; `original_text` + `first_seen_at` (the stored `captured_at`) are **retained**.
- `SUSPECTED` / `ID_GAP` = `range − stored − live` — a slot present in **neither** snapshot (never captured, now gone); no content. A still-present message (content or service action) sits in `live` and is therefore **never** flagged.
- contiguous / all-still-live ⇒ no evidence. `LIVE_EVENT` deletions arrive in work item 10.

**Storage (durable, NOT recomputable — a third table class):** unlike the recomputable extraction projection ([ADR 0006](../../adr/0006-extraction-outcomes-shape-and-lifecycle.md)) and the in-memory fold ([ADR 0007](../../adr/0007-lifecycle-fold-pure-recomputable.md)), `DeletedSignalEvidence` is **persisted** because the live snapshot it is computed against is ephemeral (it cannot be reconstructed from durable inputs). One row per `(channel_id, message_id)`: a rescan is idempotent (`+0`); a `SUSPECTED` may upgrade to `CONFIRMED` but a `CONFIRMED` never downgrades; the first-noticed `detected_at` is preserved. **All** confirmed deletions are stored (audit), but only `was_signal_candidate` ones feed the work item-8 deletion-behaviour score — chatter deletions affect nothing; `SUSPECTED` is surfaced per channel.

## 7. Scoring

```python
ScoreComponent:
    name: str                        # "sim_expectancy" | "drawdown" | ...
    raw_value: float                 # measured input
    normalized: float                # 0..1
    weight: float                    # from config
    contribution: float              # normalized * weight
    evidence_refs: list[str]         # ids of rows that produced raw_value

ProviderScore:
    channel_id: int
    score: float                     # sum(contribution), 0..1
    components: list[ScoreComponent]
    signal_count: int
    simulated_count: int             # signals with enough fields to simulate
    computed_at: datetime
    weights_version: str             # config placeholder id

ProviderScoreExplanation:
    channel_id: int
    score: float
    breakdown: list[ScoreComponent]  # full trace
    notes: list[str]                 # caveats e.g. "0 simulable signals"
```

**Scoring ([ADR 0009](../../adr/0009-provider-score-recomputable-scorecard.md)):** `ProviderScore` + `ProviderScoreExplanation` are produced by a pure `services/scoring/` (`hygiene.py` metric math → `scorecard.py` weighted assembly) over durable inputs and are **recomputed on read, never persisted** — the second in-memory recompute after the fold ([ADR 0007](../../adr/0007-lifecycle-fold-pure-recomputable.md)), not a stored projection ([ADR 0006](../../adr/0006-extraction-outcomes-shape-and-lifecycle.md)) or durable evidence ([ADR 0008](../../adr/0008-deletion-evidence-durable-projection.md)). No migration. `computed_at` defaults `_now()` but is injected for deterministic tests (mirrors `detect_deletions(detected_at)`).

- **Composite:** `score = Σ(normalized × weight)` — a plain weighted sum (no renormalization), over only the components currently backed by evidence. Weights live in `domain/score.py` as `DEFAULT_WEIGHTS = ScoreWeights(version="v0", by_component={…})`, injected into the builder so re-weighting is deterministic and touches only `scorecard.py`.
- **Components (v0 weights, placeholder — not optimal):** *scored quality* — `sim_expectancy` 0.30 + `drawdown` 0.20, `deletion_behaviour` 0.20, `completeness` 0.10, `parser_confidence` 0.10, `evidence_availability` 0.10 (Σ = 1.0); *context* — `signal_frequency`, `active_user_proxy` at **weight 0** (informational, still evidence-traced). Without simulated outcomes, the score stays **honestly partial** (`simulated_count = 0`; `notes` records that simulation evidence is absent).
- **No fabrication:** an absent-simulation or empty-denominator (0/0) component is **excluded from `components` + noted**, never scored at 0 or 0.5. `evidence_availability` is emitted only when a rescan provably ran (≥1 deletion-evidence row with `method ∈ {SNAPSHOT_DIFF, ID_GAP}`; `LIVE_EVENT` excluded), else excluded + noted — a never-rescanned channel never reads 1.0.
- **Per-component math:** `sim_expectancy.raw` = mean R-multiple, normalized = clamp((mean_r + 1) ÷ 3, 0, 1); `drawdown.raw` = max MAE, normalized = clamp(1 − max_mae, 0, 1); `deletion_behaviour` = 1 − (CONFIRMED∧signal deletions ÷ `RawSignalEvent` count); `completeness` = mean over signals of present-among-{entry, stop, ≥1 TP} ÷ 3; `parser_confidence` = DETERMINISTIC ÷ total candidates; `evidence_availability` = `count_messages` ÷ (`count_messages` + `ID_GAP` gaps); `signal_frequency` = candidates ÷ observation-window-days; `active_user_proxy` raw = `subscriber_count`, normalized = mean of saturated {subs, median views, median forwards} over available inputs.
- **evidence_refs grammar (100% traceable):** typed-prefix strings — `channel:<id>` · `message:<channel>/<msg>` · `event:<uuid>` · `signal:<uuid>` · `unrecognized:<uuid>` · `deletion:<uuid>` · `parser_drift:<uuid>` · `filter_drift:<uuid>`. Refs name every row used to **measure** the value (numerator + denominator), so a measured `0.0` still traces; bulk message-corpus denominators anchor on `channel:<id>` (a deterministic `count_messages` query) instead of enumerating thousands of rows.
- **Surface:** offline `verasig score <ref>` reads via repos, calls the pure builder, prints `format_score` + `format_explanation` (notes incl.); unknown channel exits 1 — mirrors `stats`/`lifecycle`/`deletions`.

## 8. Simulation

```python
SimOutcome:
    folded_signal_id: uuid           # == FoldedSignal.root_signal_id (NEW_ENTRY id); fold is in-memory (ADR 0007)
    kind: SimOutcomeKind             # R_MULTIPLE | MARK_TO_MARKET | UNFILLED
    r_multiple: float?               # when stop present
    pct_return: float?               # when MTM
    mfe: float                       # max favorable excursion
    mae: float                       # max adverse excursion → drawdown
    entry_fill_at: datetime?
    exit_at: datetime?
    exit_reason: str                 # stop | tp | expiry | unfilled
    policy: str                      # "ProviderStatedPolicy"
    tie_break: str                   # "stop_first"

Kline:
    symbol: str
    open_time: datetime
    open: Decimal; high: Decimal; low: Decimal; close: Decimal
    volume: Decimal
```

## 9. Service interfaces (the seams TDD tests inject fakes at)

```python
# domain/protocols.py
class MarketData(Protocol):
    def klines(self, symbol: str, start: datetime, end: datetime,
               interval: str = "1") -> list[Kline]: ...   # "1" = 1m

class LlmExtractor(Protocol):
    def extract(self, candidate_text: str) -> TradeIntent | None: ...   # text in, trade-shape out; service links
# adapter: ClaudeCliExtractor(command="claude"|"codex", runner=...) (subprocess, runner-injectable); FakeExtractor (tests)
# the deterministic parser is SYMMETRIC: parse(rule, candidate_text) -> TradeIntent | None
# both feed ExtractService._link, which stamps event_id/channel_id/extraction_method/rule_id

class RuleDistiller(Protocol):
    def distill_filter(self, labels: list[GoldenLabel]) -> FilterRule: ...        # recall-first, from is_signal
    def distill_parsers(self, labels: list[GoldenLabel]) -> list[ParserRule]: ...  # precision-first, from expected fields
# adapter: ClaudeCliDistiller (distinct recall-first vs precision-first prompts); FakeDistiller (tests)

class ExecutionPolicy(Protocol):
    def simulate(self, folded: FoldedSignal, klines: list[Kline]) -> SimOutcome: ...
# v0: ProviderStatedPolicy; future: CustomRiskPolicy

# domain/telegram.py
class TelegramDeliveryEvent(BaseModel):  # live message + its latency provenance
    message: RawTelegramMessage
    mode: DeliveryMode               # PUSH | POLL | CATCH_UP
    captured_at: datetime
    source_pts: int?                 # channel pts at delivery, when known
    gap_closed: bool                 # this delivery resolved a detected pts gap

class TelegramDeletionEvent(BaseModel):  # live deletion notice for one message id
    channel_id: int
    message_id: int
    detected_at: datetime
    source_pts: int?                 # channel pts at deletion, when known

TelegramLiveEvent = TelegramDeliveryEvent | TelegramDeletionEvent

# domain/protocols.py
class TelegramSource(Protocol):
    # resolve: @handle | t.me link | numeric id → channel identity + metadata (work item 2)
    async def resolve_channel(self, reference: str | int) -> TelegramChannel: ...
    # backfill: chunked + resumable — yields one committable batch at a time, never full history
    def backfill_batches(self, channel_id: int, after_message_id: int?,
                         batch_size: int) -> AsyncIterator[list[RawTelegramMessage]]: ...
    # deletion rescan: the channel's CURRENT live message-id set, for snapshot-diff (work item 7, ADR 0008)
    async def live_message_ids(self, channel_id: int) -> set[int]: ...
    # live: ONE global socket, many channels; hybrid push + short-poll behind this method
    def live_events(self, channel_ids: list[int]) -> AsyncIterator[TelegramLiveEvent]: ...
# adapter: foundation/telegram_source.py TelethonSource (resolve + push handler + bounded short-poll + dedupe); FakeSource (tests, fixture corpora)
```

**Every external dependency (Telegram, LLM CLI, market data, Postgres) sits behind one of these Protocols** so unit tests run pure and offline; integration tests use ephemeral Postgres + recorded fixtures. No test ever calls the real CLI or real Telegram.
