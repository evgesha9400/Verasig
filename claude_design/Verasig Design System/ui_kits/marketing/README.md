# Verasig Marketing — site UI kit

A high-fidelity recreation of the **Verasig marketing home page**. SEDA-inspired structure (dark, data-forward, product-tile grid, provider marquee) rendered in the Verasig identity.

**Entry:** `index.html` (loads `../../styles.css`, `site.css`, and the compiled `_ds_bundle.js`).

### Sections
- **Nav** — sticky, frosted, with `Button` CTA.
- **Hero** — eyebrow, big Space-Grotesk headline, sub, dual CTA, meta stats, and a live **verification panel** (trace + `StatusPill` + `ConfidenceBar`) on the right.
- **Marquee** — scrolling provider wordmark chips (`#providers`).
- **Products** — 4-tile grid (`#products`): Verify · Quorum · Channels · Provenance, each with a headline stat.
- **Stats band** — four mono KPIs.
- **Why Verasig** — 4 icon features (`#why`).
- **CTA** — lattice + glow closing call.
- **Footer** — brand, link columns, legal bar.

### Files
`site.data.jsx` · `Nav.jsx` · `Hero.jsx` · `Products.jsx` (Products + Stats + Marquee) · `Why.jsx` (Why + CTA + Footer) · `Site.jsx` (composition) · `site.css`.

### Notes
Provider **logos** are intentionally shown as mono wordmark chips rather than fabricated marks — drop real logos into `/assets` and swap the `.mk-chip` content to upgrade. All section CSS is namespaced `mk-`.
