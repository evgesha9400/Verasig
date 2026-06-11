# The Execution step

Configures how each verified signal from a feed becomes orders on the exchange (Bybit in the prototype). Replaces the old "Risk management" step.

## The model: three lifecycle sections, in order

| § | Section | What it owns | Source of truth |
|---|---|---|---|
| 01 | **Position size** | Risk per trade (%), max leverage | Always the user — signal authors never decide account exposure |
| 02 | **Entry** | How a posted entry range becomes orders: First touch / Midpoint / Ladder (levels, equal or martingale weighting) | User strategy applied to the signal's range |
| 03 | **Exit** | Where stops & targets come from: the signal's, or the user's own fixed SL/TP | Scoped choice — this is the *only* place "signal vs. own" is meaningful |

### Why this structure (decisions log)

- **"Risk" → "Execution":** the step configures sizing + entry + exit; only sizing is risk management proper. Entry-range handling is execution; TP allocation is trade management. Naming it Risk conflated all three.
- **Sizing was trapped inside "configure my own risk" mode** in the old design — but you need position sizing even when trusting the signal's stops. It's now always visible (§01).
- **The old global radio "use signal's risk vs. my own" really only governed exits.** It's now a segmented toggle inside §03.
- **Entry-before-exit ordering** matches how traders think through a trade; the old page configured exits first and buried entries at the bottom.
- **Dropdowns → segmented toggles** for two-option choices (missing-risk handling, exit source).
- Layout: **"Numbered flow"** — one card, sections connected by a vertical numbered rail (chosen over stacked cards and ledger rows; see `Execution Step Explorations.html`).

## §03 Exit — controls

When **Signal's stops & targets** is selected:

- **Missing-risk handling** (segmented): *Apply a fallback* (fallback SL % + TP %) or *Skip the signal*. Shown with the corpus stat ("8% of signals omit a stop or target").
- **Allocation across multiple targets** (segmented): *Equal split* (34/33/33) / *Front-heavy* (50/30/20) / *TP1 only* (100/0/0).
- **Follow the author's updates** (switch): partial closes, stop moves, early exits posted as replies override the plan. Relative updates resolve against **your fills**, not the author's entry (see `execution-engine-rules.md`).
- **Move stop to break-even after TP1** (switch): after the first target fills, SL moves to average entry.
  - When both switches are on, an info note states the conflict resolution: **the tighter stop wins** (ratchet rule).

When **My own stop & target** is selected: fixed SL % / TP % anchored on average fill; posted stops, targets and author updates are ignored. Entry handling (§02) still applies.

## The plan preview

A sticky aside rendering the current config against a real sample signal from the feed.

- **Order:** position header (side, symbol, id) → **Size** row → the **price ladder** → stats (avg entry, entry → SL).
- **The ladder is a chart, not a list.** Vertical position = price, descending — TPs above entry, SL below (inverts naturally for shorts). It is deliberately *not* in config-section order; it shows the trade's risk/reward geometry.
- **Section ties:** hovering a config section highlights its rungs (Entry → entry zone; Exit → TPs + SL; Size → size row) and fades the rest.
- **Signal facts persist; user constructs adapt.** Targets the user allocates 0% to stay visible but dimmed (the signal posted them; the user is deliberately ignoring them). Ladder levels that don't exist under "First touch" simply aren't rendered (they were never part of the signal — the posted range stays visible as the entry zone).

## Tweaks

- **Choice style:** Segmented (default) ↔ Radio cards, app-wide tweak for the two-option controls.

## Files

- `ExecutionView.jsx` — component (`layout`: `cards` | `flow` | `ledger`; `controls`: `segmented` | `radio`)
- `execution.css` — `vx-*` styles
- Wired in `App.jsx` (screen id `risk`), pipeline label in `Pipeline.jsx`
