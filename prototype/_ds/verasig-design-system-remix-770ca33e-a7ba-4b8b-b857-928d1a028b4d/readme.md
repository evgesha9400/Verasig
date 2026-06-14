# Verasig Design System

**Verasig** is a SaaS platform for **signal verification** — it sits between signal _providers_ and the systems that act on their data, cross-checking every inbound signal across independent sources, scoring it for confidence, and **verifying, holding, or rejecting** it before it reaches production. Signals arrive from many providers over many channels (Webhook, REST, gRPC, WebSocket); Verasig is the trust layer that makes them safe to act on.

This repository **is** the Verasig design system: brand foundations, design tokens, reusable React components, and high-fidelity UI-kit recreations of the two core products.

> **Tagline:** _Trust every signal._

---

## Sources & provenance

- **Brand brief:** Verasig — "a SaaS platform for signal verification from different signal providers via different channels." Dark theme primary, light supported. Must be user-friendly and non-generic.
- **Visual inspiration (provided):** [seda.xyz](https://www.seda.xyz/) — a programmable-oracle infrastructure site. We borrowed its _posture_ (dark, technical, data-feed-forward, confident-but-quiet, mono numerics, product-tile grids, provider marquee, big restrained display type) — **not** its colors or marks. Verasig is its own identity.
- **No codebase or Figma was attached.** This is a **from-scratch brand**. Everything here is original. If a real Verasig codebase or Figma exists, re-attach it and we will reconcile.

### ⚠️ Open items / substitutions to confirm

- **Fonts load from Google Fonts CDN** (`tokens/fonts.css`) rather than self-hosted binaries — the build environment can't fetch font files. For offline use / shipping, replace the `@import`s with local `@font-face` + `.woff2` files. Fonts chosen: **Space Grotesk** (display), **Geist** (UI/body), **Geist Mono** (data). Swap any of these if you have licensed brand fonts.
- **Logo** is an original mark designed here (a "verified-signal" trace ending in a node). Replace if you have an official logo.
- **Provider names** in the marketing kit are illustrative; provider **logos** were not fabricated — they're shown as mono wordmark chips. Drop real logos into `assets/` to upgrade.

---

## Content fundamentals (voice & tone)

Verasig speaks like a **precise instrument**, not a hype machine. The reader is a developer, a risk owner, or an ops engineer who needs to trust what they ship.

- **Direct & concrete.** Lead with the fact and the number. _"Verified in 182 ms across 12 sources."_ — never _"blazing-fast, next-gen verification."_
- **Second person, active voice.** "You" and "we." _"Tell us what you're verifying."_ / _"We'll bring it to production."_
- **Quietly confident.** State capability plainly; let the metrics carry the weight. No exclamation points, no superlatives stacked on superlatives.
- **Technical, not jargon-soaked.** Use the domain vocabulary the audience already owns — _quorum, source, channel, confidence, tolerance, provenance, latency, spoofed, quarantined_ — but don't invent buzzwords.
- **Casing:** Sentence case for almost everything (headings, buttons, labels). `MONO UPPERCASE` _only_ for eyebrows/overlines and tiny metric labels, always wide-tracked. Title Case is avoided.
- **Numbers are first-class.** Always set metrics, IDs, latencies, and percentages in the **mono** typeface with tabular figures. _182 ms_, _99.4%_, _SIG-7F2A·0x9d4e_, _12 / 12_.
- **No emoji.** Not in product, not in marketing. The status _language_ is carried by color + a small set of icons.
- **Status words are consistent:** **Verified · Pending · Rejected · Observing** (and _Awaiting quorum_, _Spoofed_, _Quarantined_ as specific sub-states).

**Say:** "Holding SIG-7F2A until at least 8 sources respond." · "One integration. Every channel." · "Reject anything that fails quorum — automatically."
**Don't say:** "Revolutionary AI-powered synergy." · "Unlock the power of your data journey!" · "🚀 Game-changing trust, reimagined."

---

## Visual foundations

The Verasig aesthetic is **"oscilloscope at night"** — a deep cool-ink canvas, a single electric **signal-lime** trace, crisp mechanical geometry, and mono numerics everywhere data appears.

### Color

- **Dark is primary.** The canvas is a cool near-black **Ink** ramp (`--ink-950` app bg `#0A0C0F` → layered surfaces `--ink-850/800/750`). Surfaces step _up_ in lightness as they come forward; depth comes from layered surfaces + hairline borders, not heavy shadows.
- **One brand accent: Signal** — a chartreuse "live trace" (`--signal-500 #B9EE2E`). Used sparingly but boldly: primary buttons (dark text on lime), the brand mark, active nav rails, focus glows, and — meaningfully — the **Verified** state. Verification _is_ the positive action, so the brand color _is_ the success color.
- **Support:** **Azure** (`#5197FF`) for links/info and data-viz; a 6-hue categorical **viz ramp** for channels, providers, and charts.
- **Semantics:** Verified = signal-lime · Pending = amber `#F5B544` · Rejected = coral `#FB6A5E` · Info/Observing = azure. Each has a low-alpha `*-bg` tint.
- **Light theme** is fully supported (`[data-theme="light"]`): cool-paper surfaces, darkened accent (`--signal-600`) for legibility, the same semantic logic.

### Type

- **Space Grotesk** — display & headlines. Geometric grotesque, tracked tight (`-0.02 to -0.035em`), big and restrained. Carries the "signal" character.
- **Geist** — all UI and body. Neutral, modern, legible at small sizes.
- **Geist Mono** — every number, ID, latency, metric, code snippet, and eyebrow. Tabular figures (`tnum`). This is the system's signature: _if it's data, it's mono._
- Minimum 24px on slide-scale surfaces; UI body sits at 14–15px.

### Space, radius, shadow

- **4px base grid** (`--space-*`).
- **Crisp, mechanical corners:** controls `8px`, cards `12px`, panels `16px`, pills `999px`. Never pill-shaped buttons; never over-rounded cards.
- **Restrained elevation:** deep, low-spread shadows for true overlays (dialogs, drawers, toasts); inline cards rely on a 1px border + a one-step surface lift, _not_ drop shadows. The one expressive effect is the **signal glow** (`--glow-signal` / `--glow-soft`) reserved for live/active/verified states.

### Surfaces, borders, backgrounds

- **Cards:** `--surface-card` fill, `1px` `--border-default` hairline, `--radius-lg`. Hover → border brightens + optional `--shadow-md`. No accent-only left-border cards (an over-used trope we avoid).
- **Backgrounds:** mostly flat ink. Two signature textures, used only on heroes / section headers / empty states: the **`v-lattice`** signal grid (32px hairline grid) and the **ink glow field** (soft radial signal-lime + azure washes). No photographic imagery by default; no busy gradients.
- **Transparency & blur:** sticky headers and modal scrims use `backdrop-filter` blur (`--blur-md`/`--blur-sm`) over a semi-transparent ink — the "frosted instrument panel" feel.

### Motion

- **Quick, precise, no bounce** — like an instrument snapping to a reading. `--ease-out`/`--ease-snap`, durations 80–360ms.
- **Hover** = surface/border brighten or subtle glow; **press** = a tiny `scale(0.992)` + translateY. Pending/live states get a soft **pulse ring**. Decorative infinite loops are avoided except the providers marquee.
- Respect `prefers-reduced-motion`.

---

## Iconography

- **Line icons, ~1.7–2.0px stroke, round caps/joins**, on a 24px grid — matching Geist's geometry. Icons are monochrome and inherit `currentColor`; they never carry their own fill color except status glyphs (which take the semantic tone).
- **No icon binary set is bundled.** The components and kits draw a small, purpose-built inline-SVG set in the house style (nav, search, bell, refresh, check, alert, arrows, the status glyphs, the product/why icons). For broader coverage, the recommended CDN match is **[Lucide](https://lucide.dev)** (same stroke weight & round-join style) — link it from CDN and it will sit seamlessly beside the built-ins. _(Substitution flagged: Lucide is a stand-in for a future bespoke set.)_
- **No emoji. No unicode-glyph icons** (✓, →) used as UI icons — use the SVGs. The only "glyph" exceptions are the mono `×` close affordance and `+`/`−` deltas in text.
- **The mark** (`assets/verasig-mark.svg`) is the one piece of true brand iconography: a verified-signal trace + node, in `currentColor` (use `--signal-500` on dark, `--signal-600` on light). A fixed-color variant is in `assets/verasig-mark-signal.svg`.

---

## Index / manifest

### Root

- **`styles.css`** — the single entry point consumers link. `@import`s only.
- **`readme.md`** — this guide.
- **`SKILL.md`** — Agent-Skill front-matter so this system can be used standalone in Claude Code.

### `tokens/` — design tokens (all reached from `styles.css`)

- `fonts.css` · `colors.css` (dark `:root` + `[data-theme="light"]`) · `typography.css` · `spacing.css` · `effects.css` (radius/shadow/motion/blur) · `base.css` (reset + `.v-eyebrow`, `.v-mono`, `.v-lattice`, `.v-grain` helpers).

### `assets/`

- `verasig-mark.svg` (currentColor) · `verasig-mark-signal.svg` (fixed lime) · `logo.card.html` (lockup specimen).

### `guidelines/` — Design System tab specimen cards

- Colors: signal scale, ink scale, semantic status, surfaces, data-viz ramp, light theme.
- Type: display, body/UI, mono, eyebrow.
- Spacing: scale, radius, elevation, motion.
- Brand: voice & tone, signal motifs.

### `components/` — reusable primitives (React; namespace `window.VerasigDesignSystem_*`)

- **core/** — `Button`, `IconButton`, `Badge`, `Tag`, `Avatar`, `Tabs`
- **forms/** — `Input`, `Select`, `Checkbox`, `Switch`
- **feedback/** — `Banner`, `Tooltip`, `Dialog`, `Toast` (+ `ToastStack`)
- **data/** — `Card`, `MetricStat`, `ConfidenceBar`, `StatusPill`, `SignalRow` _(the domain core)_
- Each directory ships `<Name>.jsx` + `<Name>.d.ts` + `<Name>.prompt.md` and one `@dsCard` demo HTML.

### `ui_kits/` — high-fidelity product recreations

- **app/** — the **Verasig Console**: sidebar + topbar shell, Overview dashboard (metrics, live feed, provider health), Signals table (filters + status tabs), Signal detail **drawer** (quorum, source breakdown, timeline), Providers, plus reject **Dialog** + **Toast**. Interactive click-through. Entry: `ui_kits/app/index.html`.
- **marketing/** — the **Verasig marketing home**: sticky nav, hero with live verification panel, provider marquee, product grid, stats band, "why" grid, CTA, footer. Entry: `ui_kits/marketing/index.html`.

> UI kits load the compiled `_ds_bundle.js` and read components from `window.VerasigDesignSystem_*`. The bundle is generated automatically by the design-system compiler.
