# Naming & structure conventions

The house style, so new code reads like old code. Where this doc and a local
pattern disagree, the local pattern wins for that area — but update this doc.

## Files & folders

| Kind | Convention | Example |
|------|-----------|---------|
| Folders (all) | kebab-case | `template-mining/`, `parser_overlay/` (backend snake) |
| Frontend components | PascalCase `.jsx` | `TemplateMiningPage.jsx` |
| Frontend logic modules | camelCase `.js` | `feedMessages.js` |
| Frontend styles | kebab-case `.css` | `template-mining.css` |
| Frontend tests | colocated `.test.jsx` sibling | `AuditReview.test.jsx` |
| Backend modules | snake_case `.py`, name discloses purity | `deterministic_parser.py` (pure), `extract_service.py` (IO), `feed_repository.py` (data) — [ADR 0010](adr/0010-refine-codebase-structure-without-new-application-layer.md) |

## CSS classes

Plain CSS over design tokens only (no Sass, no CSS-in-JS). One `vrs-` prefix per
feature, BEM-lite (`block__element`, `.is-modifier`). Self-injecting CSS is
allowed **only** inside the design system; app features ship a colocated `.css`.

**Prefix registry** (one feature ↔ one prefix, no bare non-`vrs` prefixes):

| Prefix | Owns |
|--------|------|
| `vrs-` | shell + design-system primitives |
| `vrs-tm-` | template mining |
| `vrs-bf-` | backfill screen |
| `vrs-feed-` | feed list (was `vrs-chat-`; "chat" is retired — see CONTEXT.md) |
| `vrs-ex-` | execution step (was `vx-`) |

## Design-system additions

A new component ships four files + the barrel export: `Name.jsx`, `Name.d.ts`,
`Name.prompt.md`, `Name.test.jsx`, and an entry in `design-system/index.js`.
Tokens are CSS custom properties in `design-system/tokens/*.css` — no JS token
objects.

## Vocabulary

`docs/context/CONTEXT.md` is canonical and overrides everything here on wording:
**feed** not chat, **Templates** not "template families" in UI copy, **Mining
confirm** not verify/distill. Retired words must not reappear on the wire or in
new class prefixes.

## Backend

snake_case modules and feature folders; `CamelModel` wire schemas expose
camelCase JSON (`alias_generator=to_camel`, `populate_by_name`). Rules persist
through `features/rules/repository.py` regardless of producer (Mining or the
legacy distillation loop).
