# Label Sampling Recommendation

## Status

- Review recommendation.
- Written on 2026-06-15.
- Applies to the Telegram source labeling, distillation, and verification loop.

## Recommendation

| Decision | Recommended value |
|---|---:|
| Minimum labels before first distill | 30 |
| Minimum Signal labels | 10 |
| Minimum Non-signal labels from candidate rows | 10 |
| Minimum raw unflagged audit labels | 10 |
| Verification minimum | 20 verdicts |
| Verification preferred target | 30 verdicts |
| Verification pass rule | 0 wrong verdicts |
| Verification failure action | Label 12 more messages, redistill, reverify |

## Sampling Policy

| Sample group | Share | Purpose |
|---|---:|---|
| Recent history | 50% | Match the provider format most likely to be used next. |
| Middle history | 30% | Catch format changes inside the captured window. |
| Oldest history | 20% | Preserve coverage of older but still relevant formats. |

- Use the whole captured history.
- Sample by time strata.
- Prefer recent messages inside each label session.
- Include candidate rows for precision feedback.
- Include raw unflagged rows for filter-miss discovery.
- Do not ask the user to manually choose history ranges in V1.

## Reasoning

- Five Signal labels are enough for a prototype gate.
- Five Signal labels are not enough for durable provider-specific rules.
- A filter rule needs positive examples.
- A filter rule also needs negative examples.
- A recall-first filter needs unflagged raw-message audits.
- Recent-only sampling misses older provider formats.
- Equal thirds overweight stale provider formats.
- Pure random whole-history sampling is unbiased but less future-focused.
- Recency-weighted stratified sampling balances future relevance with historical coverage.
- Zero wrong verdicts keeps the pass rule easy to explain.
- More labels after failure give the distiller fresh counterexamples.

## Confidence Intuition

| Clean verification verdicts | Approximate unseen error ceiling |
|---:|---:|
| 6 | 39% |
| 20 | 15% |
| 30 | 10% |
| 60 | 5% |

- These are rough binomial zero-failure bounds.
- The product should show this as operational confidence, not statistical certainty.
- The `30` label minimum is a usability compromise.
- The `20` verdict minimum is a minimum ship gate.
- The `30` verdict target is the better default when the user has enough samples.

## Current Implementation Gap

| Area | Current behavior | Gap |
|---|---|---|
| Requirements | Distillation unlocks after 5 Signal labels. | Recommended gate is 30 total labels with class minimums. |
| Label sample | Samples only rows joined to `RawSignalEventRow`. | No raw unflagged audit sample. |
| Label order | Orders by `posted_at`, oldest first. | No random or stratified sample. |
| Verify sample | Samples only rows joined to `RawSignalEventRow`. | Cannot measure filter misses over raw history. |
| Verify minimum | Requires 6 verdicts. | Recommended minimum is 20 verdicts. |

References:

- `docs/work/source-labeling-reader/requirements.md`
- `docs/adr/0005-distilled-filter-and-advisory-gate.md`
- `apps/backend/src/verasig/features/rules/labeling.py`
- `apps/backend/src/verasig/features/rules/verification.py`

## Local LLM Stance

| Option | Recommendation |
|---|---|
| Deterministic rules only | Use as the production path for V1. |
| External LLM per message | Reject for V1. |
| FunctionGemma per new message in Lambda | Defer until measured drift justifies it. |
| FunctionGemma batch triage | Consider after the golden corpus is large enough to fine-tune. |
| Fine-tuned FilterGemma or ParserGemma | Consider only after measured recall and drift audits. |

- FunctionGemma is a small function-calling model based on Gemma 3 270M.
- FunctionGemma is designed for local edge use after task-specific tuning.
- Lambda can technically run small CPU inference.
- Lambda has a 15 minute timeout.
- Lambda has up to 10,240 MB memory.
- Lambda has up to 10,240 MB `/tmp` storage.
- Per-message Lambda inference is still risky because cold starts and model loading dominate small requests.
- The better future shape is SQS batch -> warmed Lambda or ECS worker -> local advisory triage.
- Deterministic rules remain the source of truth until local-model quality is measured.

External references:

- Google FunctionGemma announcement: https://blog.google/innovation-and-ai/technology/developers-tools/functiongemma/
- AWS Lambda quotas: https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html
- AWS Lambda timeout: https://docs.aws.amazon.com/lambda/latest/dg/configuration-timeout.html
- AWS Lambda ephemeral storage: https://docs.aws.amazon.com/lambda/latest/dg/configuration-ephemeral-storage.html

## User Stories

- As a user, I label a representative sample before distillation.
- As a user, I do not manually choose history ranges during V1 labeling.
- As a user, I see progress toward the minimum label set.
- As a user, I am asked for more labels only when coverage is insufficient.
- As a user, I verify an independent holdout sample before extraction.
- As an operator, I can measure filter misses from unflagged raw-message audits.
- As an operator, I can compare deterministic rules against later local-model triage.

## Review Questions

- Should the product hard-block distillation until all class minimums are met?
- Should the UI expose why raw unflagged messages appear in the label queue?
- Should verification use 20 as a hard minimum and 30 as a recommended target?
- Should failed verification always request 12 more labels?
- Should FunctionGemma be tested first in an offline batch benchmark?
