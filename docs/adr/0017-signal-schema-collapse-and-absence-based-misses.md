# Signal schema collapse: `raw_signal_event` + `extracted_signal` → `signal`, misses become absence

We collapsed the extraction schema from three tables (`raw_signal_event`,
`extracted_signal`, `unrecognized_signal`) into one: `signal`, keyed by the
message it came from (`user_id`, `external_id`, `external_message_id`, plus a
surrogate `id` PK). A "miss" — a message the miner did not turn into a signal —
is no longer a stored row; it is the **absence** of a `signal` for a message,
recovered by an anti-join between `raw_message` and `signal`. Alongside this we
generated all enum-backed CHECK constraints from the domain `StrEnum`s
(`enum_check()` in `storage/models.py`), moved feed status/history-depth into
first-class enums (`FeedStatus`, `HistoryDepth` in `domain/feed.py`), dropped
several always-dead columns and enum members, and squashed the 22-migration
history into one baseline (`migrations/versions/0001_init.py`), verified
byte-identical to the old chain by an empty `pg_dump` diff.

We did this because the schema this replaces was designed for a world that no
longer exists. `RawSignalEvent` was a candidate-filter gate feeding two
extractors (a deterministic parser and an LLM fallback) that produced one of
two outcomes, `ExtractedSignal` or `UnrecognizedSignal` — a real one-of-two
lifecycle when misses carried diagnostic data (`reason`, `attempted_methods`)
and a second extractor could recover a first extractor's miss. [ADR
0016](0016-remove-legacy-loop-and-regex-rule-pipeline.md) already removed the
regex-rule pipeline and left the miner as the only extractor. This rewrite
finishes that trajectory: the LLM fallback path is gone entirely
(`ExtractionMethod`, `LlmExtractor`, `RuleDistiller` and everything downstream
of them), and Mining Confirm (`confirm_mined_signals`) persists a candidate
message and its extraction **together, in one write** — there is no
intermediate "candidate event" a miss could reference, so `UnrecognizedSignal`
had nothing left to record beyond "no `signal` row exists for this message,"
which is answerable without persisting anything.

Once the event and its 1:1 extraction projection were always written and read
together, keeping them as two joined tables cost real bugs. The clearest one:
Mining Confirm's old persistence upserted per-candidate rather than replacing
the feed's whole projection, so re-confirming a *smaller* accepted set than a
prior confirm left the de-selected families' `extracted_signal` rows orphaned —
they resurrected on reopen because nothing deleted them. Confirm is now
**replace-the-feed-projection**: one transaction deletes every `signal` row for
`(user_id, external_id)`, then inserts exactly the accepted candidates'
signals. This is idempotent (a re-confirm of the same set is `+0`/`-0`) and
makes the persisted set always exactly the accepted set, closing the orphan bug
at the root instead of patching around it.

## Considered options

- **Keep three tables, drop only the dead LLM-path columns**: rejected. The
  one-of-`{ExtractedSignal, UnrecognizedSignal}` invariant was the entire reason
  for two clean outcome tables ([ADR 0006](0006-extraction-outcomes-shape-and-lifecycle.md)).
  With one extractor and one-shot persistence, a miss is answerable by asking
  "does a `signal` exist for this message?" — storing an empty-in-effect miss
  row alongside it, and having Confirm write and delete rows in two tables
  every time, buys nothing and keeps the orphan-row failure mode alive.
- **Merge into one `extraction_outcome` table with a nullable one-of shape**
  (an option ADR 0006 itself considered and rejected then, for the two-extractor
  world): still rejected for the same reason ADR 0006 gave — sparse nullable
  columns and a row↔type impedance — but now there is a strictly better third
  option below, because misses no longer need a row at all.
- **Merge into one `signal` table, misses as absence (chosen)**: a `signal` row
  is only ever a successful extraction, so every column stays `NOT NULL` where
  the domain requires it (`symbol`, `side`, `event_type`); "no row for this
  message" *is* the miss, recovered on demand via an anti-join against
  `raw_message`, never persisted. This is the option the removal of the LLM
  fallback and the one-shot Confirm write actually enable.
- **Keep `raw_signal_event` as a separate candidate-flagging row, drop only
  `unrecognized_signal`**: rejected. Nothing produces a candidate independent
  of its extraction anymore — Mining Confirm mines and extracts in the same
  pass — so a standalone event row would carry linkage fields (`event_id`) that
  exist purely to join back to the signal it always accompanies.
- **Leave the 22-migration chain in place**: rejected. Every migration in the
  chain built toward schemas this rewrite deletes (`raw_signal_event`,
  `extracted_signal`, `unrecognized_signal`, the rule/label/drift tables from
  ADR 0016). Carrying that history forward would mean new environments replay
  22 steps of dead schema to arrive at a database that could be created in one.
  Squashing to `0001_init.py` was verified safe by diffing a `pg_dump` of a
  freshly-migrated database against the old chain's end state — the diff was
  empty.

## Consequences

- **Supersedes [ADR 0006](0006-extraction-outcomes-shape-and-lifecycle.md).**
  ADR 0006's two-clean-tables decision rested on two facts that are no longer
  true: two extractors could each independently win or miss (the LLM fallback
  is gone), and a miss carried data worth keeping (`UnrecognizedSignal.reason`,
  `attempted_methods` — gone, because a miss is now just an absent row with
  nothing to say about itself). With both premises removed, the schema ADR
  0006 rejected (one merged table) is now strictly correct, because the
  reasons it was rejected — sparse nullable columns split across a one-of shape
  — never arise when the "empty" side of the one-of is never stored.
- **Amends [ADR 0001](0001-two-layer-raw-capture.md).** Append-only scope no
  longer includes `raw_signal_event`; that table is gone. The two-layer split
  (`raw_message` = 100% capture, insert-only; everything derived from it) still
  holds, but the derived layer above `raw_message` is now the recomputable
  `signal` projection, not a second append-only capture table.
- **Updates [ADR 0015](0015-mining-confirm-persists-rules-and-rederives.md).**
  ADR 0015's synchronous re-derivation pipeline (`derive_candidates →
  sweep_advisory → rematerialize_signal_outcomes → update_evidence_candidacy`)
  was already superseded by the miner-based Confirm in ADR 0016. This ADR
  updates the *persistence* half of that superseding design once more: Confirm
  now replaces the feed's `signal` projection wholesale
  (`_replace_feed_signals` in `mining_confirm.py`) rather than upserting
  per-candidate, fixing the orphaned-row bug described above.
- **Dropped for good:** `raw_signal_event.matched_reasons`,
  `extracted_signal.references_message_id` (always-dead columns),
  `MatchReason`, `SignalEventType.UNRECOGNIZED`, `ExtractionMethod` (and its
  `LLM_FALLBACK` member), `LlmExtractor`, `RuleDistiller`, the
  `unrecognized_signal` table, and `materialization.py` / `ExtractOutcome`.
- **CHECK constraints can no longer drift from Python.** `enum_check()` builds
  every enum-backed `CheckConstraint` from the corresponding domain `StrEnum`
  (`ck_signal_side`, `ck_signal_event_type`, `ck_feed_status`,
  `ck_feed_history_depth`, `ck_user_account_plan`, and the risk-config enums);
  adding or renaming an enum member updates the constraint for free.
- **New domain surface:** `FeedStatus` and `HistoryDepth` in `domain/feed.py`
  replace scattered string literals for feed lifecycle and backfill depth.
- **Migration history resets.** `migrations/versions/0001_init.py` is the sole
  baseline; the prior 22-migration chain is gone from the repo (schema
  byte-identical, proven by an empty `pg_dump` diff against the old chain's
  head).
- **`parser_confidence` (the ProviderScore component) survives, redefined.**
  It no longer measures an `extraction_method` distribution (that signal is
  gone). It is now a recognition rate — extracted signals over all candidate
  messages, where a "miss" is a candidate with no `signal` row (the anti-join)
  — computed in `measure_parser_confidence` (`features/provider_scores/hygiene.py`).

## Superseded by hindsight

ADRs are historical records of a decision made with the information available
at the time, not evergreen design law. ADR 0006's two-outcome-table shape was
the right call when it was written — two live extractors genuinely could
disagree, and a miss's `reason` was real diagnostic signal. Neither is true
anymore. This ADR does not mean ADR 0006 was wrong in 2025; it means the
ground it stood on (the LLM fallback path, the miss-as-data model) was removed
by later work, and the schema is now free to reflect the simpler system that
resulted.
