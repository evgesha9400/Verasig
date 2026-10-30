# Remove the legacy label→distill→verify loop and the orphaned regex-rule pipeline

Template mining ([ADR 0013](0013-mining-wizard-replaces-label-distill-verify-frontend.md))
replaced the label→distill→verify loop in the UI, and the server-side
**miner-based** Mining Confirm (`confirm_mined_signals`,
`POST /feeds/{external_id}/mining/confirm`) made the deterministic template miner
the single extractor: on Confirm it persists each accepted template family's
candidate straight into `raw_signal_event` + `extracted_signal` and marks the feed
`verified`. It writes **no** `filter_rule` / `parser_rule`.

That left the entire regex-rule + golden-label + drift machinery
**dead-in-effect**: nothing wrote rules, so `candidate_derivation` (the only drift
producer) ran against an empty ruleset, `deterministic_parser` / `extract_service`
extracted nothing, and `golden_label` was never written — yet several consumers
still read the empty tables. This ADR records the big-bang removal of that dead
machinery and the schema that backed it.

## What was removed

- **Regex-rule pipeline**: `candidate_derivation`, `candidate_filter`,
  `deterministic_parser`, `extract_service`, `llm_fallback`, `rules/views`
  (`present_rules`), and the rule functions of `rules/repository`.
- **Drift**: `drift_repository`, `domain/drift.py`, and the `ParserDriftWarning`
  wiring in `ExtractOutcome` / `outcome_repository`.
- **Label infrastructure**: `domain/label.py` (`GoldenLabel` / `LabelKind`), the
  label functions of `rules/repository`, and the `golden_label` reads in the
  deletion / backtest / signals consumers.
- **LLM fallback ports**: `domain/llm_ports.py`, `shared/json_object.py` (the
  `foundation/llm` runner was already gone).
- **Schema** (migration `0016`, forward-only per the `0015` lab-table-drop
  convention): tables `filter_rule`, `parser_rule`, `golden_label`,
  `filter_drift_warning`, `parser_drift_warning`; columns `feed.verify_attempt`
  and `raw_signal_event.filter_rule_id`.

## What survives

`raw_signal_event`, `extracted_signal`, `unrecognized_signal`,
`deleted_signal_evidence`, `parser_overlay`, the miner (`template_mining/*`,
`mining_confirm`, `mine_routes`), `event_repository` / `outcome_repository`, and
`materialization` — now reduced to gap-filling: any event the miner did not
confirm is projected as an `UnrecognizedSignal(reason="no_match")` so the
one-of-`{ExtractedSignal, UnrecognizedSignal}` invariant still holds for provider
scoring, hygiene, and the lifecycle fold.

## Deletion candidacy is now `was_signal_candidate`

The deletion consumers previously decided "is this a signal deletion?" from golden
`SIGNAL` labels **and** a rule-backed feed gate (`read_rule_feed_ids`). Both
sources are gone. `was_signal_candidate` — set at detection time iff the deleted
message had a `RawSignalEvent`, which only the miner writes on Confirm — is now the
single authority. `summarize_deletions`, `signals/views`, `simulation/backtesting`,
`feeds/deletion_rescan`, `feeds/feed_views`, and the `feeds/routes` rescan-ready
gate all read it directly; the now-orphaned `read_rule_feed_ids` and
`update_evidence_candidacy` were dropped. This is behaviourally equivalent
post-cleanup — the rule inputs were already always-empty — and is precisely what
lets deletion badges render (the old gate would have made every deletion
non-signal once no rules were written).

## Intentional behaviour changes

- **Orphan-mod detection dropped.** It read `MODIFIER` golden labels, which no
  longer exist; `GET /signals` now always returns `orphanMods: []` (the frontend
  already tolerates an empty list). No rule-free equivalent exists — re-introducing
  it is a product decision.
- **Live real-time rule-based extraction removed.** It was already dead (no rules
  were written). Making the *live* ingestion path miner-based is **out of scope**
  here and is flagged for product.

## Superseded ADRs

- [ADR 0002](0002-human-assisted-rule-distillation.md) (human-assisted rule
  distillation) and [ADR 0005](0005-distilled-filter-and-advisory-gate.md)
  (distilled filter + advisory gate): the distillation loop they defined is fully
  removed.
- [ADR 0015](0015-mining-confirm-persists-rules-and-rederives.md) (Mining Confirm
  persists compiled rules): superseded by the miner-based `confirm_mined_signals`,
  which persists structured signals rather than rules. Its re-derivation pipeline
  (`derive_candidates → sweep_advisory → rematerialize_signal_outcomes →
  update_evidence_candidacy`) is gone, along with the `_has_saved_rules`
  rescan-ready gate it relied on (readiness is now feed `status`).
- [ADR 0013](0013-mining-wizard-replaces-label-distill-verify-frontend.md) remains
  in force: the mining wizard is the UI.

## Consequences

- Losing the dropped tables' data is accepted — they were dead-in-effect.
- `raw_signal_event.matched_reasons` and the `MaterializationPath.FILTER_RULE` /
  `PARSER_BACKFILL` enum values are retained but now miner-unset (general
  provenance, not rule-specific); a future provenance-model cleanup may remove them.
