---
name: verasig-design
description: Use this skill to generate well-branded interfaces and assets for Verasig, either for production or throwaway prototypes/mocks/etc. Contains essential design guidelines, colors, type, fonts, assets, and UI kit components for prototyping.
user-invocable: true
---

Read the README.md file within this skill, and explore the other available files.

If creating visual artifacts (slides, mocks, throwaway prototypes, etc), copy assets out and create static HTML files for the user to view. If working on production code, you can copy assets and read the rules here to become an expert in designing with this brand.

If the user invokes this skill without any other guidance, ask them what they want to build or design, ask some questions, and act as an expert designer who outputs HTML artifacts _or_ production code, depending on the need.

## Quick map
- `readme.md` — the full design guide: brand context, voice & tone, visual foundations, iconography, manifest. **Start here.**
- `styles.css` — link this one file to inherit every token, font, and base style. Dark is `:root`; add `data-theme="light"` on `<html>` for light mode.
- `tokens/` — colors, typography, spacing, effects (radius/shadow/motion), fonts, base helpers.
- `guidelines/` — specimen cards for colors, type, spacing, brand.
- `components/` — React primitives (core / forms / feedback / data). Each has a `.jsx`, a `.d.ts` props contract, and a `.prompt.md` usage note.
- `ui_kits/app/` & `ui_kits/marketing/` — full-screen recreations to copy patterns from.
- `assets/` — the Verasig mark (SVG).

## House rules (the short version)
- **Dark-first.** Cool-ink canvas, one electric **signal-lime** accent (`--signal-500`), used sparingly.
- **If it's data, it's mono.** Numbers, IDs, latencies, metrics → Geist Mono, tabular.
- **Voice:** direct, second-person, quietly confident, sentence case, no emoji, numbers first.
- **Verified = the brand color.** Semantic: verified=lime, pending=amber, rejected=coral, info=azure.
- **Crisp corners, hairline borders, restrained shadows;** the one flourish is the signal glow on live/verified states.
- Status vocabulary: **Verified · Pending · Rejected · Observing.**

## Using components outside this project
Components reference CSS custom properties only — link `styles.css` and they're styled. In HTML artifacts, load React + Babel, then the compiled `_ds_bundle.js`, and read components from `window.VerasigDesignSystem_*` (see any `components/**/*.card.html` for the exact pattern and namespace).
