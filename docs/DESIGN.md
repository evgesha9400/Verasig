---
name: Verasig
description: Proof-first signal provider intelligence.
colors:
  bg: "oklch(1.000 0.000 0)"
  surface: "oklch(0.972 0.006 250)"
  surface-raised: "oklch(0.985 0.004 250)"
  sidebar: "oklch(0.150 0.010 250)"
  sidebar-muted: "oklch(0.620 0.030 250)"
  border: "oklch(0.875 0.010 250)"
  border-strong: "oklch(0.720 0.018 250)"
  ink: "oklch(0.180 0.018 250)"
  muted: "oklch(0.430 0.020 250)"
  primary: "oklch(0.540 0.145 330)"
  primary-deep: "oklch(0.430 0.130 330)"
  accent: "oklch(0.880 0.105 86)"
  success: "oklch(0.560 0.125 150)"
  success-soft: "oklch(0.940 0.040 150)"
  warning: "oklch(0.820 0.130 82)"
  warning-soft: "oklch(0.955 0.040 82)"
  danger: "oklch(0.560 0.160 28)"
  danger-soft: "oklch(0.950 0.040 28)"
  info: "oklch(0.570 0.120 245)"
  info-soft: "oklch(0.945 0.035 245)"
typography:
  display:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "2rem"
    fontWeight: 650
    lineHeight: 1.15
    letterSpacing: "0"
  headline:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 650
    lineHeight: 1.2
    letterSpacing: "0"
  title:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 620
    lineHeight: 1.35
    letterSpacing: "0"
  body:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: "0"
  label:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "0"
  mono:
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
    fontSize: "0.8125rem"
    fontWeight: 500
    lineHeight: 1.45
    letterSpacing: "0"
rounded:
  xs: "4px"
  sm: "6px"
  md: "8px"
  lg: "12px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  xxl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.bg}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "8px 12px"
  button-secondary:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "8px 12px"
  input-default:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.sm}"
    padding: "8px 10px"
  card-evidence:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "16px"
  chip-warning:
    backgroundColor: "{colors.warning-soft}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.xs}"
    padding: "3px 7px"
---

<!-- SEED -->

# Design System: Verasig

## 1. Overview

**Creative North Star: "Ledger Console"**

Ledger Console is a restrained product interface for reviewing evidence. It should feel like a clean audit ledger with enough density for scorecards, parser traces, raw messages, deleted-signal evidence, and simulated outcomes to sit on one screen without visual noise.

The default surface is light because users compare rows, read explanations, and inspect provenance. A dark sidebar can anchor navigation, but the content area stays bright, quiet, and legible. The rose primary color comes from the brand seed and is used sparingly for focus, selection, and primary action. Green, amber, red, and blue are reserved for measured states.

This system rejects hype-driven trading bot visuals, exchange casino energy, black-box score cards, and decorative chrome that competes with evidence.

**Key Characteristics:**

- Dense information without cramped text.
- Restrained color with state-rich semantics.
- Flat surfaces with structural borders.
- Clear provenance markers.
- Familiar product controls.

## 2. Colors

The palette is pure white and cool neutral by default, with rose identity used rarely and evidence colors used only when they encode state.

### Primary

- **Ledger Rose** (`oklch(0.540 0.145 330)`): Primary action, selected navigation, focused controls, and one active chart series. Use on less than 8 percent of any screen.
- **Deep Ledger Rose** (`oklch(0.430 0.130 330)`): Pressed primary state, focused text links on light surfaces, and compact active markers.

### Secondary

- **Evidence Amber** (`oklch(0.880 0.105 86)`): Pending, caution, incomplete evidence, and review-needed states. Prefer the soft token for backgrounds.
- **Signal Green** (`oklch(0.560 0.125 150)`): Positive simulated outcome, passed checks, and parser coverage success.

### Tertiary

- **Risk Red** (`oklch(0.560 0.160 28)`): Deletion evidence, failed checks, broken parser output, and high-risk warnings.
- **Trace Blue** (`oklch(0.570 0.120 245)`): Links, informational notices, trace references, and neutral drill-down actions.

### Neutral

- **White Ledger** (`oklch(1.000 0.000 0)`): Main content background.
- **Cool Panel** (`oklch(0.972 0.006 250)`): Page bands, table headers, and secondary panels.
- **Raised White** (`oklch(0.985 0.004 250)`): Cards and grouped evidence surfaces.
- **Ink** (`oklch(0.180 0.018 250)`): Body text and data values.
- **Muted Ink** (`oklch(0.430 0.020 250)`): Secondary metadata, timestamps, and helper text.
- **Rule Gray** (`oklch(0.875 0.010 250)`): Dividers, table row boundaries, input borders.
- **Strong Rule Gray** (`oklch(0.720 0.018 250)`): Active borders, resizable panel handles, and selected row outlines.
- **Night Sidebar** (`oklch(0.150 0.010 250)`): Primary app navigation and operator context.

### Named Rules

**The Evidence Color Rule.** Green, amber, red, and blue appear only when they encode measured state, warning, risk, or traceability.

**The Rose Scarcity Rule.** Ledger Rose is identity, not decoration. It marks the current action or selected object.

## 3. Typography

**Display Font:** Inter, with system sans fallback.
**Body Font:** Inter, with system sans fallback.
**Label/Mono Font:** ui-monospace for message ids, hashes, symbols, timestamps, and raw numeric traces.

**Character:** The type system is familiar, compact, and readable. It avoids display styling because Verasig users are comparing evidence, not reading a campaign page.

### Hierarchy

- **Display** (650, 2rem, 1.15): Page titles and major dashboard views only.
- **Headline** (650, 1.5rem, 1.2): Section headers, scorecard titles, and provider profile headings.
- **Title** (620, 1rem, 1.35): Card headings, table group labels, and fieldset names.
- **Body** (400, 0.9375rem, 1.55): Explanations, empty states, and normal prose with a 65 to 75 character line cap.
- **Label** (600, 0.8125rem, 1.3): Buttons, table headers, tabs, filters, field labels, and compact status text.
- **Mono** (500, 0.8125rem, 1.45): Raw Telegram ids, provider refs, symbols, R-multiples, timestamps, and trace ids.

### Named Rules

**The Data First Rule.** Numbers, ids, and trace references use mono; prose and controls use Inter.

**The No Fluid Type Rule.** Product UI uses fixed rem steps. Tables and panels should not resize type with viewport width.

## 4. Elevation

Verasig is flat by default. Depth is conveyed with tonal layers, borders, and state changes. Shadows are reserved for transient overlays such as menus, popovers, and command palettes.

### Shadow Vocabulary

- **Overlay Low** (`0 8px 24px color-mix(in oklch, oklch(0.180 0.018 250) 12%, transparent)`): Menus, floating filters, date pickers, and command suggestions.
- **Overlay High** (`0 16px 40px color-mix(in oklch, oklch(0.180 0.018 250) 18%, transparent)`): Dialogs and command palettes only.

### Named Rules

**The Flat By Default Rule.** Cards, tables, and score panels use borders and tonal backgrounds at rest.

**The Overlay Only Rule.** Shadows do not decorate static cards.

## 5. Components

### Buttons

- **Shape:** Compact rectangle with a 6px radius.
- **Primary:** Ledger Rose fill, white text, 8px 12px padding, label typography.
- **Hover / Focus:** Deep Rose hover, visible 2px focus ring, 180ms state transition.
- **Secondary:** Raised White background, Rule Gray border, Ink text.
- **Ghost:** Transparent background, Ink text, subtle Cool Panel hover.

### Chips

- **Style:** Soft state background, strong readable text, 4px radius, compact padding.
- **State:** Success, warning, danger, and info chips must map to measured evidence states.
- **Selection:** Selected filters use Ledger Rose text and a full border, not a colored side stripe.

### Cards / Containers

- **Corner Style:** 8px for evidence cards, 12px only for large empty states.
- **Background:** Raised White on White Ledger or Cool Panel.
- **Shadow Strategy:** No static card shadows.
- **Border:** Rule Gray at rest; Strong Rule Gray for selected or focused containers.
- **Internal Padding:** 16px default, 24px for large summary panels.

### Inputs / Fields

- **Style:** White background, Rule Gray border, 6px radius, 8px 10px padding.
- **Focus:** Ledger Rose border plus a 2px outside focus ring.
- **Error / Disabled:** Risk Red for errors; Cool Panel background and Muted Ink for disabled.

### Navigation

- **Style:** Night Sidebar with compact labels, mono hints for operational counters, and 8px row radius.
- **Default:** Sidebar Muted text with transparent background.
- **Hover:** Slightly lighter sidebar tonal fill.
- **Active:** Ledger Rose-tinted background plus high-contrast text.
- **Mobile:** Collapse to a top bar with a drawer; preserve active view and command access.

### Score Evidence Table

- **Style:** Dense rows, fixed header, mono numeric cells, and row separators instead of card rows.
- **State:** Warnings and deletion evidence use chips in cells, not row-wide color fills.
- **Drill-down:** Row click opens an inline evidence drawer before using a modal.

## 6. Do's and Don'ts

### Do:

- **Do** use White Ledger as the default content background.
- **Do** reserve Ledger Rose for primary action, selection, and focus.
- **Do** use Signal Green, Evidence Amber, Risk Red, and Trace Blue only for measured states.
- **Do** keep score inputs traceable to raw evidence, parser output, simulation, or deletion records.
- **Do** use mono text for ids, symbols, timestamps, R-multiples, and trace references.
- **Do** preserve WCAG AA contrast for every label, chip, table cell, and placeholder.
- **Do** show loading with skeleton rows in tables and panels.

### Don't:

- **Don't** look like a hype-driven trading bot, exchange casino, or profit-promise funnel.
- **Don't** imply guaranteed returns, investment advice, or autonomous live execution.
- **Don't** hide score inputs behind black-box summaries.
- **Don't** treat subscribers, views, forwards, or reactions as quality claims without labeling them as proxies.
- **Don't** use decorative dashboard chrome that competes with evidence, tables, traces, and audit trails.
- **Don't** use gradient text, glass cards, thick side-stripe borders, or card shadows on static panels.
- **Don't** use color as the only meaning for profit, loss, warning, confidence, or deletion evidence.
