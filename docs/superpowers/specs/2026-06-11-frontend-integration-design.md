# Frontend Integration: Prototype → Production

**Date:** 2026-06-11
**Branch:** `feature/source-labeling-reader`
**Scope:** Integrate `claude_design/Verasig/` prototype + `claude_design/Verasig Design System/` into `apps/frontend/`

---

## 1. Goal

Replace the placeholder `apps/frontend/src/App.jsx` with the full Verasig prototype — including auth screens — converted from CDN/global pattern to proper Vite + React 18 ES modules. No compatibility shims, no residual CDN globals, no dead files.

---

## 2. Source Inventory

| Source | Pattern | Destination |
|--------|---------|-------------|
| `claude_design/Verasig Design System/components/` | `import React from 'react'` + named exports | `src/design-system/components/` (copy as-is) |
| `claude_design/Verasig Design System/tokens/` | Plain CSS | `src/design-system/tokens/` (copy as-is) |
| `claude_design/Verasig Design System/styles.css` | CSS entry point | `src/design-system/styles.css` |
| `claude_design/Verasig/icons.jsx` | `window.Icon = Icon` | `src/design-system/icons/Icon.jsx` (named export) |
| `claude_design/Verasig/Shell.jsx` | `window.Shell = Shell` | `src/layout/Shell.jsx` (named export) |
| `claude_design/Verasig/auth.jsx` | `window.AuthPage = AuthPage` | `src/features/auth/{LoginView,RegisterView,BrandPanel}.jsx` + `auth.css` |
| `claude_design/Verasig/App.jsx` | `window.App = App` | `src/App.jsx` (default export) |
| `claude_design/Verasig/data.jsx` | `window.VRS_DATA = {...}` | `src/data/seed.js` (named exports) |
| `claude_design/Verasig/Pipeline.jsx` | `window.PIPELINE_STEPS`, `window.Pipeline` | `src/features/pipeline/Pipeline.jsx` (named exports) |
| `claude_design/Verasig/*View.jsx` (10 files) | `window.XView = XView` | `src/features/{feature}/` (named exports) |
| `claude_design/Verasig/app.css` | Global layout styles | `src/app.css` |
| `claude_design/Verasig/execution.css` | ExecutionView-specific styles | `src/features/pipeline/steps/execution.css` |
| `claude_design/Verasig/auth.css` | Auth-specific styles | `src/features/auth/auth.css` |
| `claude_design/Verasig/assets/verasig-mark.svg` | Brand mark | `src/assets/verasig-mark.svg` |

### Not migrated

- `claude_design/Verasig/tweaks-panel.jsx` — prototype-only dev tool, dropped
- `claude_design/Verasig/design-canvas.jsx` — design artifact, not a production view
- `claude_design/Verasig/marketing.jsx` + `marketing.css` — separate product, not part of app
- `claude_design/Verasig/_ds/` — the IIFE bundle; replaced by direct DS source
- `claude_design/Verasig/docs/` — design documentation, not production code

---

## 3. Target File Structure

```
apps/frontend/src/
├── design-system/
│   ├── components/
│   │   ├── core/            # Button, IconButton, Badge, Tag, Avatar, Tabs
│   │   ├── data/            # Card, MetricStat, ConfidenceBar, StatusPill, SignalRow
│   │   ├── feedback/        # Banner, Tooltip, Dialog, Toast, ToastStack
│   │   └── forms/           # Input, Select, Checkbox, Switch
│   ├── icons/
│   │   └── Icon.jsx         # single named export: export function Icon({name, size, fill, style})
│   ├── tokens/              # fonts.css colors.css typography.css spacing.css effects.css base.css
│   ├── styles.css           # DS entry: @import tokens/*
│   └── index.js             # barrel: re-exports all 20 components + Icon
├── layout/
│   └── Shell.jsx            # UserMenu + Shell components
├── features/
│   ├── auth/
│   │   ├── BrandPanel.jsx
│   │   ├── LoginView.jsx
│   │   ├── RegisterView.jsx
│   │   └── auth.css
│   ├── sources/
│   │   ├── SourcesView.jsx
│   │   ├── TelegramSetup.jsx
│   │   └── ChatsView.jsx
│   ├── pipeline/
│   │   ├── Pipeline.jsx     # stepper bar + PIPELINE_STEPS constant
│   │   └── steps/
│   │       ├── BackfillView.jsx
│   │       ├── LabelView.jsx
│   │       ├── DistillView.jsx
│   │       ├── VerifyView.jsx
│   │       ├── ExchangeView.jsx
│   │       ├── ExecutionView.jsx
│   │       ├── BacktestView.jsx
│   │       └── execution.css
│   ├── signals/
│   │   └── SignalsView.jsx
│   ├── exchanges/
│   │   └── ExchangesView.jsx
│   └── settings/
│       └── SettingsView.jsx
├── data/
│   └── seed.js              # export const CHATS, MESSAGES, SIGNALS, SOURCES, ... (no window.*)
├── assets/
│   └── verasig-mark.svg
├── app.css                  # app layout styles (from prototype app.css)
├── App.jsx                  # state machine router, default export
└── main.jsx                 # ReactDOM.createRoot + import DS styles
```

---

## 4. Conversion Rules

### 4a. Global → ESM

Every prototype file ends with `window.X = X`. The conversion rule is:

| Before | After |
|--------|-------|
| `function Foo(...) { ... }` at top level | `export function Foo(...) { ... }` |
| `window.Foo = Foo` | Remove |
| `const { A, B } = window.VerasigDesignSystem_fd565b` | `import { A, B } from '../design-system/index.js'` |
| `window.VRS_DATA.CHATS` | `import { CHATS } from '../data/seed.js'` |
| `window.Icon` | `import { Icon } from '../design-system/icons/Icon.jsx'` |
| `window.PIPELINE_STEPS` | `import { PIPELINE_STEPS } from '../features/pipeline/Pipeline.jsx'` |
| `window.Shell` | `import { Shell } from '../layout/Shell.jsx'` |
| `const { useState } = React` | `import { useState } from 'react'` |

### 4b. data.jsx → seed.js

Replace `window.VRS_DATA = { CHATS, MESSAGES, ... }` with individual named exports:

```js
export const CHATS = [...]
export const MESSAGES = [...]
export const DISTILLED_RULES = [...]
// ... etc
```

### 4c. auth.jsx split

The prototype has one `AuthPage` component that takes `mode` prop. Split into:

- `LoginView.jsx` — renders `<AuthPage mode="login" />` or inlines the login form directly
- `RegisterView.jsx` — renders `<AuthPage mode="register" />` or inlines the register form directly
- `BrandPanel.jsx` — the shared left panel, used by both

Auth routing: `App.jsx` gets a new `authScreen` state: `'login' | 'register' | null`. When null, the user is "authenticated" and the main shell renders. Auth views render full-screen (no Shell wrapper).

### 4d. App.jsx tweaks

Remove:
- `useTweaks` + `TweaksPanel` + `TweakSection` + `TweakRadio` + `TweakButton` calls (prototype dev tool)
- `TWEAK_DEFAULTS` constant
- `window.App = App` global registration

Adjust:
- All `window.VRS_DATA.*` → named imports from `../data/seed.js`
- All DS destructuring → named imports from `../design-system/index.js`
- All view references → named imports from their respective feature files

### 4e. main.jsx

```jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import '../src/design-system/styles.css'
import '../src/app.css'
import App from './App.jsx'

ReactDOM.createRoot(document.getElementById('root')).render(<App />)
```

And `index.html` needs `data-theme="dark"` on `<html>`.

### 4f. design-system/index.js barrel

```js
export { Button, IconButton, Badge, Tag, Avatar, Tabs } from './components/core/...'
export { Card, MetricStat, ConfidenceBar, StatusPill, SignalRow } from './components/data/...'
export { Banner, Tooltip, Dialog, Toast, ToastStack } from './components/feedback/...'
export { Input, Select, Checkbox, Switch } from './components/forms/...'
export { Icon } from './icons/Icon.jsx'
```

---

## 5. No New Dependencies

The existing `package.json` already has everything needed:
- `react` + `react-dom` — React 18
- `vite` + `@vitejs/plugin-react` — build
- `vitest` + `@testing-library/react` — tests

DS components use self-contained injected CSS (no CSS modules, no styled-components). No additional packages required.

---

## 6. CSS Strategy

| File | Scope | Location |
|------|-------|----------|
| DS token files | Global design tokens | `design-system/tokens/` |
| `design-system/styles.css` | DS component styles entry | `design-system/styles.css` |
| `app.css` | App shell layout (`.vrs-shell`, `.vrs-sb`, `.vrs-main`, etc.) | `src/app.css` |
| `auth.css` | Auth page layout only | `features/auth/auth.css` |
| `execution.css` | ExecutionView-specific styles only | `features/pipeline/steps/execution.css` |
| DS component CSS | Injected by each component via `document.createElement('style')` | Self-contained in each `Component.jsx` |

---

## 7. Auth Flow

```
App renders auth first:
  authScreen === 'login'    → <LoginView onRegister={() => setAuthScreen('register')} onLogin={() => setAuthScreen(null)} />
  authScreen === 'register' → <RegisterView onLogin={() => setAuthScreen('login')} onRegister={() => setAuthScreen(null)} />
  authScreen === null       → <Shell ...>{/* main app */}</Shell>
```

Default `authScreen` is `'login'` (user starts unauthenticated). In the prototype the auth pages were separate HTML files linked via `window.location.href` — replace with state transitions.

---

## 8. Testing Strategy

Tests live in `apps/frontend/src/__tests__/`. Using vitest + @testing-library/react.

Priority tests (in order):
1. `App.test.jsx` — state machine: auth transitions, nav transitions, workflow screen sequence
2. `features/auth/LoginView.test.jsx` — form submit triggers `onLogin`
3. `features/pipeline/Pipeline.test.jsx` — stepper renders correct active step
4. `design-system/index.test.js` — all exports present, no missing components

---

## 9. Implementation Order

1. Copy DS source (tokens + components) → `src/design-system/`
2. Create `design-system/index.js` barrel
3. Convert `icons.jsx` → `design-system/icons/Icon.jsx`
4. Convert `data.jsx` → `data/seed.js`
5. Convert `Shell.jsx` → `layout/Shell.jsx`
6. Convert `Pipeline.jsx` → `features/pipeline/Pipeline.jsx`
7. Convert all `*View.jsx` files → their feature folders (10 files)
8. Split `auth.jsx` → `features/auth/{LoginView,RegisterView,BrandPanel}.jsx`
9. Convert `App.jsx` — wire all imports, add auth state, remove tweaks
10. Update `main.jsx` + `index.html`
11. Move CSS files to correct locations
12. Run `npm run build` — fix any import errors
13. Write tests
14. `npm run lint` — clean up

---

## 10. Out of Scope

- Backend API integration (no real auth, no real data — seed data only)
- Marketing page migration
- Design system token changes
- New features beyond what exists in the prototype
