# Verasig Console — App UI kit

A high-fidelity, click-through recreation of the **Verasig Console** — the operator-facing app for monitoring and acting on signal verification.

**Entry:** `index.html` (loads `../../styles.css`, `app.css`, and the compiled `_ds_bundle.js`).

### Screens & flow
- **Overview** — KPI metrics (`MetricStat` + sparklines), a **live verification feed** of recent `SignalRow`s, and a **provider health** panel (`StatusPill`).
- **Signals** — status tabs (`Tabs` with counts), channel filter chips (`Tag`), and a table of `SignalRow`s. Click a row → detail drawer.
- **Signal drawer** — quorum + `ConfidenceBar`, per-source breakdown, and a verification timeline. *Reject* opens a confirm `Dialog`; confirming fires a `Toast`.
- **Providers** — connected sources table with health + uptime.
- *Channels / Settings* are stubbed empty states.

### Files
`app.data.jsx` (fake data) · `Sidebar.jsx` · `Topbar.jsx` · `OverviewView.jsx` · `SignalsView.jsx` · `SignalDrawer.jsx` · `ProvidersView.jsx` · `App.jsx` (shell + state) · `app.css` (kit layout only — primitives bring their own styles).

### Composition
The kit **composes** design-system primitives (`Button`, `IconButton`, `Tabs`, `Tag`, `Avatar`, `Card`, `MetricStat`, `StatusPill`, `ConfidenceBar`, `SignalRow`, `Dialog`, `Toast`, `Tooltip`) — it does not re-implement them. Kit-specific CSS is namespaced `vrs-`.
