# Recommended architecture

Your hypothesis is correct, with two refinements:

1. **Episode linking is a separate decision from event extraction.**
2. **Related messages with no state effect should create relationship records, not artificial events.**

```text
Teleg:contentReference[oaicite:0]{index=0}tes + 0..n RelationCandidates
    ↓
Episode target resolution
    ↓
Candidate state replay and validation
    ↓
Human adjudication
    ↓
Accepted event log
    ↓
Deterministic canonical replay
    ↓
Verified fixture
    ↓
Rule distillation, certification, and regression testing
```

The final state must always be a **derived projection**. Reviewers should correct events, links, evidence, or ordering—not directly edit the projected state.

---

## 1. Critique of the label-verify approach

| Limitation                                    | Consequence                                                                                | Better abstraction                                                 |
| --------------------------------------------- | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------ |
| A message is treated as the atomic unit       | One message can contain several events, several signals, or no state-changing event        | Extract `0..n` events and `0..n` relationships per message         |
| A label combines multiple questions           | “Modifier” conflates classification, value extraction, target resolution, and state effect | Review these decisions separately                                  |
| Direct replies are over-trusted               | A reply can be a question, celebration, explanation, or unrelated comment                  | Treat reply metadata as relationship evidence only                 |
| Non-reply modifiers have no natural target    | Reviewers must infer context outside the label                                             | Run an explicit episode-resolution workflow                        |
| Labels do not encode transition semantics     | Correctly labeled messages can still produce an incorrect final state                      | Apply events through a deterministic state reducer                 |
| Labels become combinatorial                   | `partial-close + new-SL + TP-hit` requires multiple overlapping labels                     | Represent separate typed events                                    |
| Provenance is weak                            | A reviewer cannot tell exactly where a value came from                                     | Attach every extracted field to evidence spans                     |
| Regression tests operate at message level     | They miss sequence, linking, and state-replay errors                                       | Test whole episode streams and intermediate states                 |
| Reviewers repeatedly inspect obvious messages | Review effort is spread uniformly rather than by risk                                      | Prioritize uncertain links, high-impact events, and novel patterns |
| Final-state corrections are opaque            | A manually corrected state may not correspond to source evidence                           | Corrections must create auditable event/adjudication records       |

### The correct review unit

The primary review unit should be a **signal episode**, containing:

* Source messages and their versions
* Accepted and candidate relationships
* Candidate state-changing events
* Related messages with no state effect
* Event-by-event state changes
* Current projected state
* Validation failures and unresolved ambiguities

---

## 2. Better domain model

| Entity              | Purpose                                                                                           |
| ------------------- | ------------------------------------------------------------------------------------------------- |
| `MessageKey`        | Stable identity such as `telegram:<chat_id>:<message_id>`                                         |
| `MessageVersion`    | Immutable version of a message, including edits, deletion state, raw payload hash, and timestamps |
| `EvidenceItem`      | Exact source span, message metadata, relationship evidence, or explicit human assertion           |
| `MessageRelation`   | Reply, quote, forward, inferred episode reference, or manually confirmed relationship             |
| `SignalEvent`       | A semantic action or observation extracted from a message                                         |
| `TargetResolution`  | Candidate and accepted episode targets for an event                                               |
| `SignalEpisode`     | The lifecycle container for one trading idea                                                      |
| `StateProjection`   | Deterministically derived state after replaying accepted events                                   |
| `Adjudication`      | Immutable reviewer decision: accept, reject, correct, link, split, merge, or supersede            |
| `RuleSetVersion`    | Immutable collection of normalization, extraction, linking, and negative rules                    |
| `RegressionFixture` | Inputs plus expected events, relationships, evidence, intermediate states, and final state        |

### Required cardinalities

* One `MessageVersion` can produce **zero, one, or many events**.
* One `MessageVersion` can have **many relationships**.
* An event can initially target **zero, one, or several candidate episodes**.
* An accepted event may target one episode or explicitly multiple episodes.
* An episode can begin from **several opening messages**, not necessarily one complete signal message.
* A related message can belong to an episode while producing **no event**.
* A final state is generated only from the ordered accepted-event stream.

### Separate state domains

| State domain          | Examples                                                  |
| --------------------- | --------------------------------------------------------- |
| **Identity**          | Instrument, venue, market type, long/short                |
| **Instruction state** | Entries, take-profits, stop loss, risk directives         |
| **Execution state**   | Entries filled, TP hit, SL hit, position partially closed |
| **Lifecycle state**   | Provisional, active, cancelled, closed, reopened          |

This distinction prevents `"TP1 hit"` from accidentally rewriting the take-profit plan. It updates execution state; it does not necessarily remove or replace the instruction.

### Important value semantics

Use explicit values rather than overloading `null`:

* `UNSET`: no instruction has yet been supplied
* `NONE`: explicitly no stop loss or no targets
* `UNKNOWN`: the source implies a value exists, but it cannot be determined
* `KNOWN`: values are available

Arrays must use stable IDs such as `entry-2` or `tp-3`. Do not use array position as identity because later updates can reorder, remove, or replace levels.

The provenance structure can be aligned with W3C PROV: messages and states are entities; extraction, replay, and adjudication are activities; reviewers, rules, and models are responsible agents. ([W3C][1])3. Recommended end-to-end workflow

| Stage                         | Programmatic operation                                                                                                       | Output                                           |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| 1. Capture                    | Persist raw message payloads, edits, deletes, authorship, entities, replies, threads, and timestamps                         | Immutable `MessageVersion` records               |
| 2. Normalize                  | Normalize whitespace, Unicode, numeric formats, aliases, and line structure while maintaining a raw-to-normalized offset map | Searchable normalized text with reversible spans |
| 3. Build source graph         | Create direct reply, quote, forward, thread, and message-version edges                                                       | `MessageRelation` candidates                     |
| 4. Decompose semantics        | Extract zero or more event candidates and zero or more non-event semantic roles                                              | Candidate event ledger                           |
| 5. Create or resolve episodes | Create provisional episodes from initiation events; resolve modifiers against compatible episodes                            | Ranked episode candidates                        |
| 6. Candidate replay           | Replay candidate events against each proposed episode                                                                        | Before/after state diffs                         |
| 7. Validate                   | Run structural, provenance, transition, lifecycle, and semantic checks                                                       | Errors, warnings, blockers                       |
| 8. Human adjudication         | Accept or correct event, evidence, target, event order, and relationship role independently                                  | Immutable adjudications                          |
| 9. Canonical replay           | Replay accepted events using a versioned reducer                                                                             | Verified final state and state hash              |
| 10. Generate fixture          | Save messages, expected events, links, evidence, snapshots, and final state                                                  | Gold regression fixture                          |
| 11. Distill rules             | Mine recurring verified patterns and generate deterministic candidate rules                                                  | Candidate rule version                           |
| 12. Certify and deploy        | Run fixtures, holdouts, negative tests, and shadow comparisons                                                               | Certified production rules                       |

### Telegram ingestion requirements

Telegram’s direct reply field represents the immediate replied-to message and does not recursively include the whole reply chain. Edited messages are delivered as distinct update forms. Therefore, the system must reconstruct its own relationship graph and preserve message versions. Bot API updates are retained for no more than 24 hours, so continuous capture should be persisted promptly; historical MTProto history retrieval exists but is restricted to user accounts. ([Telegram][2])idence offsets in an explicitly declared coordinate system. Telegram entities and quote positions use UTF-16 code units, which also aligns conveniently with browser string indexing. Storing both UTF-16 and Unicode code-point offsets is safer for mixed backend languages. ([Telegram][3])age revisions

Support two projection policies:

| Policy             | Behavior                                                                  | Use                                               |
| ------------------ | ------------------------------------------------------------------------- | ------------------------------------------------- |
| `AS_OBSERVED`      | Original content applies first; edited content supersedes it at edit time | Historical audit and reconstruction               |
| `CANONICAL_LATEST` | Latest accepted version is treated as the canonical message content       | Training data and latest published interpretation |

Never overwrite an earlier message version or extracted event. Mark it as superseded.

---

## 4. Alternative workflows and tradeoffs

| Workflow                                              | Strength                                               | Tradeoff                                          | Recommended use                                             |
| ----------------------------------------------------- | ------------------------------------------------------ | ------------------------------------------------- | ----------------------------------------------------------- |
| **Episode-event-replay review**                       | Verifies linking, extraction, and final state together | More initial backend and UI work                  | Primary architecture                                        |
| **Per-chat deterministic templates first**            | Very high precision for repetitive channels            | Low coverage and poor transfer to new styles      | Fast onboarding of highly regular chats                     |
| **LLM candidate extraction plus deterministic gates** | Broad initial coverage                                 | Variable outputs and significant review load      | Bootstrapping and long-tail fallback                        |
| **Two independent extractors with consensus**         | Disagreement is a useful error signal                  | Higher compute; correlated errors remain possible | Critical events and gold-corpus generation                  |
| **Graph-first relationship review**                   | Efficiently resolves implicit modifiers                | Does not verify extracted values by itself        | Chats with many non-reply updates                           |
| **State-diff fast lane**                              | Reviewers approve concise before/after changes         | Can hide faulty evidence or event decomposition   | Only for certified mature rules with evidence click-through |

The best production system combines the recommended workflow with:

* Chat-specific deterministic rules for high-volume patterns
* LLM candidate generation for unseen patterns
* Episode-level human review for unresolved or high-risk cases
* Random audits of auto-certified cases

---

## 5. Simple web UI for human verification

### A. Review queue

Each row represents an episode or unresolved episode candidate, not a message.

Recommended columns:

* Chat and author profile
* Instrument and side
* Episode start time
* Number of messages and events
* Unresolved target count
* Validation blockers
* Highest-impact event
* New-template or rule-disagreement indicator
* Review status
* Rule-set version

### B. Episode adjudication screen

| Panel                       | Content                                                                                                      |
| --------------------------- | ------------------------------------------------------------------------------------------------------------ |
| **Left: source timeline**   | Raw Telegram messages, edits, reply paths, timestamps, highlighted evidence spans, related/non-related roles |
| **Middle: event ledger**    | Ordered events, payloads, target episode, evidence, rule trace, adjudication status                          |
| **Right: state projection** | State before selected event, state after event, final state, field-level provenance, validation results      |

### Essential interactions

* Select an event to highlight its exact source text.
* Select a state field to jump to every contributing event and evidence span.
* Approve the **event semantics** and **episode target** independently.
* Split one message into multiple events.
* Split one message into multiple signal episodes.
* Merge incorrectly separated episodes.
* Mark a message as `RELATED_NO_STATE_EFFECT`.
* Resolve an ordinal such as `TP2` to a stable target-level ID.
* Correct a parsed value and reselect its source span.
* Mark a value `UNKNOWN` rather than forcing a guess.
* View message-version diffs and the resulting state changes.
* Show all candidate episodes and the resolver’s feature breakdown.
* Finalize only when no blocking conditions remain.

### Never allow silent direct edits to final state

A state-field edit should produce either:

1. A corrected source-derived event with updated evidence, or
2. A clearly marked human-asserted correction event with reviewer provenance

Human assertions without source spans must remain distinguishable from source-grounded extraction.

### Display separate uncertainty dimensions

Do not expose only one confidence number. Show:

* Extraction uncertainty
* Evidence-span uncertainty
* Modality or negation uncertainty
* Episode-link uncertainty
* State-transition conflict
* Source-version uncertainty
* Unsupported-event uncertainty

---

## 6. Structured JSON Schema

The full implementation-oriented schema is available here:

[Download the evidence-first JSON Schema](sandbox:/mnt/data/telegram_trading_signal_evidence_schema.json)

It has been validated as a JSON Schema Draft 2020-12 document. Draft 2020-12 provides the current released JSON Schema validation dialect and supports reusable definitions and conditional validation. ([JSON Schema][4])level shape

```json
{
  "schema_version": "1.0.0",
  "dataset_id": "dataset-2026-06",
  "generated_at": "2026-06-19T12:00:00Z",
  "ruleset_version": "rules-18",
  "messages": [],
  "evidence": [],
  "relations": [],
  "events": [],
  "episodes": [],
  "adjudications": [],
  "final_states": []
}
```

### Evidence-first event structure

```json
{
  "event_id": "event-104",
  "source_message_version_id": "msgv-892-v1",
  "event_index": 0,
  "event_type": "STOP_TO_BREAKEVEN",
  "affects": ["INSTRUCTION"],
  "effective_at": "2026-06-18T10:15:00Z",
  "target_resolution": {
    "status": "RESOLVED",
    "episode_ids": ["episode-btc-81"],
    "candidates": [
      {
        "episode_id": "episode-btc-81",
        "score": 91,
        "reason_codes": [
          "EXACT_INSTRUMENT",
          "UNIQUE_COMPATIBLE_OPEN_EPISODE",
          "SAME_AUTHOR"
        ]
      }
    ],
    "resolution_method": "DETERMINISTIC_RULE",
    "resolution_margin": 34
  },
  "payload": {
    "stop_loss": {
      "mode": "BREAKEVEN",
      "reference": "AVERAGE_ENTRY",
      "price": null
    }
  },
  "evidence_ids": ["evidence-301"],
  "field_evidence": {
    "/payload/stop_loss/mode": ["evidence-301"],
    "/payload/stop_loss/reference": ["evidence-301"]
  },
  "extraction": {
    "method": "RULE",
    "extractor_version": "extractor-9",
    "ruleset_version": "rules-18",
    "rule_ids": ["stop-to-be-en-3"],
    "model_id": null,
    "prompt_version": null,
    "confidence": 0.997,
    "trace_ref": "trace-551"
  },
  "adjudication": {
    "status": "AUTO_CERTIFIED",
    "adjudication_ids": []
  }
}
```

### Important schema choices

* Prices are decimal strings, avoiding floating-point distortion.
* Entry and target levels have stable IDs.
* Every event field can map to one or more evidence IDs using JSON Pointer paths.
* Explicit `NONE`, `UNSET`, and `UNKNOWN` states are supported.
* Instruction state and execution state are separate.
* Message edits are immutable versions.
* Both candidate and accepted relationships are retained.
* Human assertions are represented separately from source spans.
* Final states include a reproducible state hash and projection version.
* Referential integrity beyond JSON Schema—such as checking that an evidence ID exists—is enforced by application validators.

---

## 7. Rule-distillation workflow

Do not distill one monolithic extraction prompt. Distill separate rule families:

1. Text and number normalization
2. Signal-initiation detection
3. Event detection
4. Field extraction
5. Negation, question, quotation, and modality rules
6. Episode target resolution
7. State-transition guards
8. Chat-specific conventions
9. Related-but-no-effect classification

### Workflow

| Stage               | Operation                                                                           | Promotion gate                                 |
| ------------------- | ----------------------------------------------------------------------------------- | ---------------------------------------------- |
| Select fixtures     | Use only adjudicated gold episodes                                                  | No unresolved links or evidence errors         |
| Segment             | Group by chat, author role, language, template, and event type                      | Sufficient positive and hard-negative examples |
| Propose rules       | LLM or programmatic miner proposes regex, token grammar, aliases, and guards        | Rule must produce an inspectable AST           |
| Attach evidence     | Named captures must map output fields to raw spans                                  | Every extracted field grounded                 |
| Add negative rules  | Generate questions, negations, quotations, hypothetical statements, and near-misses | Hard-negative suite passes                     |
| Compile             | Convert rule AST into deterministic executable rule                                 | No arbitrary generated code                    |
| Evaluate extraction | Event type, values, and source spans                                                | Precision threshold passed                     |
| Evaluate linking    | Episode target and candidate margin                                                 | Link threshold passed separately               |
| Evaluate replay     | Intermediate and final state exact match                                            | All sequence fixtures pass                     |
| Shadow run          | Compare old and new rule-set outputs                                                | Every changed gold episode explained           |
| Certify             | Register immutable rule version                                                     | Statistical and regression gates passed        |
| Monitor             | Track precision, abstention, and template drift                                     | Certification revoked on drift                 |

### Example deterministic rule representation

```json
{
  "rule_id": "stop-to-breakeven-en-v3",
  "scope": {
    "chat_profiles": ["channel-profile-12"],
    "languages": ["en"]
  },
  "match": {
    "positive_regex": "\\b(move|set)\\s+(the\\s+)?(sl|stop)\\s+(to\\s+)?(be|breakeven)\\b",
    "negative_regex": "\\b(do not|don't|should we|maybe)\\b|\\?"
  },
  "extract": {
    "event_type": "STOP_TO_BREAKEVEN",
    "evidence_capture": "full_match"
  },
  "target": {
    "strategy": "reply_ancestor_then_unique_compatible_open_episode"
  },
  "guards": [
    "episode.lifecycle_status == ACTIVE",
    "episode.identity.instrument_is_compatible == true"
  ],
  "priority": 90
}
```

### Proper LLM role

The LLM may:

* Propose candidate events and evidence spans
* Cluster recurring message templates
* Propose deterministic rule ASTs
* Generate hard-negative and mutation tests
* Explain why a case is ambiguous

The LLM should not:

* Directly mutate final state
* Silently invent ungrounded values
* Auto-link ambiguous episodes
* Promote its own rules
* Be the sole verifier of its output

---

## 8. Modifier messages that do not reply to the original signal

Treat target resolution as a state-aware retrieval and ranking problem.

### Step 1: Build candidates

Candidate episodes should satisfy event-specific lifecycle windows:

| Event family                    | Eligible episodes            |
| ------------------------------- | ---------------------------- |
| Entry, TP, SL, or risk mutation | Provisional or active        |
| Cancellation                    | Pending or active            |
| Partial/full close              | Open or partially closed     |
| TP/SL hit report                | Active or recently completed |
| Reopen                          | Recently cancelled or closed |

### Step 2: Apply hard constraints

Reject a candidate when:

* Explicit instrument conflicts
* Explicit side conflicts
* Episode began after the modifier
* Event is impossible in the current lifecycle
* Referenced target or entry cannot exist in that state
* Thread or topic constraints conflict
* The episode was superseded or merged

### Step 3: Rank compatible candidates

Illustrative initial scoring:

| Feature                                          | Suggested weight |
| ------------------------------------------------ | ---------------: |
| Direct reply to episode message                  |             +100 |
| Reply to a descendant or related episode message |              +70 |
| Exact explicit instrument match                  |              +40 |
| Explicit episode alias, such as “BTC scalp”      |              +35 |
| Referenced price matches an existing level       |              +25 |
| `TP2` is valid and active in current state       |              +25 |
| Unique compatible open episode                   |              +20 |
| Same Telegram topic/thread                       |              +20 |
| Same signal-author role                          |              +10 |
| Strong temporal proximity                        |         0 to +15 |
| Conflicting instrument or side                   |      Hard reject |
| Incompatible lifecycle                           |      Hard reject |

Auto-link only when:

* The resolver itself is certified
* The top score exceeds a calibrated threshold
* The margin over the second candidate exceeds a calibrated threshold
* No hard ambiguity remains

An initial conservative policy might require a score of at least `70` and a margin of at least `25`, calibrated separately per chat profile.

### State-aware resolution examples

* `"TP2 hit"` should favor episodes that currently have an active second target.
* `"Move SL to BE"` should favor an active episode with a defined entry basis.
* `"Close the remaining 50%"` should require a compatible open or partially closed position.
* `"Cancel BTC"` should distinguish a pending signal from an already open position.
* `"Close all longs"` may legitimately target several episodes; emit one shared multi-target action or separate linked events with common source evidence.

When several same-instrument, same-side episodes are active and no differentiator exists, the correct output is `UNRESOLVED`, not a low-confidence guess.

---

## 9. Replies that are related but do not modify the signal

Separate these properties:

* `relation_type`: how messages are structurally connected
* `semantic_role`: what the related message is doing
* `state_effect`: mutation, observation, or none

| Message                    | Semantic role         | State effect                                               |
| -------------------------- | --------------------- | ---------------------------------------------------------- |
| “Move SL to BE”            | Modifier              | Instruction mutation                                       |
| “Close half now”           | Modifier              | Execution/lifecycle mutation                               |
| “TP1 hit”                  | Status report         | Execution observation                                      |
| “Why did you enter here?”  | Question              | None                                                       |
| “Nice trade”               | Celebration           | None                                                       |
| “Resistance is at 68k”     | Rationale/commentary  | None unless a verified convention makes it a target update |
| “Should we move the stop?” | Question/hypothetical | None                                                       |
| “Do not move SL yet”       | Negated instruction   | Usually none; retains existing state                       |
| Quoted old signal text     | Quotation             | None unless the author explicitly reasserts it             |
| Risk disclaimer            | Disclaimer            | None                                                       |

### State-changing event gate

A source-derived state mutation should generally require:

1. A recognized action or verified channel idiom
2. An assertive, imperative, or clearly declarative modality
3. A resolvable affected slot
4. No dominating negation, question, hypothetical, or quotation context
5. A compatible target episode
6. Passing transition preconditions

A direct reply satisfies none of these semantic requirements by itself.

---

## 10. Accuracy guarantees, validation, and regression testing

### What can actually be guaranteed

Semantic intent cannot be mathematically guaranteed when the source itself is ambiguous. The system can guarantee process and structural properties and statistically bound observed accuracy.

| Guarantee                     | Enforcement                                                                              |
| ----------------------------- | ---------------------------------------------------------------------------------------- |
| Source immutability           | Versioned raw payloads and hashes                                                        |
| Evidence integrity            | Span quote and offset must match the referenced message hash                             |
| Provenance completeness       | Every non-null source-derived field requires evidence                                    |
| Deterministic replay          | Same accepted events, reducer version, and order produce the same state hash             |
| Idempotent processing         | Duplicate message/update ingestion cannot duplicate state effects                        |
| No silent state editing       | State is always produced by replay                                                       |
| No unresolved verified export | Unresolved targets and blocking validations exclude gold status                          |
| Rule traceability             | Every auto-produced event records rule/model and version                                 |
| Change visibility             | Rule-set updates produce episode-level semantic diffs                                    |
| Quality separation            | Draft, auto-certified, human-verified, double-verified, and gold outputs remain distinct |

### Validation layers

#### Structural

* JSON Schema passes
* IDs and references exist
* Event and evidence indexes are unique
* Decimal strings parse correctly
* Range low is not greater than range high

#### Evidence

* Evidence message version exists
* UTF-16 offsets are valid
* Stored quote equals the referenced substring
* Message hash matches
* Every populated event field has field-level evidence
* Normalized spans map back to raw text

#### Target and chronology

* Target episode predates the event
* Explicit symbol and side are compatible
* Event order is total and deterministic
* Superseded message versions cannot remain simultaneously active
* Event target is not a merged or invalid episode

#### State transitions

* `TP_HIT` references an existing active target
* `ENTRY_FILLED` references an existing entry level
* Partial-close fraction is between zero and one when known
* Known cumulative closes do not exceed the open position
* Full close leaves no known open fraction
* `STOP_NONE` cannot coexist with an active stop price
* Cancellation and full close are not treated as interchangeable
* Post-terminal mutations require an explicit reopen or correction event

#### Semantic warnings

These should usually be warnings rather than unconditional failures:

* Long stop above all entries
* Short stop below all entries
* Long targets below the entry region
* Short targets above the entry region
* Implausible decimal scale
* Duplicate entry or target values
* Sudden symbol change in one episode

Strategies and channels can legitimately violate common assumptions, so only chat-certified invariants should become hard blockers.

### Metrics

Measure separately:

* Event-type precision and recall
* Field-value exact match
* Evidence-span exact match
* Episode-link accuracy
* No-effect classification accuracy
* Event-sequence exact match
* Final-state exact match
* Full-episode exact match
* Abstention rate
* Auto-certification coverage
* Accuracy by chat, author, event type, language, and rule version

Do not report only message-level accuracy.

### Statistical release criterion

For auto-certification, use a lower confidence bound rather than observed precision alone. For example, under representative independent sampling:

* Zero errors in **598** reviewed cases gives a one-sided 95% lower bound of approximately **99.5%**.
* Zero errors in **2,995** reviewed cases gives a one-sided 95% lower bound of approximately **99.9%**.

Certification should be stratified by event type and chat profile. Pooling thousands of easy entry extractions must not certify a weak cancellation or close-position rule.

### Regression fixtures

Each fixture should contain:

```text
Input:
  message versions
  reply/quote metadata
  chat profile
  projection policy

Expected:
  candidate semantic roles
  accepted and rejected events
  exact evidence spans
  accepted and rejected episode links
  event ordering
  intermediate state after every event
  final state
  validation outputs
  unresolved cases
```

### Required test classes

* Rule-level positive tests
* Rule-level hard-negative tests
* Episode-link resolver tests
* State-reducer unit tests
* End-to-end episode fixtures
* Property-based transition tests
* Duplicate-ingestion and out-of-order tests
* Message-edit and deletion tests
* Temporal holdout tests
* Cross-chat holdout tests
* Rule-set semantic diff tests
* Metamorphic tests covering:

  * Whitespace and line-break changes
  * Emoji
  * Unicode variants
  * `1,250` versus `1.250`
  * Upper/lower case
  * Quoted signal text
  * `"TP1 hit?"` versus `"TP1 hit"`
  * `"close"` versus `"do not close"`

A rule release must not alter a gold fixture unless that fixture is explicitly migrated and adjudicated.

---

## 11. Active-learning strategy

Prioritize review using expected error impact rather than raw model uncertainty:

```text
priority =
    estimated_error_probability
    × state_change_impact
    × pattern_frequency
    × novelty_or_drift
    ÷ expected_review_cost
```

### Highest-priority cases

1. Ambiguous episode links
2. Rule or extractor disagreement
3. Stop-loss, cancellation, full-close, and partial-close events
4. Invariant failures
5. Edited messages that change projected state
6. New high-frequency templates
7. Multiple same-symbol concurrent episodes
8. Unsupported modifiers
9. Low target-resolution margin
10. New language, author, or formatting cluster

### Preserve unbiased auditing

A practical initial review allocation:

* **50%** ambiguity, disagreement, and validation failures
* **25%** novel or high-frequency uncovered patterns
* **15%** stratified audit of auto-certified outputs
* **10%** uniform random sample

The random and high-confidence audit portions are necessary because uncertainty-based review alone misses confidently wrong rules.

### Selection unit

Select entire episodes for review, but surface the exact events responsible for priority. Reviewing an isolated message may hide the actual linkage or state error.

---

## 12. Failure modes and uncertainty exposure

| Failure mode                           | UI treatment                                                                |
| -------------------------------------- | --------------------------------------------------------------------------- |
| One message opens several signals      | Offer “split into episodes”; show separate evidence spans                   |
| One message contains several modifiers | Show multiple event rows with independent approval                          |
| Modifier has several plausible targets | Display ranked episode candidates and feature contributions                 |
| Two same-symbol trades overlap         | Block auto-link unless an explicit differentiator exists                    |
| Reply targets an intermediate comment  | Show the full ancestor path; do not jump automatically to the root          |
| Message was edited                     | Show source-version diff and state-impact diff                              |
| Message was deleted                    | Preserve captured version plus deletion tombstone                           |
| Number locale is ambiguous             | Show raw token, normalized number, and locale rule                          |
| Partial close has no quantity          | Set `quantity_known=false`; never assume 50%                                |
| “BE” is ambiguous in a new chat        | Mark unknown until a chat-specific convention is verified                   |
| Quoted or forwarded signal text        | Visually separate quoted assertion from current-author assertion            |
| Conflicting updates                    | Show event order, reducer failure, and alternative ordering if applicable   |
| Unsupported modifier                   | Preserve as `UNSUPPORTED_MODIFIER`; block verified finalization if material |
| LLM supplies a field without evidence  | Reject at validation time                                                   |
| Human correction lacks source support  | Mark as human assertion and exclude from source-grounded quality claims     |
| Rule drift                             | Show rule version, recent audit metrics, and certification status           |

### UI uncertainty principle

Every uncertainty should answer:

* **What is uncertain?**
* **Which alternatives exist?**
* **What evidence supports each alternative?**
* **What state fields would change under each choice?**
* **Does the uncertainty block verified export?**

---

## 13. Phased implementation plan

| Phase                                        | Build                                                                                                | Exit criterion                                                         |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| **0. Ontology and acceptance contract**      | Event taxonomy, transition table, quality tiers, `NONE/UNSET/UNKNOWN` semantics, accuracy metrics    | Representative episodes can be expressed without opaque labels         |
| **1. Immutable source ledger**               | Message versions, raw payload hashes, reply graph, edits/deletes, normalization maps, evidence spans | Idempotent ingestion and exact span round-trip                         |
| **2. Event and reducer core**                | Event schema, stable level IDs, target selectors, pure reducers, validations, state hashes           | Deterministic replay across synthetic and real fixtures                |
| **3. Episode adjudication UI**               | Three-panel reviewer, target candidates, event correction, split/merge, no-effect relations          | Reviewers can resolve known cases without editing state directly       |
| **4. Gold corpus and fixture runner**        | Immutable adjudications, sequence fixtures, regression dashboard, reviewer disagreement workflow     | Gold episodes reproduce exact intermediate and final states            |
| **5. Rule registry and distillation**        | Rule AST, compiler, scope, negative guards, rule metrics, certification                              | First high-precision rules safely auto-certify narrow patterns         |
| **6. Active learning and shadow deployment** | Risk queues, novelty clusters, random audits, old/new semantic diffing                               | Review effort concentrates on errors without losing drift detection    |
| **7. Scale and governance**                  | Double review for critical cases, rule revocation, quality-tier exports, audit logs                  | Accuracy and coverage measurable by chat, event type, and rule version |

## Final design decision

The source of truth should be:

```text
Immutable message versions
    + accepted relationship graph
    + accepted ordered event log
    + immutable adjudications
```

The final trading signal is a reproducible projection of those records.

That design turns human review into an accumulating engineering asset: every adjudicated episode becomes a regression fixture, every recurring fixture pattern can become a deterministic rule, and every rule remains measurable, reversible, and traceable to exact source evidence.

[1]: https://www.w3.org/TR/prov-o/?utm_source=chatgpt.com "PROV-O: The PROV Ontology"
[2]: https://core.telegram.org/bots/api?utm_source=chatgpt.com "Telegram Bot API"
[3]: https://core.telegram.org/bots/api "Telegram Bot API"
[4]: https://json-schema.org/draft/2020-12?utm_source=chatgpt.com "Draft 2020-12"
