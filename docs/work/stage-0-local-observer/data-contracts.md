# Stage 0 — Data Contracts

Canonical Pydantic contracts (`domain/`) + service interfaces. **Contracts are frozen before implementation** (TDD writes tests against these). SQLAlchemy ORM rows in `storage/models.py` mirror these 1:1 and are append-only (insert-only; no UPDATE/DELETE on raw tables).

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
ExtractedSignal:                     # canonical, flexible; required = symbol+side
    id: uuid
    event_id: uuid                   # → RawSignalEvent
    channel_id: int
    symbol: str                      # REQUIRED, normalized e.g. "BTCUSDT"
    side: Side                       # REQUIRED
    event_type: SignalEventType      # NEW_ENTRY | MODIFY | CLOSE
    references_message_id: int?      # for MODIFY/CLOSE (from reply_to or text)
    entry_type: EntryType?
    entry_low: Decimal?              # single → low==high
    entry_high: Decimal?
    stop_loss: Decimal?
    take_profits: list[Decimal]      # ordered, may be empty
    leverage: Decimal?
    confidence: Decimal?             # provider-stated, if any
    parser_confidence: float         # 0..1, extractor's confidence
    extraction_method: ExtractionMethod
    rule_id: str?                    # which ParserRule matched
    extracted_at: datetime

UnrecognizedSignal:                  # extraction produced nothing usable
    id: uuid
    event_id: uuid
    reason: str                      # no_symbol | no_side | no_match | fallback_failed
    attempted_methods: list[ExtractionMethod]
    created_at: datetime
```

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
FoldedSignal:                        # derived; not stored raw, computed in sim slice
    root_signal_id: uuid             # the NEW_ENTRY
    symbol: str
    side: Side
    timeline: list[FoldStep]         # entry + each modification, time-ordered
    closed_at: datetime?             # if a CLOSE was applied

FoldStep:
    at: datetime
    source_signal_id: uuid
    effective_stop_loss: Decimal?
    effective_take_profits: list[Decimal]
```

**Rule:** a `FoldedSignal` is multi-step **only** when ≥1 `MODIFY`/`CLOSE` references it. A standalone complete `NEW_ENTRY` folds to a single-step timeline.

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

## 8. Simulation

```python
SimOutcome:
    folded_signal_id: uuid
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
# foundation/market_data.py
class MarketData(Protocol):
    def klines(self, symbol: str, start: datetime, end: datetime,
               interval: str = "1") -> list[Kline]: ...   # "1" = 1m

# services/extraction/llm_fallback.py
class LlmExtractor(Protocol):
    def extract(self, candidate_text: str) -> ExtractedSignal | None: ...
# adapters: ClaudeCliExtractor, CodexCliExtractor (subprocess); FakeExtractor (tests)

# services/distillation/rule_distiller.py  (one labeling pass → both rule kinds; ADR 0005)
class RuleDistiller(Protocol):
    def distill_filter(self, labels: list[GoldenLabel]) -> FilterRule: ...        # recall-first, from is_signal
    def distill_parsers(self, labels: list[GoldenLabel]) -> list[ParserRule]: ...  # precision-first, from expected fields
# adapter: ClaudeCliDistiller (distinct recall-first vs precision-first prompts); FakeDistiller (tests)

# services/scoring/policies.py
class ExecutionPolicy(Protocol):
    def simulate(self, folded: FoldedSignal, klines: list[Kline]) -> SimOutcome: ...
# v0: ProviderStatedPolicy; future: CustomRiskPolicy

# foundation/telegram_source.py   (async seam — supersedes the old sync backfill()/stream(); see ADR 0004)
class TelegramDeliveryEvent(BaseModel):  # live message + its latency provenance
    message: RawTelegramMessage
    mode: DeliveryMode               # PUSH | POLL | CATCH_UP
    captured_at: datetime
    source_pts: int?                 # channel pts at delivery, when known
    gap_closed: bool                 # this delivery resolved a detected pts gap

class TelegramSource(Protocol):
    # resolve: @handle | t.me link | numeric id → channel identity + metadata (Slice 2)
    async def resolve_channel(self, reference: str | int) -> TelegramChannel: ...
    # backfill: chunked + resumable — yields one committable batch at a time, never full history
    def backfill_batches(self, channel_id: int, after_message_id: int?,
                         batch_size: int) -> AsyncIterator[list[RawTelegramMessage]]: ...
    # live: ONE global socket, many channels; hybrid push + short-poll behind this method
    def live_events(self, channel_ids: list[int]) -> AsyncIterator[TelegramDeliveryEvent]: ...
# adapter: TelethonSource (resolve + push handler + bounded short-poll + dedupe); FakeSource (tests, fixture corpora)
```

**Every external dependency (Telegram, LLM CLI, market data, Postgres) sits behind one of these Protocols** so unit tests run pure and offline; integration tests use ephemeral Postgres + recorded fixtures. No test ever calls the real CLI or real Telegram.
