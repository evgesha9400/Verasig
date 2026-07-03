# Mining replaces Label/Distill/Verify on the frontend, but the backend routes they called stay untouched

The frontend's swipe-based Label → Distill → Verify pipeline is replaced end to
end by a single **Mining** step: a parser-first, deterministic wizard embedded
in the pipeline between Backfill and Exchange. Mining mines candidate parser
templates from a feed's captured messages, lets the operator accept or reject
template families, and compiles the accepted families into rules — all in the
browser, without calling the backend routes the old screens used.

We are **not modifying or removing** `label_routes.py`, `distill_routes.py`,
`verify_routes.py`, or `rule_distiller.py`
(`apps/backend/src/verasig/features/rules/`), because
`apps/backend/src/verasig/features/signals/deterministic_parser.py` and
`extract_service.py` still consume the `ParserRule` records those flows
persist (and, upstream, `apps/backend/src/verasig/features/feeds/candidate_derivation.py`
still consumes both `FilterRule` and `ParserRule` for candidate gating, with
`candidate_filter.py` consuming `FilterRule`), and live signal extraction
depends on that data continuing to exist and to be servable. Deleting or altering the producers would risk the
consumers with no replacement in place. This ADR exists so a future reader
finds those four backend files with no caller and understands why: the
frontend entry points were retired on purpose, not by oversight, and the
backend was deliberately left alone as a separate, deferred piece of work.

## Considered options

- **Modify the backend now to accept Mining's compiled rules**: rejected for
  this change, deferred as follow-up work. It would require new persistence
  and API surface for Mining's rule shape and is a larger, independent piece
  of work than "replace the frontend wizard."
- **Keep the old swipe UI running in parallel as a fallback**: rejected.
  Contradicts the requirement to completely replace Label/Distill/Verify with
  Mining, and doubles the maintenance surface for two UIs that both claim to
  produce the operator's ruleset.

## Consequences

- `POST /feeds/{id}/distill`, `POST /feeds/{id}/verify`, and the label
  endpoints become unreachable from the product the moment this ships — no UI
  calls them. They are not deleted; they are dead code from the frontend's
  perspective only.
- The `ParserRule`/`FilterRule` tables and the extraction pipeline reading
  them (`deterministic_parser.py`, `extract_service.py`) remain live and
  unaffected. Live signal extraction keeps working off whatever rules the old
  human-assisted distillation loop ([ADR 0002](0002-human-assisted-rule-distillation.md),
  [ADR 0005](0005-distilled-filter-and-advisory-gate.md)) already produced.
- Mining's compiled rules exist only in frontend memory for the duration of
  the wizard session and are **not persisted to the backend at all**. Nothing
  the operator accepts in Mining reaches `ParserRule`/`FilterRule` storage or
  the extraction pipeline today.
- A follow-up task (explicitly out of scope here) must wire Mining's
  accepted-family rules into backend persistence before extraction can
  benefit from Mining-produced rules in production. Until that lands, Mining
  is a review/preview tool and the backend keeps extracting against whatever
  rules distillation already wrote.
- [ADR 0002](0002-human-assisted-rule-distillation.md) and
  [ADR 0005](0005-distilled-filter-and-advisory-gate.md) are **not
  superseded** — the human-assisted distillation loop they describe is still
  the mechanism actually feeding live extraction — but their frontend entry
  points (the Label/Distill/Verify screens) are now dead.
