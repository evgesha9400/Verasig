# Parser rules come from human-assisted distillation, not autonomous mining

Deterministic `ParserRule`s are produced by a human-in-the-loop distillation loop: the operator labels signal messages, an LLM distills declarative rules from those examples, and the operator's labels become the golden corpus. This replaces `requirements.md`'s original "agent mines message history and distills parser rules" (autonomous).

We did this to honour the explicit no-auto-research scope while still avoiding pure hand-coding of regexes: the human supplies ground truth and judgement, the LLM does the tedious pattern induction, and the result is auditable declarative config. A reader expecting an autonomous miner (per the old requirements) needs to know the autonomy was deliberately removed.

## Consequences

- The operator review UI is intentionally not implemented in the current codebase; framework and workflow are TBD.
- Parser precision/recall is measurable against the human golden corpus from day one.
- Autonomous rule generation remains out of scope unless validation data justifies it.

## Amendment (ADR 0005)

The same loop now distils the **candidate filter** as well, not just the parser. Per [ADR 0005](0005-distilled-filter-and-advisory-gate.md): one `GoldenLabel` pass feeds both a distilled `FilterRule` (from `is_signal`) and `ParserRule`s (from `expected` fields). The filter-distillation prompt is deliberately **recall-first** (loose, OR-joined include rules), unlike the precision-first parser prompt. A cheap hand-coded heuristic remains only as a cold-start seed; filter misses surface as `FilterDriftWarning`, symmetric to `ParserDriftWarning`.
