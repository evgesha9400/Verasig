# Parser rules come from human-assisted distillation, not autonomous mining

Deterministic `ParserRule`s are produced by a human-in-the-loop distillation loop: the operator highlights signal messages in the UI, an LLM distills declarative rules from those examples, the rules are applied and matched messages filtered out, and the residue is re-presented until the operator is satisfied. The operator's labels become the golden corpus. This replaces `requirements.md`'s original "agent mines message history and distills parser rules" (autonomous).

We did this to honour the explicit no-auto-research scope while still avoiding pure hand-coding of regexes: the human supplies ground truth and judgement, the LLM does the tedious pattern induction, and the result is auditable declarative config. A reader expecting an autonomous miner (per the old requirements) needs to know the autonomy was deliberately removed.

## Consequences

- The UI (Streamlit) is a first-class interactive workbench, not a read-only report.
- Parser precision/recall is measurable against the human golden corpus from day one.
- Autonomous rule generation remains out of scope unless validation data justifies it.

## Amendment (ADR 0005)

The same loop now distils the **candidate filter** as well, not just the parser. Per [ADR 0005](0005-distilled-filter-and-advisory-gate.md): one `GoldenLabel` pass feeds both a distilled `FilterRule` (from `is_signal`) and `ParserRule`s (from `expected` fields) in a single workbench cycle (classify `is_signal` first, then fill fields for positives). The filter-distillation prompt is deliberately **recall-first** (loose, OR-joined include rules), unlike the precision-first parser prompt. A cheap hand-coded heuristic remains only as a cold-start seed; filter misses surface as `FilterDriftWarning`, symmetric to `ParserDriftWarning`.
