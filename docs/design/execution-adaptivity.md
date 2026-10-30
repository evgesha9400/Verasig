# Execution step — adaptive display logic

The step adapts to what the feed actually posts. Visual version: [`execution-adaptivity-decision-tree.html`](./execution-adaptivity-decision-tree.html).

## Principles

1. **Two layers.** The backfilled **corpus** decides what the step *shows* (once per feed). Each **signal** decides what the engine *does* (at execution time). Feeds are heterogeneous — 64% ranges and 36% single prices can coexist — so showing a control is a corpus decision, never a per-signal one.
2. **Three independent dimensions.** Entry shape (none / single / range) × target count (0 / 1 / many) × stop (present / absent) = 18 signal shapes, but the dimensions don't interact. Three small UI adapters; seven engine rules.
3. **The skeleton stays put.** §01/§02/§03 always render in order. A section with nothing to configure collapses to a one-line statement of fact — it never disappears.

## Display gates (corpus → UI)

### §01 Position size
Always rendered, always identical. No signal dependency.

### §02 Entry
- **No signal posts a range** → no controls; line: *"This feed posts single entry prices — orders are placed at the posted price."*
- **Any signal posts a range** → render First touch / Midpoint / Ladder + corpus stat (*"64% of signals post a range"*).
  - Mixed feed → add: *"Single-price signals fill at the posted price — this setting doesn't affect them."*
  - "Enter now" signals exist → add: *"Signals without a price fill at market."*

### §03 Exit
- **No signal posts any stop/target** → no source toggle; own-SL/TP config only ("no risk management detected" case).
- Otherwise render the source toggle. Under **Signal's stops & targets**, per-control gates:
  - **Missing-risk handling**: hidden if 100% of signals post both SL and ≥1 TP; otherwise shown with stat.
  - **Allocation + break-even**: hidden if no signal posts >1 target; line: *"Signals post a single target — the full position closes there."* When shown, break-even additionally hides under *TP1 only* (TP1 closes 100% — nothing left to protect).
  - **Follow author's updates**: always shown (updates exist regardless of shape).

## Engine matrix (signal → behavior)

| Dimension | Signal posts | Engine does |
|---|---|---|
| Entry | Range | Entry mode applies as configured |
| Entry | Single price | One limit order at the posted price (mode bypassed) |
| Entry | No price ("enter now") | Market fill on verification |
| Targets | Multiple | Allocation applies as configured |
| Targets | One | 100% closes there (allocation bypassed; break-even moot) |
| Targets | None | Missing-handling: fallback TP (anchored on avg fill) or skip |
| Stop | None | Missing-handling: fallback SL (anchored on avg fill) or skip |

### Worked combinations

- **Range · 1 TP · SL** — ladder applies; single target takes 100%; break-even moot.
- **Single price · 3 TPs · SL** — one fill at posted price; allocation + break-even apply.
- **Range · 3 TPs · no SL** — ladder + allocation apply; stop from fallback or signal skipped.
- **"Enter now" · 0 TPs · no SL** — market fill, everything from fallbacks — or skipped.

## Preview: where combinations live

No single sample signal demonstrates a config against a mixed feed. The plan preview should page through **2–3 representative signals from the backfill** (e.g. `Range · 3 TPs`, `Single · 1 TP`, `No stop`) via a chip switcher, each rendered through the live config — so users *see* the ladder collapse to one fill, one target take 100%, the fallback stop appear.

## Open questions (not yet ruled on)

- **Thresholds:** show range controls whenever range-count > 0 (even 2%), with the stat conveying rarity? (Proposed: yes.)
- **Hide vs. disable:** gates *hide* controls and leave a statement of fact. Disabling would advertise capabilities the feed can't use. (Proposed: hide.)
- **Corpus drift:** if a feed starts posting ranges after configuration, resurface entry controls on next visit (default: first touch) and possibly notify.

> Status: **specified, not yet implemented** — the live `ExecutionView.jsx` does not yet apply these gates or the preview switcher.
