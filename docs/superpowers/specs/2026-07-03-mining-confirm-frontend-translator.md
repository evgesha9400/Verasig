# Mining Confirm — frontend rule translator (follow-up)

**Status:** design needed. The backend endpoint is done and tested; the frontend
translator is deferred because it is a paradigm bridge, not a shape-map.

## The gap

`POST /feeds/{id}/mining/rules` ([ADR 0015](../../adr/0015-mining-confirm-persists-rules-and-rederives.md))
persists a **backend** ruleset:

- `FilterRule.include_patterns` / `exclude_patterns` — **regexes**.
- `ParserRule.patterns` — **regexes with named groups**; `field_map` maps each
  named group to an `ExtractedSignal` field; `side_aliases` normalizes direction
  words to `LONG`/`SHORT`. Extraction runs `re.search` (deterministic_parser.py).

The **frontend** miner (`domain/template-mining/rules.js` `compileRuleFromTemplate`)
produces a different model:

- `pattern` is a **normalized template string** (e.g. `"<SIDE> <INSTRUMENT>\nEntry <PRICE>"`),
  not a regex.
- `fields` values are **semantic detector names** (`detected_instrument`,
  `price_after_entry_label`), not regex groups.
- Matching is by template subsumption + confidence threshold + reject phrases
  (`applyAcceptedRules`), plus dictionary/overlay-driven instrument & direction
  detection (`extract.js`, `instruments.js`, `directions.js`). No regex.

So the browser recognises signals by **semantic detection over a grouped
template**; the backend recognises them by **regex named-group capture**. There
is no 1:1 field map between them.

## What a faithful translator must do

Convert each accepted template into a backend `ParserRule` by walking the
normalized skeleton (`template.js` placeholders: `<INSTRUMENT>`, `<SIDE>`,
`<SIDE_EMOJI>`, `<PRICE>`, `<PRICE_LIST>`, `<RANGE>`, `<LEVERAGE>`, `TP<N>`, and
literal label words), emitting:

- `<INSTRUMENT>` → `(?P<symbol>…)` — needs the instrument vocabulary + overlay
  aliases to avoid over/under-matching.
- `<SIDE>` / `<SIDE_EMOJI>` → `(?P<side>…)` + `side_aliases` (incl. overlay
  direction tokens and emoji).
- `<PRICE>`/`<RANGE>`/`<PRICE_LIST>` → `entry` / `entry_low`+`entry_high` /
  `stop_loss` / `take_profit` groups, disambiguated by the **preceding literal
  label** the template preserves (`Entry`/`SL`/`TP…`).
- literal words → escaped literals; `<*>` → `.*?`.
- `FilterRule.include_patterns` from the accepted templates (recall-first),
  `exclude_patterns` from `REJECT_PHRASES` + `overlay.rejectPhrases`.

## Verification bar (why it can't be rushed)

The translated regexes must extract the **same** signals the browser miner shows
in the audit, across real provider formats (Cyrillic tickers, `#BTC`/`$ETH`,
emoji sides, TP ladders, ranges). Ship it only with a round-trip test:
mined-audit-parsed set == backend-`rematerialize`-extracted set on the demo feed
and a couple of real captures. Until then the backend keeps extracting via the
existing rules + LLM fallback, so nothing regresses.

## Frontend wiring (ready once the translator exists)

- `domain/template-mining/rules.js`: `toMiningRulesPayload(acceptedGroups, overlay)`
  (pure, the translator above).
- `shared/api/miningApi.js`: `confirmMiningRules(token, feedId, payload)` → POST.
- `ProductApp`: Verify "Confirm & continue" / "Confirm & keep verified" call it,
  show loading, toast the pipeline stats on success then `routeAfterVerify()` /
  `stopAfterVerify()` + `refreshSources()` (server now owns `verified`); on
  failure keep Verify mounted. `TemplateMiningPage` already accepts
  controlled decisions to clear on success.
