# Mining Confirm persists compiled rules and re-derives extraction, evidence, and status

Mining Confirm (`POST /feeds/{external_id}/mining/rules`) makes the operator's
browser-mined ruleset authoritative. It persists the compiled `FilterRule` +
`ParserRule`s into the **existing** rule tables, then synchronously re-derives
everything downstream: candidate events through the new filter, a parser sweep
for late-materialized misses, a full re-extraction of every event, a recompute
of deletion-evidence candidacy from the rules, and a server-side transition of
the feed to `verified`.

This closes the gap [ADR 0013](0013-mining-wizard-replaces-label-distill-verify-frontend.md)
left open: Mining was preview-only, its rules died with the browser session, and
"verified" was a frontend-only localStorage patch. Live extraction, provider
scoring, and deletion detection all still ran off whatever the legacy
distillation loop had written — never the operator's Mining decisions.

## How it works

- **Reuse, not a parallel store.** Rules persist through
  `features/rules/repository.py` — the same boundary the legacy distillation loop
  writes to and that `candidate_derivation`, `deterministic_parser`, and
  `extract_service` already read. Mining is simply a second rule *producer*.
- **Replace, don't append.** `read_filter_rules` / `read_parser_rules` return
  every version and `ExtractService` is first-match-wins, so a stale version
  would shadow the re-mined ruleset. Confirm deletes the feed's prior rules and
  inserts the new ones at `next_rule_version(...)`.
- **Provenance.** Mined rules carry `distilled_from_label_ids = []` (they come
  from templates, not golden labels) and a greppable id convention
  `{user}:{feed}-mining-filter-v{n}` / `-mining-parser-{i}-v{n}`, mirroring the
  distillation loop's `-filter-v{n}` scoping.
- **Re-derivation pipeline** (`mining_confirm.confirm_mining_rules`, one
  transaction per step): `derive_candidates` (new FILTER_RULE events) →
  `sweep_advisory` (PARSER_BACKFILL recovery + drift) → `rematerialize_signal_outcomes`
  (re-extract every event; `record_outcome` upserts by `(user_id, event_id)`, so
  it is idempotent) → `update_evidence_candidacy` → `set_status("verified")`.
- **Evidence candidacy is rule-authoritative.** A CONFIRMED deletion's
  `was_signal_candidate` is recomputed as "is it a current candidate, or does its
  retained `original_text` match the rules". The text fallback is required
  because a wiped-and-recaptured feed ([ADR 0014](0014-full-refetch-wipes-and-recaptures.md))
  keeps deletion evidence with no surviving `raw_message` row. Downgrades are
  allowed: operator-approved rules supersede the recall-first seed heuristic.
- **No escape hatches from the wire.** `mining_schemas` omits `python_filter` /
  `python_extractor`, so no dotted path can arrive from a browser.

## Considered options

- **New mining-scoped tables**: rejected. The consumers already read
  `filter_rule` / `parser_rule`; a second store would need a second reader
  everywhere extraction runs.
- **Append a new version without deleting the old**: rejected. First-match-wins
  extraction would let a stale version shadow the re-mine.
- **Async job + SSE (like distill)**: deferred. Re-derivation is CPU-bound and
  seconds-scale; the sync handler runs in FastAPI's threadpool. If confirm p95
  exceeds ~10s on large feeds, lift it to the `JobRegistry` + `sse_stream`
  pattern `distill_routes` already uses.
- **Persist per-message verdicts instead of rules**: rejected. It would fix
  scam-detection candidacy but leave live extraction on the old rules — Confirm
  would still not teach the parser.

## Consequences

- **[ADR 0013](0013-mining-wizard-replaces-label-distill-verify-frontend.md) is
  amended** (see its Amendment section): its "not persisted at all" consequence
  is superseded.
- The [ADR 0002](0002-human-assisted-rule-distillation.md) /
  [ADR 0005](0005-distilled-filter-and-advisory-gate.md) distillation loop
  becomes the *legacy* rule producer; both feed the same tables.
- Live extraction and provider scoring now reflect the operator's Mining
  decisions. Feed `verified` status is real and server-owned; the frontend patch
  is superseded (its cleanup is follow-up frontend work).
- Persisted rules also satisfy the Check-gaps readiness gate
  (`_has_saved_rules`), so confirming unlocks deletion rescan.
