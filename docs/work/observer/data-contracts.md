# Observer Data Contracts

Canonical Pydantic contracts (`domain/`) + service interfaces. SQLAlchemy ORM rows in `storage/models.py` implement the durable shapes; enum-backed CHECK constraints are generated from the domain `StrEnum`s (`enum_check()`), so they cannot drift from Python. **Raw capture** (`raw_message`) is append-only within one capture generation — see [ADR 0001](../../adr/0001-two-layer-raw-capture.md). **`signal`** is a recomputable projection over it, one row per message that the miner turned into a trade. Mining Confirm addresses an immutable `MiningReview`; after revision validation it replaces the feed's whole signal projection, records confirmed miss evidence, and marks the feed verified in one transaction. A "miss" is the **absence** of a `signal` row for a reviewed candidate message. See [ADR 0017](../../adr/0017-signal-schema-collapse-and-absence-based-misses.md) and [ADR 0018](../../adr/0018-revisioned-mining-review.md).

Notation: `?` = optional, `[]` = list, enums in `UPPER`.

## 1. Enums

```python
Side          = LONG | SHORT                         # buy→LONG, sell→SHORT
EntryType     = MARKET | LIMIT_SINGLE | LIMIT_RANGE   # MARKET = no price given
SignalEventType = NEW_ENTRY | MODIFY | CLOSE
DeletionConfidence = CONFIRMED | SUSPECTED
DeletionMethod = SNAPSHOT_DIFF | ID_GAP | LIVE_EVENT
SimOutcomeKind = R_MULTIPLE | MARK_TO_MARKET | UNFILLED
DeliveryMode  = PUSH | POLL | CATCH_UP               # live message delivery path (latency provenance)
FeedStatus    = NEW | BACKFILLING | BACKFILLED | VERIFIED | ANALYZED | CANCELLED | FAILED
HistoryDepth  = 6m | 1y | ALL                        # how far back a fresh capture reaches
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
```

The persisted `feed` row also owns `capture_generation`, an integer advanced
before each full-history recapture. It is storage revision state, not Telegram
channel metadata, and contributes to every mining `inputRevision`.

There is no separate "candidate event" row: the miner mines and extracts a
message in one pass, so a message either has a `Signal` (§3) or it doesn't —
there is nothing to materialize independently of the extraction itself.

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

Signal(TradeIntent):                 # a TradeIntent RECORDED against the message it came from
    id: uuid
    channel_id: int                  # external_id
    message_id: int                  # external_message_id; (channel_id, message_id) unique per user
    candidate_text: str              # exact slice fed to extraction (verbatim message text)
    event_type: SignalEventType      # NEW_ENTRY | MODIFY | CLOSE (lifecycle; defaults NEW_ENTRY at extraction)
    rule_id: str?                    # the miner's template key that matched, if any
    extracted_at: datetime
```

**One table, keyed by message ([ADR 0017](../../adr/0017-signal-schema-collapse-and-absence-based-misses.md)):** the miner is the only extractor and Mining Confirm mines + extracts a message in one pass, so there is no separate candidate-event row to link against — `Signal` carries its own message identity directly. A row only ever exists for a **successful** extraction; misses have no persisted outcome row.

**Misses are absence in the signal projection.** A candidate message is a miss
when it has no `Signal`; no outcome row is written or cleaned up. For confirmed
parser confidence, the candidate denominator and missed message ids come from the
addressed confirmed `MiningReview`, not an anti-join over the entire raw corpus.

**Confirm is replace-the-projection, not upsert.** `POST /feeds/{external_id}/mining/confirm` loads the addressed `MiningReview`; it does not re-mine live messages. After validating that review's revision, Confirm deletes every `signal` row for `(user_id, external_id)` and inserts exactly the accepted reviewed candidates' signals. A smaller accepted set therefore removes de-selected families instead of leaving orphaned signals.

## 4. Mining review and confirmation

```python
MiningReview:                        # immutable reviewed input + mined output (ADR 0018)
    review_id: uuid                  # JSON: reviewId; required by Audit and Confirm
    user_id: uuid
    external_id: int
    input_revision: str              # JSON: inputRevision; SHA-256 digest
    messages: list[ChatMessage]      # exact ordered id/text/date corpus shown
    groups: list[TemplateGroup]      # exact mined families shown
    overlay: dict                    # exact parser overlay used
    created_at: datetime

MiningReviewConfirmation:            # evidence recorded against the addressed review
    accepted_template_keys: list[str]
    missed_message_ids: list[int]    # confirmed candidate misses for scoring
    confirmed_at: datetime
```

`inputRevision` digests the ordered message identity, text, and date; the parser
overlay; and the feed's `capture_generation`. A full-history re-fetch advances
that generation even if the recaptured bytes are identical. Audit and Confirm
recompute the live revision and return `409 MINING_REVIEW_STALE` without mutation
when the corpus, overlay, or generation changed.

Confirm holds the feed-row lock while it validates the addressed review,
replaces the `signal` projection, records accepted template keys and confirmed
miss ids, and sets `FeedStatus.VERIFIED`. These writes commit atomically. Backfill
creation uses the same lock, so capture cannot start through a partial Confirm.

Confirmed misses are the addressed review's ambiguous candidates, rare-template
candidates, and potential misses after excluding every message that produced a
persisted signal. Parser confidence reads these stored ids from the latest current
confirmed review; it does not reclassify a later corpus.

## 5. Lifecycle (folded view)

```python
FoldedSignal:                        # derived; recomputable from durable inputs, NEVER stored (ADR 0007)
    root_signal_id: uuid             # the NEW_ENTRY Signal id == SimOutcome.folded_signal_id
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
- Modifications are **not** their own `Signal`s — they are recognized at fold-time from the `reply_to` chain (transitive, symbol-guarded), so lifecycle linkage lives in the **folded view** (`FoldStep.source_message_id`), never written back to `signal`.
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
    was_signal_candidate: bool       # was there a Signal for this message?
```

**Detection ([ADR 0008](../../adr/0008-deletion-evidence-durable-projection.md)):** a deletion is found by **re-fetching the channel's current live message-id set** (`TelegramSource.live_message_ids`, §8) and diffing it against the durable **stored** set. Raw capture is insert-only, so a deleted message never leaves our DB — two *stored* backfills can never reveal it. Over `range = [min..max]` of `stored ∪ live`:
- `CONFIRMED` / `SNAPSHOT_DIFF` = `stored − live` — we captured it, it is gone now; `original_text` + `first_seen_at` (the stored `captured_at`) are **retained**.
- `SUSPECTED` / `ID_GAP` = `range − stored − live` — a slot present in **neither** snapshot (never captured, now gone); no content. A still-present message (content or service action) sits in `live` and is therefore **never** flagged.
- contiguous / all-still-live ⇒ no evidence. `LIVE_EVENT` deletions arrive in work item 10.

**Storage (durable, NOT recomputable — a third table class):** unlike the recomputable `signal` projection ([ADR 0017](../../adr/0017-signal-schema-collapse-and-absence-based-misses.md)) and the in-memory fold ([ADR 0007](../../adr/0007-lifecycle-fold-pure-recomputable.md)), `DeletedSignalEvidence` is **persisted** because the live snapshot it is computed against is ephemeral (it cannot be reconstructed from durable inputs). One row per `(channel_id, message_id)`: a rescan is idempotent (`+0`); a `SUSPECTED` may upgrade to `CONFIRMED` but a `CONFIRMED` never downgrades; the first-noticed `detected_at` is preserved. **All** confirmed deletions are stored (audit), but only `was_signal_candidate` ones feed the work item-8 deletion-behaviour score — chatter deletions affect nothing; `SUSPECTED` is surfaced per channel.

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

**Scoring ([ADR 0009](../../adr/0009-provider-score-recomputable-scorecard.md)):** `ProviderScore` + `ProviderScoreExplanation` are produced by a pure `features/provider_scores/` (`hygiene.py` metric math → `scorecard.py` weighted assembly) over durable inputs and are **recomputed on read, never persisted** — the second in-memory recompute after the fold ([ADR 0007](../../adr/0007-lifecycle-fold-pure-recomputable.md)), not a stored projection ([ADR 0017](../../adr/0017-signal-schema-collapse-and-absence-based-misses.md)) or durable evidence ([ADR 0008](../../adr/0008-deletion-evidence-durable-projection.md)). No migration. `computed_at` defaults `_now()` but is injected for deterministic tests (mirrors `detect_deletions(detected_at)`).

- **Composite:** `score = Σ(normalized × weight)` — a plain weighted sum (no renormalization), over only the components currently backed by evidence. Weights live in `domain/score.py` as `DEFAULT_WEIGHTS = ScoreWeights(version="v0", by_component={…})`, injected into the builder so re-weighting is deterministic and touches only `scorecard.py`.
- **Components (v0 weights, placeholder — not optimal):** *scored quality* — `sim_expectancy` 0.30 + `drawdown` 0.20, `deletion_behaviour` 0.20, `completeness` 0.10, `parser_confidence` 0.10, `evidence_availability` 0.10 (Σ = 1.0); *context* — `signal_frequency`, `active_user_proxy` at **weight 0** (informational, still evidence-traced). Without simulated outcomes, the score stays **honestly partial** (`simulated_count = 0`; `notes` records that simulation evidence is absent).
- **No fabrication:** an absent-simulation or empty-denominator (0/0) component is **excluded from `components` + noted**, never scored at 0 or 0.5. `evidence_availability` is emitted only when a rescan provably ran (≥1 deletion-evidence row with `method ∈ {SNAPSHOT_DIFF, ID_GAP}`; `LIVE_EVENT` excluded), else excluded + noted — a never-rescanned channel never reads 1.0.
- **Per-component math:** `sim_expectancy.raw` = mean R-multiple, normalized = clamp((mean_r + 1) ÷ 3, 0, 1); `drawdown.raw` = max MAE, normalized = clamp(1 − max_mae, 0, 1); `deletion_behaviour` = 1 − (CONFIRMED∧signal deletions ÷ signal count); `completeness` = mean over signals of present-among-{entry, stop, ≥1 TP} ÷ 3; `parser_confidence` = recognition rate — extracted signals ÷ (extracted signals + misses), where a miss is a candidate message with no `signal` row (the anti-join, §3); `evidence_availability` = `count_messages` ÷ (`count_messages` + `ID_GAP` gaps); `signal_frequency` = signals ÷ observation-window-days; `active_user_proxy` raw = `subscriber_count`, normalized = mean of saturated {subs, median views, median forwards} over available inputs.
- **evidence_refs grammar (100% traceable):** typed-prefix strings — `channel:<id>` · `message:<channel>/<msg>` · `signal:<uuid>` (a persisted `Signal`) · `event:<uuid>` (a `Signal`'s own id, or a missed candidate's message id, used as the recomputable-candidate reference) · `deletion:<uuid>`. Refs name every row used to **measure** the value (numerator + denominator), so a measured `0.0` still traces; bulk message-corpus denominators anchor on `channel:<id>` (a deterministic `count_messages` query) instead of enumerating thousands of rows.
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
# domain/market_ports.py
class MarketData(Protocol):
    def klines(self, symbol: str, start: datetime, end: datetime,
               interval: str = "1") -> list[Kline]: ...   # "1" = 1m

# domain/execution_ports.py
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

# domain/telegram_ports.py
class TelegramSource(Protocol):
    # resolve: @handle | bare handle | t.me link | numeric id | title:<exact joined dialog title>
    #          | non-username title → channel identity + metadata (work item 2)
    async def resolve_channel(self, reference: str | int) -> TelegramChannel: ...
    # backfill: chunked + resumable — yields one committable batch at a time, never full history
    def backfill_batches(self, channel_id: int, after_message_id: int?,
                         batch_size: int) -> AsyncIterator[list[RawTelegramMessage]]: ...
    # deletion rescan: the channel's CURRENT live message-id set, for snapshot-diff (ADR 0008)
    async def live_message_ids(self, channel_id: int) -> set[int]: ...
    # live: ONE global socket, many channels; hybrid push + short-poll behind this method
    def live_events(self, channel_ids: list[int]) -> AsyncIterator[TelegramLiveEvent]: ...
# adapter: foundation/telegram/telethon_source.py TelethonSource (resolve + push handler + bounded short-poll + dedupe); FakeSource (tests, fixture corpora)
```

**Every external dependency (Telegram, market data, Postgres) sits behind one of these Protocols** so unit tests run pure and offline; integration tests use ephemeral Postgres + recorded fixtures. No test ever calls real Telegram.
