# Interaction system — buttons, surfaces & hover language

The rules for *which* control to use, *how* it looks, and *how* it reacts to hover.
Source of truth for `apps/frontend/design-system` (`Button`, `IconButton`, `Card`/`InteractiveCard`)
and for any hand-rolled affordance in `apps/frontend/web`.

## The one principle

**Lime is the primary, deliberate, forward action. Grey is surface, utility, or navigation.**

Two corollaries make it enforceable:

1. **No double emphasis.** A container and the action inside it must never both claim lime. A navigable card hovers grey; the lime belongs to a real button, not to decorative text.
2. **No false affordance.** Nothing shows an interactive (hover) state unless it is interactive, and the whole click target is exactly the thing that reacts.

## Emphasis ladder

One **primary** per view. Everything else steps down from it.

| Tier | Component | Display | Hover | Use for |
|---|---|---|---|---|
| **Primary** | `Button variant="primary"` | lime fill, dark ink text | brighter lime + glow | The single most important forward action: Configure, Connect, Add feed, Backtest, Continue, Link, Connect & verify |
| **Secondary** | `Button variant="secondary"` | grey raised fill, white text, grey border | **lime** border + glow | Strong-but-not-primary action, or the main action on a low-stakes view: Go to sources, Start backfill |
| **Ghost** | `Button variant="ghost"` | transparent, grey text | grey `--surface-hover` fill | Dismissive / utility text actions: Cancel, Dismiss, Stay here, View deleted signals, **Back** |
| **Danger** | `Button variant="danger"` | transparent, red text + red-tint border | red fill + red glow | Destructive / irreversible: Disconnect, Delete & restart |
| **Icon-utility** | `IconButton variant="ghost"` (default) | transparent, grey icon | grey `--surface-hover` fill | Repeatable toolbar / row utility: Refresh, row Options (⚙) |
| **Icon-strong** | `IconButton variant="solid"` | grey raised fill, grey border | **lime** border | Icon action that needs to read as a discrete control, not a hint |
| **Icon-accent** | `IconButton variant="accent"` | lime tint + lime ring | lime glow | *Reserved.* Icon action that must draw the eye. Use sparingly; never more than one per view |

**Focus is always lime, on every tier.** `:focus-visible` draws `--focus-ring` + `--signal-glow` regardless of hover tier. Focus signals keyboard position (accessibility); hover signals emphasis. They are different channels and must not be merged.

## Interaction-surface rules (cards & rows)

A card or row is exactly one of these. Pick the type, then the rules are fixed.

| Surface type | Component | Hover | Click target | Rule |
|---|---|---|---|---|
| **Navigable** — opens a detail view | `InteractiveCard` / row `<button>` | grey `--border-strong` + shadow (**never lime**) | **the whole surface** | Canonical. No primary `Button` inside. The forward hint is **muted text** (`--text-muted`) with an arrow that nudges on surface hover. Inner badges/popovers call `stopPropagation`. |
| **Action** — hosts a CTA | plain `.vrs-src-card` / `Card` (no `is-clickable`) | **none on the surface** | the inner `Button` | The surface is a static container. The lime primary button is the only affordance. Never add `is-clickable`. |
| **Selectable** — choose one option | `InteractiveCard selected` / `RadioCard` | grey on hover, **lime border when selected** | the whole surface | Selection state owns the lime (`--accent` border + glow); hover stays grey. |

### Canonical navigable surface

The whole card/row is the button. The "Open →" is a muted hint, not a control.

```
┌─────────────────────────────┐
│ ⬢ Telegram      ● Connected │   whole card is the click target
│ 12 feeds · 4 analyzed       │   hover: grey border + shadow (no lime)
│ 👥 mara@…          Open  →   │   "Open →" = --text-muted, arrow nudges on hover
└─────────────────────────────┘
```

## Hover language — the decision

| You want hover to say… | Use | Reads as |
|---|---|---|
| "this performs the primary action" | lime (primary / secondary / accent) | a deliberate commit |
| "this is a utility or a way out" | grey fill (ghost) | low-stakes, reversible |
| "this whole surface navigates" | grey border + shadow | a place to go, not an action |
| "this is selected" | lime border | current choice |
| nothing | no hover | not interactive — and it must not be |

## Conformance map

State of every audited surface after the consistency sweep. ✅ = conforms to the rules above.

| Page | Element | Rule | Status |
|---|---|---|---|
| Exchanges | Configure | Primary | ✅ |
| Exchanges | Disconnect | Danger | ✅ |
| Exchanges | Connected card | Action surface (no `is-clickable`) | ✅ removed dead clickable + CSS |
| Sources | Connect | Primary | ✅ |
| Sources | Connected card | Navigable (whole card) | ✅ |
| Sources | "Open →" | Navigable hint = muted text + hover arrow | ✅ recolored to `--text-muted` |
| Signals | Go to sources | Secondary | ✅ |
| Signals | Signal rows | Navigable (whole-row `<button>` + chevron) | ✅ |
| Feeds | Feed rows | Action rows (no row `onClick`) | ✅ buttons kept; `analyzed` got an explicit Results button |
| Telegram setup | Resend code / Change number | Link-styled `<button>` (`.vrs-link`) | ✅ converted from clickable spans |
| Settings | Save / Resend / Cancel / plan CTAs | Primary / secondary / ghost / danger | ✅ |
| Pipeline | step buttons, swipe controls, choices | Button / IconButton / Radio / Interactive cards | ✅ |
| Marketing | Sign up / Log in CTAs | Primary + secondary | ✅ |
| Auth | Log in / Create account | Primary (submit) + lime link (switch) | ✅ `.auth-link` now styled |
| Topbar | Back | Ghost button + chevron | ✅ replaced `.vrs-crumb` |
| Topbar | Refresh | Icon-utility | ✅ |

## Anti-patterns (banned)

1. **Dead hover.** A surface with `is-clickable` / hover styling but no handler. If it lifts on hover, it must do something.
2. **Lime pseudo-button.** Lime-colored text or icon that looks like a primary action but is decorative or non-interactive. Lime is reserved for real `primary` / `secondary` / `accent` controls.
3. **Double click target.** A navigable row/card that also contains a competing primary button. Choose one model from the surface table.
4. **Hand-rolled buttons.** New `<button>` with bespoke styling when a `Button` / `IconButton` variant fits. Extend the design system instead.
5. **Two primaries on one view.** If two actions both shout lime, one of them is secondary.
