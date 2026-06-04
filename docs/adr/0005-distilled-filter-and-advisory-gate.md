# Filter rules are distilled too, and the candidate gate is advisory, not hard

The candidate filter stops being a hard gate of hand-coded heuristics. Two changes: (1) candidate flagging becomes **advisory** — it sets queue priority and decides what the expensive LLM and the operator UI see, but it is **not** eligibility; deterministic rules may run over **all** captured messages. (2) The filter's rules are produced by the **same** human-assisted LLM distillation loop that produces parser rules — one `GoldenLabel` pass yields a distilled `FilterRule` (from `is_signal`) and `ParserRule`s (from `expected` fields). A cheap hand-coded heuristic survives only as a **cold-start seed**. Filter false negatives surface as `FilterDriftWarning` (a background deterministic parse, the operator, or the LLM finds a signal the filter missed) — symmetric to `ParserDriftWarning`.

We did this because a hard keyword gate silently drops real signals that nothing downstream can recover, and hand-coded multilingual keyword lists are brittle to provider slang. Distilling the filter from operator labels makes it provider-specific, deterministic, auditable, and unit-testable behind a Protocol, while keeping bulk channel content off the external LLM — only operator-selected examples are ever sent (privacy, spec §10). Two independent model consultations (Gemini `gemini-3.1-pro-preview`, Codex `gpt-5.5`) converged on this design after an earlier pair converged on capture-all + cheap-triage + deterministic-distilled-parser + local-LLM-residue + external-LLM-for-distillation-only.

## Considered options

- **Keep the hard gate** (only candidates parsed/shown): rejected — unrecoverable silent false negatives; a vocabulary shift the dictionary misses is dropped at Layer 1 and never warns, never reaches fallback, never appears in the UI.
- **Drop the gate entirely** (parse every message): rejected — the distillation UI drowns in chatter and there is no triage to bound the expensive LLM.
- **Live LLM classifier over every message**: rejected — per-message cost/latency, and it sends bulk channel content to the model (§10). Rule-distillation gives the same recall benefit while keeping bulk content local.
- **Reuse `ParserRule` for filtering**: rejected — filtering decides *inclusion* (recall-first), parsing *maps fields* (precision-first); distinct objectives and prompts. They share a regex engine internally but are separate entities.

## Consequences

- **Supersedes the hard-gate framing in [ADR 0001](0001-two-layer-raw-capture.md).** `RawSignalEvent` becomes an *advisory* candidate and may be **late-materialized** (e.g. when a background parse or audit finds a missed signal). The extraction-metric denominator moves off the candidate subset to `GoldenLabel`: filter **recall** is measured on `is_signal`, parser **precision/recall** on `expected` fields.
- **Extends [ADR 0002](0002-human-assisted-rule-distillation.md).** Distillation now yields `FilterRule`s in addition to `ParserRule`s, from one unified workbench loop (classify `is_signal` first, then fill expected fields for positives).
- **New contracts:** `FilterRule`, `FilterDriftWarning`; redefined `RawSignalEvent` provenance (`materialized_by` + `matched_reasons` + optional `filter_rule_id`).
- **Cold start:** the hand-coded seed heuristic bootstraps the first candidates; the operator also samples random *unflagged* raw messages to discover missed formats. No one-off zero-shot LLM pass over channel history.
- **Biggest risk:** rule distillation tends to tighten toward *precision*, but the filter must be *recall-first*. Mitigated by (a) a recall-first filter-distillation prompt that demands loose, OR-joined, high-recall rules, (b) `FilterDriftWarning` feedback, (c) random unflagged audits.
- **Plan:** the former Slice 3 (candidate filter) and Slice 4 (distillation loop) merge into one slice — candidate seed filter + unified distillation producing `FilterRule` + `ParserRule` + golden corpus; subsequent slices renumber down by one.
- **Scale:** declarative rules are the Stage-0 target; a fine-tuned local `FilterGemma`/`ParserGemma` (trained on the same golden corpus) and a possible hard gate are deferred to a later stage, justified only after measured recall + drift audits.
