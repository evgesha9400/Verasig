# Template-Mining page — UI polish (spacing, symmetry, design)

- Date: 2026-06-30
- Branch: `feature/parser-first-template-mining`
- Scope (approved): spacing + design polish. **No card-anatomy rewrite.**

## Goal

Make the mining page consistent, symmetrical, correctly spaced, and properly
designed — without restructuring content, components, or behaviour.

## Problems (evidence)

| # | Area | Issue |
|---|------|-------|
| 1 | Symmetry | Cards in a row have ragged, unequal heights (`align-items:start`) |
| 2 | Symmetry | Action buttons sit at different baselines across a row |
| 3 | Spacing | Body gaps mix `6/8/10/12/14/16px`, not tokenized |
| 4 | Spacing | Inline styles: `gap:16`, `marginTop:6`, `flex/minWidth` |
| 5 | Spacing | `min-height:132px` textarea — off the 4px grid |
| 6 | Layout | Source panel: sparse header→content + bottom dead space |
| 7 | Layout | Empty-state panels carry heavy dead padding |
| 8 | Hierarchy | Card action row: 1 primary + 2–3 ghost buttons wrap/compete |
| 9 | Hierarchy | Stats (count + confidence) baselines slightly off |

## Design

### 1 · Spacing rhythm (tokenize to the 4px grid)

| Context | Now | → Token |
|---|---|---|
| Card body gap | `14` | `--space-4` (16) |
| Metrics + families grid gap | `14/16` | `--space-4` (16) |
| Stats / legend / actions | `8/10/12` | `--space-2` / `--space-3` |
| Warn / issues tight gaps | `6` | `--space-1-5` (6) |
| Textarea min-height | `132` | `128` (8rem) |
| Section gap, inline `gap:16` | inline | `--space-5` via class |

### 2 · Symmetry — equal-height cards (stretch to tallest)

- Families grid → `align-items: stretch`.
- Card `.vrs-card__pad` → flex column; `.vrs-tm-actions` gets `margin-top:auto`
  to pin to a shared bottom baseline. Actions stay in the body; expansion still
  renders below. (Only structural touch; within "no anatomy rewrite".)

### 3 · Design polish

- Action row: `Accept` (primary) left; `Reject`/`Reset`/`Show all` grouped right,
  no wrap-competition.
- Stats block: count value + confidence bar share one baseline.
- Badges: normalized min-width so suggestion chips read as equal.
- Metric cards: tighten value→caption hierarchy, consistent padding.
- Empty states (Compiled rules, Review, page): unify on dashed `.vrs-empty--sm`.
- Source panel: tighten header→content, remove bottom dead space.

## Verification

- Existing tests stay green (`make test`); behavioural, not CSS-coupled.
- Live Playwright screenshots before/after at 1280 / 940 / 520px.
- `npm run format` + `lint` before commit.
