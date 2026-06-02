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

RawSignalEvent:                      # subset flagged as signal candidate
    id: uuid
    channel_id: int
    message_id: int                  # → RawTelegramMessage
    candidate_text: str              # exact slice fed to extraction
    matched_reason: str              # which heuristic fired (audit)
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

**Invariant:** every `RawSignalEvent` yields **exactly one** of `{ExtractedSignal, UnrecognizedSignal}`.

## 4. Parser rules & drift

```python
ParserRule:                          # declarative + escape hatch
    rule_id: str                     # stable id (PK)
    channel_id: int?                 # null = global
    version: int
    patterns: list[str]              # ordered regexes
    field_map: dict[str,str]         # named group → ExtractedSignal field
    side_aliases: dict[str,Side]     # "buy"→LONG, "ОТКРЫЛ ЛОНГ"→LONG ...
    python_extractor: str?           # dotted path; escape hatch
    created_at: datetime
    distilled_from_label_ids: list[uuid]   # provenance → golden corpus

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

# services/distillation/rule_distiller.py
class RuleDistiller(Protocol):
    def distill(self, labels: list[GoldenLabel]) -> list[ParserRule]: ...
# adapter: ClaudeCliDistiller; FakeDistiller (tests)

# services/scoring/policies.py
class ExecutionPolicy(Protocol):
    def simulate(self, folded: FoldedSignal, klines: list[Kline]) -> SimOutcome: ...
# v0: ProviderStatedPolicy; future: CustomRiskPolicy

# foundation/telegram_session.py
class TelegramSource(Protocol):
    def backfill(self, channel_id: int) -> Iterator[RawTelegramMessage]: ...
    def stream(self, channel_id: int) -> AsyncIterator[Event]: ...   # live slice
# adapter: TelethonSource; FakeSource (tests, fixture corpora)
```

**Every external dependency (Telegram, LLM CLI, market data, Postgres) sits behind one of these Protocols** so unit tests run pure and offline; integration tests use ephemeral Postgres + recorded fixtures. No test ever calls the real CLI or real Telegram.
