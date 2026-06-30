# Template-Mining — pattern-precedence matching (specificity-first)

- Date: 2026-06-30
- Branch: `feature/parser-first-template-mining`
- Status: **spec for review — no implementation yet**
- Related: display-ordering already shipped (`feat: order audit results most-likely-first`)

## 1 · Why

Today, applying accepted templates over a feed is **exact-key routing**: each
message normalizes to exactly one `templateKey` (`template.js:343`), and
`applyAcceptedRules` looks that key up in a `Map` (`rules.js:199`). A message
belongs to exactly one family, so **no two templates compete for it** and
"apply the most-likely template first" has no effect.

We want templates to **compete**: a message a specific family doesn't claim
should be recoverable by a more general accepted family. Once they compete,
order decides the winner — and that is the feature the user asked for.

## 2 · Goal

- Accepted templates apply as **overlapping patterns**, not exact keys.
- A message is claimed by the **most-specific** matching rule; general templates
  act as fallbacks that **recover messages that today fall to "rare."**
- Deterministic, inspectable, no LLM. Review semantics unchanged.

## 3 · Current architecture (facts)

| Fact | Location |
|---|---|
| `normalizeTemplate` → `{ templateKey: tpl_<hash(skeleton)>, normalizedTemplate }` | `template.js:331-344` |
| Skeleton tokens: `<INSTRUMENT> <PRICE> <PRICE_LIST> <RANGE> <SIDE> <SIDE_EMOJI> <LEVERAGE> TP<N>`, structural words, and `<*>` | `template.js:138-204` |
| `<*>` = one stray (non-structural) word per line; runs collapse to a single `<*>` | `template.js:290-305` |
| Families discovered by bucketing on exact `templateKey` | `mining.js:24-32` |
| Audit routes each candidate by exact key; unmatched → "rare" | `rules.js:165-180,199` |

Key insight: `<*>` **already** encodes "any single foreign word here," so
subsumption between skeletons is well-defined and tractable.

## 4 · Proposed model

### 4.1 Subsumption (does rule pattern P match message skeleton S?)

- Align **line-by-line**, then **token-by-token** within a line.
- A non-`<*>` token in P must **equal** the token in S.
- A `<*>` in P matches **exactly one** token in S (mirrors how `<*>` is
  generated — at most one stray word, runs already collapsed).
- A placeholder in P matches the same placeholder in S **or any placeholder it
  subsumes** per the hierarchy in §4.1a (decision: generalization is in scope).
- Exact equality (`P === S`) is the special, maximal case (today's behaviour).

### 4.1a Placeholder subsumption hierarchy (decided: generalize)

A more-general placeholder in the **rule** matches a more-specific one in the
**message**:

| General (rule) | Subsumes (message) | Rationale |
|---|---|---|
| `<PRICE_LIST>` | `<PRICE>` | a list of one price is still a list |
| `<SIDE>` | `<SIDE_EMOJI>` | an emoji side is a weaker spelling of a side |
| `<*>` | any single word | existing stray-word wildcard |

- Subsumption is **one-directional**: a `<PRICE>` rule does NOT match a
  `<PRICE_LIST>` message (specific rule, general message → no claim).
- Generalizing always **lowers** specificity (§4.2), so the exact family still
  wins over a generalizing fallback — consistent with specificity-first.
- **Remaining sub-decision:** `<RANGE> ⊇ <PRICE>`? A range is an entry *zone*,
  semantically distinct from a single level. **Proposed: keep distinct in v1**
  (flagged in §8).

### 4.2 Specificity score (higher = more specific = wins)

```
specificity(P) = (# structural words) + (# value placeholders) − w·(# <*>)
```

- Literal structural words (`BUY`, `МОНЕТА`, …) are the strongest signal.
- `<*>` wildcards reduce specificity (general templates score low).
- `w` tuned so any `<*>` template loses to its `<*>`-free counterpart.

### 4.3 Precedence order (first match wins)

```
specificity ↓  →  confidenceAvg ↓  →  coverage(count) ↓  →  templateKey (stable)
```

- **Specificity first** prevents greedy capture: a broad `<SIDE> <PRICE>` family
  cannot steal a message that the specific `МОНЕТА <INSTRUMENT> …` family owns.
- Coverage is only a **tie-breaker** — this is the deliberate departure from the
  user's "coverage-first" instinct (confirmed via the "Both" decision).

## 5 · Data-model changes

`compileRuleFromTemplate` (`rules.js:100`) additionally carries:

| Field | Source |
|---|---|
| `pattern` | `group.normalizedTemplate` (the skeleton) |
| `specificity` | computed per §4.2 |
| `coverage` | `group.count` |
| `confidenceAvg` | `group.confidenceAvg` |

`ParserRule` type (`types.js`) updated to match.

## 6 · Algorithm change (`applyAcceptedRules`)

- Precompute `orderedRules = rules.sort(precedence)` (§4.3) **once**.
- For each candidate:
  1. **Fast path:** exact `templateKey` hit → that rule (it is the most specific
     by construction).
  2. **Fallback:** else, first `orderedRules` entry whose `pattern` subsumes the
     candidate's `normalizedTemplate`.
  3. else → "rare" (unchanged).
- Threshold + reject-phrase checks unchanged (`rules.js:171-179`).
- Tag each parsed signal `match: 'exact' | 'fallback'` + `parserRuleId`. The
  audit keeps fallback matches in the **Parsed** bucket with a `fallback` **badge**
  on the row (decided §8.5) — one bucket, provenance visible.

Blast radius: contained to `rules.js` + `types.js`. `mineTemplateGroups` and
review UI semantics are untouched — families are still discovered by exact key.

## 7 · Risks & mitigations

| Risk | Mitigation |
|---|---|
| Greedy capture by general templates | Specificity-first ordering (§4.3) |
| Ambiguous ties → non-determinism | Total order ends in stable `templateKey` |
| Performance: N messages × M rules subsumption | Exact-key fast path skips most; M = accepted rules (small); short-circuit on first line mismatch |
| Fallback inflates false positives | Per-rule `confidenceThreshold` still gates; fallback matches flagged for review; optional stricter fallback threshold (§8) |
| Reviewer confusion (why did X parse?) | Audit row shows claiming rule + `exact/fallback` badge |

## 8 · Decisions

| # | Decision | Status |
|---|---|---|
| 8.2 | Placeholder generalization: `<PRICE_LIST>⊇<PRICE>`, `<SIDE>⊇<SIDE_EMOJI>` | ✅ **yes** (§4.1a) |
| 8.5 | Fallback matches → badge on the **Parsed** row, no extra bucket | ✅ **decided** (§6) |
| 8.1 | `<*>` arity: exactly-one token vs zero-or-more | proposed: **exactly-one** |
| 8.3 | Fallback confidence: reuse rule threshold vs stricter bar | proposed: **reuse** |
| 8.4 | Specificity weight `w`; does `<SIDE_EMOJI>` count as half a placeholder | open (tune in impl) |
| 8.6 | `<RANGE> ⊇ <PRICE>` in the hierarchy | proposed: **keep distinct** in v1 |

## 9 · Testing strategy (TDD)

- **Specific beats general:** message matching both a specific and a general
  accepted rule is claimed by the specific one.
- **Fallback recovery:** a near-miss message that exactly matches no accepted
  family is captured by a general accepted family (was "rare").
- **Greedy-capture guard:** a high-coverage general family does NOT steal a
  specific family's messages.
- **Placeholder generalization:** a `<PRICE_LIST>` rule captures a `<PRICE>`
  message; a `<SIDE>` rule captures a `<SIDE_EMOJI>` message; the reverse does
  NOT match; `<RANGE>` and `<PRICE>` stay distinct.
- **Fallback badge:** a fallback-captured signal renders in Parsed tagged
  `fallback`; an exact one is not.
- **Determinism:** identical input → identical assignment across runs.
- **No regression:** with no overlapping patterns, output equals today's
  exact-key result (golden test over `realFeedMessages` / sample).
- **Specificity scoring:** unit tests over representative skeletons.

## 10 · Rollout

- Pure domain change behind the same `applyAcceptedRules` signature.
- Land specificity scorer + subsumption matcher as standalone, unit-tested
  modules first; wire into `applyAcceptedRules` last.
- Golden no-regression test gates the wiring commit.
