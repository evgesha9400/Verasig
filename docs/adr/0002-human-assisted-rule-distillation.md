# Parser rules come from human-assisted distillation, not autonomous mining

Deterministic `ParserRule`s are produced by a human-in-the-loop distillation loop: the operator highlights signal messages in the UI, an LLM distills declarative rules from those examples, the rules are applied and matched messages filtered out, and the residue is re-presented until the operator is satisfied. The operator's labels become the golden corpus. This replaces `requirements.md`'s original "agent mines message history and distills parser rules" (autonomous).

We did this to honour the explicit no-auto-research scope while still avoiding pure hand-coding of regexes: the human supplies ground truth and judgement, the LLM does the tedious pattern induction, and the result is auditable declarative config. A reader expecting an autonomous miner (per the old requirements) needs to know the autonomy was deliberately removed for Stage 0.

## Consequences

- The UI (Streamlit) is a first-class interactive workbench, not a read-only report.
- Parser precision/recall is measurable against the human golden corpus from day one.
- Autonomous rule generation remains a possible later stage, gated behind validation data.
