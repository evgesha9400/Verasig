# Frontend Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate the Verasig prototype from `claude_design/Verasig/` into `apps/frontend/src/`, converting every CDN/global-pattern file to proper Vite + React 18 ES modules.

**Architecture:** The prototype uses CDN React + Babel standalone + `window.*` globals. We copy the Design System source directly into `src/design-system/`, barrel-export all components via `index.js`, then convert each view file from `window.X = X` registrations to named ES module exports. The state machine router lives in `App.jsx`; auth is a new top-level state (`authScreen`).

**Tech Stack:** Vite 6, React 18, vitest 3, @testing-library/react 16, jsdom 26

---

## Conversion Rules (apply to every file)

| Before | After |
|--------|-------|
| `const { useState } = React` | `import { useState } from 'react'` |
| `const { A, B } = window.VerasigDesignSystem_fd565b` | `import { A, B } from '<rel>/design-system/index.js'` |
| `const ADS = window.VerasigDesignSystem_fd565b` | `import * as ADS from '<rel>/design-system/index.js'` |
| `window.VRS_DATA.X` or `const { X } = window.VRS_DATA` | `import { X } from '<rel>/data/seed.js'` |
| `window.Icon` | already imported via design-system/index.js |
| `window.PIPELINE_STEPS` | `import { PIPELINE_STEPS } from '<rel>/features/pipeline/Pipeline.jsx'` |
| `window.Shell` | `import { Shell } from '<rel>/layout/Shell.jsx'` |
| `window.X = X` at bottom | remove |
| `React.Fragment` | `Fragment` (add to react import) |
| `React.useLayoutEffect` | `useLayoutEffect` (add to react import) |

`<rel>` = relative path from file location to `src/` (e.g. `../../` for files in `features/*/`).

**Never convert:** `window.addEventListener` / `window.removeEventListener` — these are real DOM API calls, not prototype globals.

---

## Task 1: Copy Design System Source

**Files:**
- Create: `apps/frontend/src/design-system/` (directory tree)

- [ ] **Step 1: Copy DS component source**

```bash
cd /Users/evgesha/Projects/trading/Verasig
cp -r "claude_design/Verasig Design System/components" apps/frontend/src/design-system/components
cp -r "claude_design/Verasig Design System/tokens" apps/frontend/src/design-system/tokens
cp "claude_design/Verasig Design System/styles.css" apps/frontend/src/design-system/styles.css
```

- [ ] **Step 2: Copy SVG asset**

```bash
cp "claude_design/Verasig Design System/assets/verasig-mark.svg" apps/frontend/src/assets/verasig-mark.svg
```

(Create `src/assets/` first: `mkdir -p apps/frontend/src/assets`)

- [ ] **Step 3: Verify copy**

```bash
find apps/frontend/src/design-system -name "*.jsx" | sort
```

Expected: 20 component files across `core/`, `data/`, `feedback/`, `forms/`.

- [ ] **Step 4: Commit**

```bash
git add apps/frontend/src/design-system apps/frontend/src/assets
git commit -m "feat(frontend): copy design system source into src/design-system"
```

---

## Task 2: Design System Barrel + Icon Component

**Files:**
- Create: `apps/frontend/src/design-system/index.js`
- Create: `apps/frontend/src/design-system/icons/Icon.jsx`

- [ ] **Step 1: Create the barrel**

Create `apps/frontend/src/design-system/index.js`:

```js
export { Avatar } from './components/core/Avatar.jsx'
export { Badge } from './components/core/Badge.jsx'
export { Button } from './components/core/Button.jsx'
export { IconButton } from './components/core/IconButton.jsx'
export { Tabs } from './components/core/Tabs.jsx'
export { Tag } from './components/core/Tag.jsx'
export { Card } from './components/data/Card.jsx'
export { ConfidenceBar } from './components/data/ConfidenceBar.jsx'
export { MetricStat } from './components/data/MetricStat.jsx'
export { SignalRow } from './components/data/SignalRow.jsx'
export { StatusPill } from './components/data/StatusPill.jsx'
export { Banner } from './components/feedback/Banner.jsx'
export { Dialog } from './components/feedback/Dialog.jsx'
export { Toast, ToastStack } from './components/feedback/Toast.jsx'
export { Tooltip } from './components/feedback/Tooltip.jsx'
export { Checkbox } from './components/forms/Checkbox.jsx'
export { Input } from './components/forms/Input.jsx'
export { Select } from './components/forms/Select.jsx'
export { Switch } from './components/forms/Switch.jsx'
export { Icon } from './icons/Icon.jsx'
```

- [ ] **Step 2: Create Icon component**

Create `apps/frontend/src/design-system/icons/Icon.jsx` — copy from `claude_design/Verasig/icons.jsx`, then apply conversion:

```bash
cp "claude_design/Verasig/icons.jsx" apps/frontend/src/design-system/icons/Icon.jsx
```

Open `src/design-system/icons/Icon.jsx` and make these edits:

1. Add at the top:
```jsx
import React from 'react'
```

2. Change the function declaration:
```jsx
// before:
function Icon({ name, size = 18, fill = false, style }) {

// after:
export function Icon({ name, size = 18, fill = false, style }) {
```

3. Remove the last line:
```jsx
// remove:
window.Icon = Icon;
```

- [ ] **Step 3: Write smoke test for barrel**

Create `apps/frontend/src/design-system/index.test.js`:

```js
import { describe, it, expect } from 'vitest'
import * as DS from './index.js'

describe('design-system barrel', () => {
  const expected = [
    'Avatar', 'Badge', 'Button', 'IconButton', 'Tabs', 'Tag',
    'Card', 'ConfidenceBar', 'MetricStat', 'SignalRow', 'StatusPill',
    'Banner', 'Dialog', 'Toast', 'ToastStack', 'Tooltip',
    'Checkbox', 'Input', 'Select', 'Switch',
    'Icon',
  ]
  it.each(expected)('exports %s', (name) => {
    expect(typeof DS[name]).toBe('function')
  })
})
```

- [ ] **Step 4: Configure vitest for jsdom**

Edit `apps/frontend/vite.config.js`:

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
  },
})
```

- [ ] **Step 5: Run the smoke test**

```bash
cd apps/frontend && npm test -- src/design-system/index.test.js
```

Expected: 21 passing tests.

- [ ] **Step 6: Commit**

```bash
git add apps/frontend/src/design-system/index.js apps/frontend/src/design-system/icons/Icon.jsx apps/frontend/src/design-system/index.test.js apps/frontend/vite.config.js
git commit -m "feat(frontend): add design-system barrel and Icon component"
```

---

## Task 3: Seed Data Module

**Files:**
- Create: `apps/frontend/src/data/seed.js`

- [ ] **Step 1: Copy data source**

```bash
mkdir -p apps/frontend/src/data
cp "claude_design/Verasig/data.jsx" apps/frontend/src/data/seed.js
```

- [ ] **Step 2: Convert to named exports**

Open `apps/frontend/src/data/seed.js` and make these edits:

1. Remove the first line `/* Verasig prototype — seed data ... */` comment header if present (optional, keep if useful).

2. Remove the `const { useState } = React` line if it exists (data file shouldn't use React, but check).

3. Replace the last line:
```js
// remove:
window.VRS_DATA = { CHATS, MESSAGES, DISTILLED_RULES, VERIFY_SAMPLES, VERIFY_MIN, VERIFY_MISCLASSIFIED, EXCHANGES, SIGNALS, SOURCES, MOD_KINDS, ORPHAN_MODS, ORPHAN_LINKED_MOD };

// add after each const declaration (add `export` keyword to each):
// Change every `const CHATS = [` to `export const CHATS = [`
// Change every `const MESSAGES = [` to `export const MESSAGES = [`
// ... and so on for all 12 constants
```

The 12 constants to export:
`CHATS`, `MESSAGES`, `DISTILLED_RULES`, `VERIFY_SAMPLES`, `VERIFY_MIN`, `VERIFY_MISCLASSIFIED`, `EXCHANGES`, `SIGNALS`, `SOURCES`, `MOD_KINDS`, `ORPHAN_MODS`, `ORPHAN_LINKED_MOD`

Use a targeted sed approach:
```bash
cd apps/frontend
# add export to each const declaration
sed -i '' 's/^const CHATS /export const CHATS /g' src/data/seed.js
sed -i '' 's/^const MESSAGES /export const MESSAGES /g' src/data/seed.js
sed -i '' 's/^const DISTILLED_RULES /export const DISTILLED_RULES /g' src/data/seed.js
sed -i '' 's/^const VERIFY_SAMPLES /export const VERIFY_SAMPLES /g' src/data/seed.js
sed -i '' 's/^const VERIFY_MIN /export const VERIFY_MIN /g' src/data/seed.js
sed -i '' 's/^const VERIFY_MISCLASSIFIED /export const VERIFY_MISCLASSIFIED /g' src/data/seed.js
sed -i '' 's/^const EXCHANGES /export const EXCHANGES /g' src/data/seed.js
sed -i '' 's/^const SIGNALS /export const SIGNALS /g' src/data/seed.js
sed -i '' 's/^const SOURCES /export const SOURCES /g' src/data/seed.js
sed -i '' 's/^const MOD_KINDS /export const MOD_KINDS /g' src/data/seed.js
sed -i '' 's/^const ORPHAN_MODS /export const ORPHAN_MODS /g' src/data/seed.js
sed -i '' 's/^const ORPHAN_LINKED_MOD /export const ORPHAN_LINKED_MOD /g' src/data/seed.js
```

- [ ] **Step 3: Remove the window.VRS_DATA line**

```bash
# Remove the last window.VRS_DATA = { ... } line (it's the last line)
# Open the file and delete the line that starts with `window.VRS_DATA`
grep -n "window.VRS_DATA" apps/frontend/src/data/seed.js
```

Delete that line manually in the editor, or:
```bash
sed -i '' '/^window\.VRS_DATA/d' apps/frontend/src/data/seed.js
```

- [ ] **Step 4: Verify the file**

```bash
grep "^export const" apps/frontend/src/data/seed.js | wc -l
```

Expected: 12 lines.

- [ ] **Step 5: Commit**

```bash
git add apps/frontend/src/data/seed.js
git commit -m "feat(frontend): add seed data module with named exports"
```

---

## Task 4: Layout — Shell

**Files:**
- Create: `apps/frontend/src/layout/Shell.jsx`

- [ ] **Step 1: Copy and start converting**

```bash
mkdir -p apps/frontend/src/layout
cp "claude_design/Verasig/Shell.jsx" apps/frontend/src/layout/Shell.jsx
```

- [ ] **Step 2: Add ESM imports at top of `src/layout/Shell.jsx`**

Insert at line 1 (before the comment):
```jsx
import React from 'react'
import { Avatar } from '../design-system/index.js'
import { Icon } from '../design-system/index.js'
```

- [ ] **Step 3: Remove DS destructuring inside UserMenu**

Delete this line inside `UserMenu`:
```jsx
const { Avatar } = window.VerasigDesignSystem_fd565b;
```

- [ ] **Step 4: Remove DS destructuring inside Shell**

Delete this line inside `Shell`:
```jsx
const { Avatar } = window.VerasigDesignSystem_fd565b;
```

- [ ] **Step 5: Export both components, remove window registrations**

Change:
```jsx
// before (at bottom):
window.Shell = Shell;

// after: add export to function declarations:
export function UserMenu(...) { ... }
export function Shell(...) { ... }
```

And remove the `window.Shell = Shell;` line.

- [ ] **Step 6: Fix React destructuring inside components**

Search for `React.useState`, `React.useRef`, `React.useEffect` inside the file and convert:
- Replace `const [open, setOpen] = React.useState(false)` → add `useState` to the react import and use `useState(false)`
- Replace `const wrapRef = React.useRef(null)` → add `useRef` to react import

Updated import line:
```jsx
import { useState, useRef, useEffect } from 'react'
```

- [ ] **Step 7: Commit**

```bash
git add apps/frontend/src/layout/Shell.jsx
git commit -m "feat(frontend): convert Shell to ESM named exports"
```

---

## Task 5: Pipeline Orchestration

**Files:**
- Create: `apps/frontend/src/features/pipeline/Pipeline.jsx`

- [ ] **Step 1: Copy and start converting**

```bash
mkdir -p apps/frontend/src/features/pipeline
cp "claude_design/Verasig/Pipeline.jsx" apps/frontend/src/features/pipeline/Pipeline.jsx
```

- [ ] **Step 2: Add ESM imports at top**

Insert at line 1:
```jsx
import React, { Fragment } from 'react'
import { Icon } from '../../design-system/index.js'
```

- [ ] **Step 3: Export constants and component**

Change:
```jsx
// before:
const PIPELINE_STEPS = [...]
const PIPELINE_PROCESS_STEPS = [...]
function Pipeline({ current, onStepBack }) { ... }
window.Pipeline = Pipeline;
window.PIPELINE_STEPS = PIPELINE_STEPS;

// after:
export const PIPELINE_STEPS = [...]
export const PIPELINE_PROCESS_STEPS = [...]
export function Pipeline({ current, onStepBack }) { ... }
// remove both window.* lines
```

- [ ] **Step 4: Replace React.Fragment**

Inside Pipeline's JSX, change:
```jsx
// before:
<React.Fragment key={s.id}>

// after:
<Fragment key={s.id}>
```

- [ ] **Step 5: Write Pipeline test**

Create `apps/frontend/src/features/pipeline/Pipeline.test.jsx`:

```jsx
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Pipeline, PIPELINE_STEPS } from './Pipeline.jsx'

describe('Pipeline stepper', () => {
  it('renders all step labels', () => {
    render(<Pipeline current="label" />)
    PIPELINE_STEPS.forEach(({ label }) => {
      expect(screen.getByText(label)).toBeTruthy()
    })
  })

  it('marks steps before current as done', () => {
    const { container } = render(<Pipeline current="distill" />)
    const steps = container.querySelectorAll('.vrs-pipe__step')
    expect(steps[0].classList.contains('is-done')).toBe(true)  // backfill
    expect(steps[1].classList.contains('is-done')).toBe(true)  // label
    expect(steps[2].classList.contains('is-active')).toBe(true) // distill
  })

  it('exports PIPELINE_STEPS with 7 entries', () => {
    expect(PIPELINE_STEPS).toHaveLength(7)
    expect(PIPELINE_STEPS.map(s => s.id)).toEqual([
      'backfill', 'label', 'distill', 'verify', 'exchange', 'risk', 'backtest'
    ])
  })
})
```

- [ ] **Step 6: Run Pipeline test**

```bash
cd apps/frontend && npm test -- src/features/pipeline/Pipeline.test.jsx
```

Expected: 3 passing.

- [ ] **Step 7: Commit**

```bash
git add apps/frontend/src/features/pipeline/Pipeline.jsx apps/frontend/src/features/pipeline/Pipeline.test.jsx
git commit -m "feat(frontend): convert Pipeline to ESM, add stepper test"
```

---

## Task 6: Sources Feature (3 views)

**Files:**
- Create: `apps/frontend/src/features/sources/SourcesView.jsx`
- Create: `apps/frontend/src/features/sources/TelegramSetup.jsx`
- Create: `apps/frontend/src/features/sources/ChatsView.jsx`

- [ ] **Step 1: Copy source files**

```bash
mkdir -p apps/frontend/src/features/sources
cp "claude_design/Verasig/SourcesView.jsx" apps/frontend/src/features/sources/SourcesView.jsx
cp "claude_design/Verasig/TelegramSetup.jsx" apps/frontend/src/features/sources/TelegramSetup.jsx
cp "claude_design/Verasig/ChatsView.jsx" apps/frontend/src/features/sources/ChatsView.jsx
```

- [ ] **Step 2: Convert SourcesView.jsx**

Add at top:
```jsx
import { useState } from 'react'
import { Badge, Button } from '../../design-system/index.js'
import { Icon } from '../../design-system/index.js'
```

- Delete: `const { Badge, Button } = window.VerasigDesignSystem_fd565b;`
- Delete: `const { useState } = React;` (if present — check first)
- Change: `function SourcesView(` → `export function SourcesView(`
- Delete: `window.SourcesView = SourcesView;`

- [ ] **Step 3: Convert TelegramSetup.jsx**

Add at top:
```jsx
import { useState } from 'react'
import { Input, Button, Banner } from '../../design-system/index.js'
import { Icon } from '../../design-system/index.js'
```

- Delete: `const { Input, Button, Banner } = window.VerasigDesignSystem_fd565b;`
- Delete any `const { useState } = React;`
- Change: `function TelegramSetup(` → `export function TelegramSetup(`
- Delete: `window.TelegramSetup = TelegramSetup;`

- [ ] **Step 4: Convert ChatsView.jsx**

Add at top:
```jsx
import { useState } from 'react'
import { Badge, Button, IconButton } from '../../design-system/index.js'
import { Icon } from '../../design-system/index.js'
```

- Delete: `const { Badge, Button, IconButton } = window.VerasigDesignSystem_fd565b;`
- Delete any `const { useState } = React;`
- Change: `function ChatsView(` → `export function ChatsView(`
- Delete: `window.ChatsView = ChatsView;`

- [ ] **Step 5: Commit**

```bash
git add apps/frontend/src/features/sources/
git commit -m "feat(frontend): convert sources feature to ESM"
```

---

## Task 7: Signals Feature

**Files:**
- Create: `apps/frontend/src/features/signals/SignalsView.jsx`

- [ ] **Step 1: Copy**

```bash
mkdir -p apps/frontend/src/features/signals
cp "claude_design/Verasig/SignalsView.jsx" apps/frontend/src/features/signals/SignalsView.jsx
```

- [ ] **Step 2: Convert**

Add at top:
```jsx
import { useState, useMemo } from 'react'
import { Select, Tabs, Badge, Button } from '../../design-system/index.js'
import { Icon } from '../../design-system/index.js'
import { SIGNALS, SOURCES, MOD_KINDS, ORPHAN_MODS, ORPHAN_LINKED_MOD } from '../../data/seed.js'
```

- Delete: `const { Select, Tabs, Badge, Button } = window.VerasigDesignSystem_fd565b;`
- Delete: `const { SIGNALS, SOURCES, MOD_KINDS, ORPHAN_MODS, ORPHAN_LINKED_MOD } = window.VRS_DATA;`
- Delete any `const { useState, useMemo } = React;` (check which hooks it uses)
- Change: `function SignalsView(` → `export function SignalsView(`
- Delete: `window.SignalsView = SignalsView;`

- [ ] **Step 3: Commit**

```bash
git add apps/frontend/src/features/signals/SignalsView.jsx
git commit -m "feat(frontend): convert signals feature to ESM"
```

---

## Task 8: Pipeline Step Views (7 files)

**Files:**
- Create: `apps/frontend/src/features/pipeline/steps/BackfillView.jsx`
- Create: `apps/frontend/src/features/pipeline/steps/LabelView.jsx`
- Create: `apps/frontend/src/features/pipeline/steps/DistillView.jsx`
- Create: `apps/frontend/src/features/pipeline/steps/VerifyView.jsx`
- Create: `apps/frontend/src/features/pipeline/steps/ExchangeView.jsx`
- Create: `apps/frontend/src/features/pipeline/steps/ExecutionView.jsx`
- Create: `apps/frontend/src/features/pipeline/steps/BacktestView.jsx`
- Create: `apps/frontend/src/features/pipeline/steps/execution.css`

- [ ] **Step 1: Copy all step views**

```bash
mkdir -p apps/frontend/src/features/pipeline/steps
cp "claude_design/Verasig/BackfillView.jsx" apps/frontend/src/features/pipeline/steps/BackfillView.jsx
cp "claude_design/Verasig/LabelView.jsx" apps/frontend/src/features/pipeline/steps/LabelView.jsx
cp "claude_design/Verasig/DistillView.jsx" apps/frontend/src/features/pipeline/steps/DistillView.jsx
cp "claude_design/Verasig/VerifyView.jsx" apps/frontend/src/features/pipeline/steps/VerifyView.jsx
cp "claude_design/Verasig/ExchangeView.jsx" apps/frontend/src/features/pipeline/steps/ExchangeView.jsx
cp "claude_design/Verasig/ExecutionView.jsx" apps/frontend/src/features/pipeline/steps/ExecutionView.jsx
cp "claude_design/Verasig/BacktestView.jsx" apps/frontend/src/features/pipeline/steps/BacktestView.jsx
cp "claude_design/Verasig/execution.css" apps/frontend/src/features/pipeline/steps/execution.css
```

- [ ] **Step 2: Convert BackfillView.jsx**

Add at top:
```jsx
import { useState, useEffect, useRef } from 'react'
import { Button } from '../../../design-system/index.js'
import { Icon } from '../../../design-system/index.js'
```

- Delete: `const { Button } = window.VerasigDesignSystem_fd565b;`
- Delete: `const { useState, useEffect, useRef } = React;`
- Change: `function BackfillView(` → `export function BackfillView(`
- Delete: `window.BackfillView = BackfillView;`

- [ ] **Step 3: Convert LabelView.jsx**

Add at top:
```jsx
import { useState, useEffect, useRef } from 'react'
import { Button } from '../../../design-system/index.js'
import { Icon } from '../../../design-system/index.js'
```

- Delete: `const { Button } = window.VerasigDesignSystem_fd565b;`
- Delete any `const { ... } = React;` destructuring
- Change: `function LabelView(` → `export function LabelView(`  
  *(Note: there may be helper sub-components like `MsgMedia`, `MsgCard` — these stay as plain functions, only `LabelView` gets exported)*
- Delete: `window.LabelView = LabelView;`
- **Keep intact:** `window.addEventListener('keydown', onKey)` — this is a real DOM call, not a prototype global.

- [ ] **Step 4: Convert DistillView.jsx**

Add at top:
```jsx
import { useState, useEffect } from 'react'
import { Button } from '../../../design-system/index.js'
import { Icon } from '../../../design-system/index.js'
import { DISTILLED_RULES } from '../../../data/seed.js'
```

- Delete: `const { Button } = window.VerasigDesignSystem_fd565b;`
- Delete: `const { DISTILLED_RULES } = window.VRS_DATA;`
- Delete any `const { ... } = React;`
- Change: `function DistillView(` → `export function DistillView(`
- Delete: `window.DistillView = DistillView;`

- [ ] **Step 5: Convert VerifyView.jsx**

Add at top:
```jsx
import { useState, useEffect } from 'react'
import { Badge, Button } from '../../../design-system/index.js'
import { Icon } from '../../../design-system/index.js'
import { MESSAGES, VERIFY_MIN, VERIFY_MISCLASSIFIED } from '../../../data/seed.js'
```

- Delete: `const { Badge } = window.VerasigDesignSystem_fd565b;` (first occurrence)
- Delete: `const { Button } = window.VerasigDesignSystem_fd565b;` (second occurrence, inside inner component)
- Delete: `const { MESSAGES, VERIFY_MIN, VERIFY_MISCLASSIFIED } = window.VRS_DATA;`
- Delete any `const { ... } = React;`
- Change: only `function VerifyView(` → `export function VerifyView(` (helper components stay unexported)
- Delete: `window.VerifyView = VerifyView;`

- [ ] **Step 6: Convert ExchangeView.jsx**

Add at top:
```jsx
import { useState } from 'react'
import { Button, Input, Banner, Badge } from '../../../design-system/index.js'
import { Icon } from '../../../design-system/index.js'
```

- Delete: `const { Button, Input, Banner, Badge } = window.VerasigDesignSystem_fd565b;`
- Delete any `const { ... } = React;`
- Change: `function ExchangeView(` → `export function ExchangeView(`
- Delete: `window.ExchangeView = ExchangeView;`

- [ ] **Step 7: Convert ExecutionView.jsx**

Add at top:
```jsx
import { useState } from 'react'
import { Button, Input, Select, Tabs, Switch } from '../../../design-system/index.js'
import { Icon } from '../../../design-system/index.js'
import './execution.css'
```

- Delete: `const { Button, Input, Select, Tabs, Switch } = window.VerasigDesignSystem_fd565b;`
- Delete any `const { ... } = React;`
- Change: `function ExecutionView(` → `export function ExecutionView(`
- Delete: `window.ExecutionView = ExecutionView;`

- [ ] **Step 8: Convert BacktestView.jsx**

Add at top:
```jsx
import { useState, useEffect } from 'react'
import { Button, MetricStat, ConfidenceBar, Card } from '../../../design-system/index.js'
import { Icon } from '../../../design-system/index.js'
```

- Delete: `const { Button, MetricStat, ConfidenceBar, Card } = window.VerasigDesignSystem_fd565b;`
- Delete any `const { ... } = React;`
- Change: `function BacktestView(` → `export function BacktestView(`
- Delete: `window.BacktestView = BacktestView;`

- [ ] **Step 9: Commit**

```bash
git add apps/frontend/src/features/pipeline/steps/
git commit -m "feat(frontend): convert pipeline step views to ESM"
```

---

## Task 9: Exchanges + Settings Features

**Files:**
- Create: `apps/frontend/src/features/exchanges/ExchangesView.jsx`
- Create: `apps/frontend/src/features/settings/SettingsView.jsx`

- [ ] **Step 1: Copy SettingsView**

```bash
mkdir -p apps/frontend/src/features/settings
cp "claude_design/Verasig/SettingsView.jsx" apps/frontend/src/features/settings/SettingsView.jsx
```

- [ ] **Step 2: Convert SettingsView.jsx**

Add at top:
```jsx
import { useState } from 'react'
import { Card, Input, Button, Badge, Banner, Dialog } from '../../design-system/index.js'
import { Icon } from '../../design-system/index.js'
```

- Delete: `const { Card, Input, Button, Badge, Banner, Dialog } = window.VerasigDesignSystem_fd565b;`
- Delete any `const { ... } = React;`
- Change: `function SettingsView(` → `export function SettingsView(`
- Delete: `window.SettingsView = SettingsView;`

- [ ] **Step 3: Extract ExchangesView from App.jsx**

The `ExchangesView` component is defined inline in `claude_design/Verasig/App.jsx` at line 295. Create a new file:

```bash
mkdir -p apps/frontend/src/features/exchanges
```

Create `apps/frontend/src/features/exchanges/ExchangesView.jsx`:

```jsx
import { useState } from 'react'
import { Badge, Button, Dialog, Input, Banner, Switch } from '../../design-system/index.js'
import { Icon } from '../../design-system/index.js'
import { EXCHANGES } from '../../data/seed.js'
```

Then copy the `ExchangesView` function body from `claude_design/Verasig/App.jsx` (lines 295–410) into this file, wrapping it as:

```jsx
export function ExchangesView({ bybitConnected, onConnect, onDisconnect }) {
  // ... body from App.jsx lines 295-410 ...
}
```

Remove the `const { Badge, Button, Dialog, Input, Banner, Switch } = window.VerasigDesignSystem_fd565b;` line and `const { EXCHANGES } = window.VRS_DATA;` line from inside the function.

- [ ] **Step 4: Commit**

```bash
git add apps/frontend/src/features/exchanges/ExchangesView.jsx apps/frontend/src/features/settings/SettingsView.jsx
git commit -m "feat(frontend): convert exchanges and settings features to ESM"
```

---

## Task 10: Auth Feature

**Files:**
- Create: `apps/frontend/src/features/auth/BrandPanel.jsx`
- Create: `apps/frontend/src/features/auth/LoginView.jsx`
- Create: `apps/frontend/src/features/auth/RegisterView.jsx`
- Create: `apps/frontend/src/features/auth/auth.css`

- [ ] **Step 1: Copy auth CSS**

```bash
mkdir -p apps/frontend/src/features/auth
cp "claude_design/Verasig/auth.css" apps/frontend/src/features/auth/auth.css
```

- [ ] **Step 2: Create BrandPanel.jsx**

The `BrandPanel` component is in `claude_design/Verasig/auth.jsx` (lines ~13–49). Create `apps/frontend/src/features/auth/BrandPanel.jsx`:

```jsx
import React from 'react'
import { Icon } from '../../design-system/index.js'

function AuthMark({ size = 26 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" fill="none" style={{ color: 'var(--signal-500)' }}>
      <path d="M4 22 L11 22 L17 30 L24 9 L30 18" stroke="currentColor" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="30" cy="18" r="3.4" fill="currentColor" />
    </svg>
  )
}

export function BrandPanel() {
  return (
    // ... copy BrandPanel JSX from auth.jsx lines 16-48 verbatim ...
  )
}
```

Copy the `BrandPanel` function body from `claude_design/Verasig/auth.jsx`.

- [ ] **Step 3: Create LoginView.jsx**

Create `apps/frontend/src/features/auth/LoginView.jsx`:

```jsx
import { useState } from 'react'
import { Button, Input, Checkbox } from '../../design-system/index.js'
import { Icon } from '../../design-system/index.js'
import { BrandPanel } from './BrandPanel.jsx'
import './auth.css'

export function LoginView({ onLogin, onRegister }) {
  const [email, setEmail] = useState('mara@northwave.io')
  const [password, setPassword] = useState('verasig-demo-2026')

  function handleSubmit(e) {
    e.preventDefault()
    onLogin()
  }

  return (
    <div className="auth-wrap">
      <BrandPanel />
      <main className="auth-main">
        <div className="auth-form-wrap">
          <a className="auth-form-wrap__logo" href="#"><Icon name="sources" size={24} />Verasig<span style={{ color: 'var(--signal-500)' }}>.</span></a>
          <div className="auth-eyebrow">Welcome back</div>
          <h1 className="auth-title">Log in to Verasig</h1>
          <p className="auth-lede">Pick up where your sources left off.</p>
          <form className="auth-form" onSubmit={handleSubmit}>
            <Input label="Email" type="email" required value={email} onChange={e => setEmail(e.target.value)}
              iconLeft={<Icon name="users" size={16} />} placeholder="you@company.com" />
            <Input label="Password" type="password" required value={password} onChange={e => setPassword(e.target.value)}
              iconLeft={<Icon name="lock" size={16} />} placeholder="••••••••" />
            <div className="auth-row">
              <Checkbox label="Remember me" defaultChecked />
              <a className="auth-forgot" href="#">Forgot password?</a>
            </div>
            <Button type="submit" variant="primary" fullWidth size="lg"
              iconRight={<Icon name="arrowRight" size={16} />}>Log in</Button>
          </form>
          <div className="auth-switch">New to Verasig? <button type="button" className="auth-link" onClick={onRegister}>Create an account</button></div>
        </div>
      </main>
    </div>
  )
}
```

- [ ] **Step 4: Create RegisterView.jsx**

Create `apps/frontend/src/features/auth/RegisterView.jsx`:

```jsx
import { useState } from 'react'
import { Button, Input, Checkbox } from '../../design-system/index.js'
import { Icon } from '../../design-system/index.js'
import { BrandPanel } from './BrandPanel.jsx'
import './auth.css'

export function RegisterView({ onRegister, onLogin }) {
  const [name, setName] = useState('Mara Voss')
  const [email, setEmail] = useState('mara@northwave.io')
  const [password, setPassword] = useState('verasig-demo-2026')

  function handleSubmit(e) {
    e.preventDefault()
    onRegister()
  }

  return (
    <div className="auth-wrap">
      <BrandPanel />
      <main className="auth-main">
        <div className="auth-form-wrap">
          <a className="auth-form-wrap__logo" href="#"><Icon name="sources" size={24} />Verasig<span style={{ color: 'var(--signal-500)' }}>.</span></a>
          <div className="auth-eyebrow">Get started</div>
          <h1 className="auth-title">Create your account</h1>
          <p className="auth-lede">Connect a source and verify your first channel in a couple of minutes.</p>
          <form className="auth-form" onSubmit={handleSubmit}>
            <Input label="Full name" required value={name} onChange={e => setName(e.target.value)}
              iconLeft={<Icon name="users" size={16} />} placeholder="e.g. Mara Voss" />
            <Input label="Email" type="email" required value={email} onChange={e => setEmail(e.target.value)}
              iconLeft={<Icon name="users" size={16} />} placeholder="you@company.com" />
            <Input label="Password" type="password" required value={password} onChange={e => setPassword(e.target.value)}
              iconLeft={<Icon name="lock" size={16} />} placeholder="••••••••" hint="At least 10 characters." />
            <Button type="submit" variant="primary" fullWidth size="lg"
              iconRight={<Icon name="arrowRight" size={16} />}>Create account</Button>
          </form>
          <p className="auth-legal">By creating an account you agree to our <a href="#">Terms</a> and <a href="#">Privacy Policy</a>.</p>
          <div className="auth-switch">Already have an account? <button type="button" className="auth-link" onClick={onLogin}>Log in</button></div>
        </div>
      </main>
    </div>
  )
}
```

- [ ] **Step 5: Write auth tests**

Create `apps/frontend/src/features/auth/LoginView.test.jsx`:

```jsx
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { LoginView } from './LoginView.jsx'

describe('LoginView', () => {
  it('renders login heading', () => {
    render(<LoginView onLogin={() => {}} onRegister={() => {}} />)
    expect(screen.getByText('Log in to Verasig')).toBeTruthy()
  })

  it('calls onLogin when form is submitted', () => {
    const onLogin = vi.fn()
    render(<LoginView onLogin={onLogin} onRegister={() => {}} />)
    fireEvent.submit(screen.getByRole('form') ?? screen.getByText('Log in').closest('form'))
    expect(onLogin).toHaveBeenCalledOnce()
  })

  it('calls onRegister when Create an account link clicked', () => {
    const onRegister = vi.fn()
    render(<LoginView onLogin={() => {}} onRegister={onRegister} />)
    fireEvent.click(screen.getByText('Create an account'))
    expect(onRegister).toHaveBeenCalledOnce()
  })
})
```

- [ ] **Step 6: Run auth tests**

```bash
cd apps/frontend && npm test -- src/features/auth/LoginView.test.jsx
```

Expected: 3 passing.

- [ ] **Step 7: Commit**

```bash
git add apps/frontend/src/features/auth/
git commit -m "feat(frontend): add auth feature (BrandPanel, LoginView, RegisterView)"
```

---

## Task 11: App.jsx — State Machine

**Files:**
- Modify: `apps/frontend/src/App.jsx` (full rewrite)

This is the most complex task. App.jsx becomes the ESM entry point wiring all features together. It also gains `authScreen` state for auth routing, and loses the `TweaksPanel` dev tool.

- [ ] **Step 1: Open App.jsx for full rewrite**

Replace `apps/frontend/src/App.jsx` entirely with the converted version. Start by copying the prototype:

```bash
cp "claude_design/Verasig/App.jsx" apps/frontend/src/App.jsx
```

- [ ] **Step 2: Replace the entire preamble (top of file)**

Delete everything from the top of the file down to and including `function App() {`. Replace with:

```jsx
import { useState, useEffect, useRef, useLayoutEffect, Fragment } from 'react'
import { Button, IconButton, ToastStack, Toast, Badge, Dialog } from './design-system/index.js'
import { Icon } from './design-system/index.js'
import { Shell } from './layout/Shell.jsx'
import { Pipeline, PIPELINE_STEPS } from './features/pipeline/Pipeline.jsx'
import { SourcesView } from './features/sources/SourcesView.jsx'
import { TelegramSetup } from './features/sources/TelegramSetup.jsx'
import { ChatsView } from './features/sources/ChatsView.jsx'
import { SignalsView } from './features/signals/SignalsView.jsx'
import { BackfillView } from './features/pipeline/steps/BackfillView.jsx'
import { LabelView } from './features/pipeline/steps/LabelView.jsx'
import { DistillView } from './features/pipeline/steps/DistillView.jsx'
import { VerifyView } from './features/pipeline/steps/VerifyView.jsx'
import { ExchangeView } from './features/pipeline/steps/ExchangeView.jsx'
import { ExecutionView } from './features/pipeline/steps/ExecutionView.jsx'
import { BacktestView } from './features/pipeline/steps/BacktestView.jsx'
import { ExchangesView } from './features/exchanges/ExchangesView.jsx'
import { SettingsView } from './features/settings/SettingsView.jsx'
import { LoginView } from './features/auth/LoginView.jsx'
import { RegisterView } from './features/auth/RegisterView.jsx'
import { CHATS, MESSAGES, SIGNALS, SOURCES, MOD_KINDS, ORPHAN_MODS, ORPHAN_LINKED_MOD } from './data/seed.js'

const THEME_ACCENTS = {
  dark:  ['#B9EE2E', '#CBF457', '#8FB81E', 'rgba(185,238,46,0.28)'],
  light: ['#5197FF', '#82B6FF', '#2F6FE0', 'rgba(81,151,255,0.30)'],
}
const THEME_KEY = 'vrs-theme-1'
function loadTheme() {
  try { return localStorage.getItem(THEME_KEY) || 'dark' } catch { return 'dark' }
}

const LS_KEY = 'vrs-proto-state-1'
function loadState() {
  try { return JSON.parse(localStorage.getItem(LS_KEY)) || null } catch { return null }
}

const USER_KEY = 'vrs-user-1'
const USER_DEFAULTS = { firstName: 'Mara', lastName: 'Voss', email: 'mara@northwave.io', plan: 'operator', pendingEmail: null, cancelAt: null }
function loadUser() {
  try { return { ...USER_DEFAULTS, ...(JSON.parse(localStorage.getItem(USER_KEY)) || {}) } } catch { return { ...USER_DEFAULTS } }
}

function mergeChatFlags(savedChats) {
  if (!Array.isArray(savedChats)) return CHATS
  const seed = Object.fromEntries(CHATS.map((c) => [c.id, c]))
  return savedChats.map((c) => {
    const s = seed[c.id]
    return s ? { ...c, historyGaps: s.historyGaps, signalDeletion: s.signalDeletion } : c
  })
}

export default function App() {
```

- [ ] **Step 3: Remove DS destructuring inside App function**

Delete this line at the top of `App()`:
```jsx
const { Button, IconButton, ToastStack, Toast, Badge, Dialog } = window.VerasigDesignSystem_fd565b;
```

- [ ] **Step 4: Remove tweaks**

Delete these lines:
```jsx
const [t, setTweak] = useTweaks({ execControls: 'Segmented', ...TWEAK_DEFAULTS });
```

And the `TWEAK_DEFAULTS` constant at the top.

- [ ] **Step 5: Add auth state**

Add after the existing state declarations (after `const [signalsPreset, setSignalsPreset] = useState(null)`):

```jsx
const [authScreen, setAuthScreen] = useState('login') // 'login' | 'register' | null
```

- [ ] **Step 6: Add auth rendering at top of render logic**

Add before the `if (nav === 'signals')` block:

```jsx
if (authScreen === 'login') {
  return <LoginView onLogin={() => setAuthScreen(null)} onRegister={() => setAuthScreen('register')} />
}
if (authScreen === 'register') {
  return <RegisterView onRegister={() => setAuthScreen(null)} onLogin={() => setAuthScreen('login')} />
}
```

- [ ] **Step 7: Fix window.VRS_DATA references in App**

In App.jsx, the `mergeChatFlags` function and chat init use `window.VRS_DATA.CHATS`. These are now fixed by the import at top (`import { CHATS, ... } from './data/seed.js'`).

Find and replace inside App function:
- `window.VRS_DATA.CHATS` → `CHATS`
- `window.VRS_DATA.MESSAGES` → `MESSAGES` (if any direct reference)

- [ ] **Step 8: Fix PIPELINE_STEPS reference**

Find:
```jsx
const order = window.PIPELINE_STEPS.map((s) => s.id);
```

Replace:
```jsx
const order = PIPELINE_STEPS.map((s) => s.id)
```

- [ ] **Step 9: Fix ExchangesView inline reference**

In the render block, find:
```jsx
body = <ExchangesView bybitConnected={...} onConnect={...} onDisconnect={...} />;
```

This now uses the imported `ExchangesView` — no change needed to the JSX, just ensure the import is at top (done in step 2).

- [ ] **Step 10: Fix tweaks references in ExecutionView call**

Find:
```jsx
else if (screen === 'risk') body = <ExecutionView layout="flow" controls={t.execControls === 'Radio cards' ? 'radio' : 'segmented'} ...
```

Replace (hardcode to segmented since tweaks are removed):
```jsx
else if (screen === 'risk') body = <ExecutionView layout="flow" controls="segmented" hasRisk={true} onRun={() => setScreen('backtest')} />;
```

- [ ] **Step 11: Remove TweaksPanel JSX from return**

Find and delete the `<TweaksPanel ...>...</TweaksPanel>` block from the App return JSX.

- [ ] **Step 12: Fix React.useLayoutEffect**

Replace:
```jsx
React.useLayoutEffect(() => {
```
With:
```jsx
useLayoutEffect(() => {
```

- [ ] **Step 13: Remove window.App registration**

Delete the last line:
```jsx
window.App = App;
```

- [ ] **Step 14: Change to default export**

Ensure the function is `export default function App()` (done in step 2).

- [ ] **Step 15: Write App state machine tests**

Create `apps/frontend/src/App.test.jsx`:

```jsx
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, beforeEach } from 'vitest'
import App from './App.jsx'

beforeEach(() => {
  localStorage.clear()
})

describe('App auth flow', () => {
  it('shows login screen by default', () => {
    render(<App />)
    expect(screen.getByText('Log in to Verasig')).toBeTruthy()
  })

  it('navigates to register from login', () => {
    render(<App />)
    fireEvent.click(screen.getByText('Create an account'))
    expect(screen.getByText('Create your account')).toBeTruthy()
  })

  it('navigates back to login from register', () => {
    render(<App />)
    fireEvent.click(screen.getByText('Create an account'))
    fireEvent.click(screen.getByText('Log in'))
    expect(screen.getByText('Log in to Verasig')).toBeTruthy()
  })

  it('enters main app shell after login', () => {
    render(<App />)
    fireEvent.submit(screen.getByText('Log in').closest('form'))
    expect(screen.getByText('Sources')).toBeTruthy()
  })
})

describe('App nav', () => {
  function loginAndRender() {
    const result = render(<App />)
    fireEvent.submit(screen.getByText('Log in').closest('form'))
    return result
  }

  it('shows Sources view by default after login', () => {
    loginAndRender()
    expect(screen.getByText('Connect where your signals come from')).toBeTruthy()
  })

  it('navigates to Signals via nav', () => {
    loginAndRender()
    fireEvent.click(screen.getByText('Signals'))
    expect(screen.getByText('Signals extracted from your analyzed feeds')).toBeTruthy()
  })
})
```

- [ ] **Step 16: Run App tests**

```bash
cd apps/frontend && npm test -- src/App.test.jsx
```

Expected: all passing. If any fail due to missing DOM setup, investigate and fix.

- [ ] **Step 17: Commit**

```bash
git add apps/frontend/src/App.jsx apps/frontend/src/App.test.jsx
git commit -m "feat(frontend): convert App.jsx to ESM, add auth state machine"
```

---

## Task 12: Wire main.jsx + index.html

**Files:**
- Modify: `apps/frontend/src/main.jsx`
- Modify: `apps/frontend/index.html`
- Create: `apps/frontend/src/app.css`

- [ ] **Step 1: Copy app.css**

```bash
cp "claude_design/Verasig/app.css" apps/frontend/src/app.css
```

- [ ] **Step 2: Update main.jsx**

Replace `apps/frontend/src/main.jsx` with:

```jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import './design-system/styles.css'
import './app.css'
import App from './App.jsx'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
```

- [ ] **Step 3: Update index.html**

Open `apps/frontend/index.html`. Apply these changes:

1. Add `data-theme="dark"` to the `<html>` tag:
```html
<html lang="en" data-theme="dark">
```

2. Remove any old `<link rel="stylesheet">` tags that reference CDN fonts (the DS tokens/fonts.css handles fonts via its own `@import`).

3. The file should end up as a clean minimal Vite entry:
```html
<!doctype html>
<html lang="en" data-theme="dark">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/src/assets/verasig-mark.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Verasig — Signal Verification</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

- [ ] **Step 4: Update DS styles.css to use correct token paths**

Open `apps/frontend/src/design-system/styles.css`. It was copied from the DS root and contains `@import './tokens/...'` lines. Verify these paths resolve correctly relative to `src/design-system/styles.css`. They should work as-is.

- [ ] **Step 5: Run the dev server**

```bash
cd apps/frontend && npm run dev
```

Open `http://localhost:5173` in a browser. You should see the login screen.

- [ ] **Step 6: Run build**

```bash
cd apps/frontend && npm run build
```

Fix any import errors that surface. Common issues:
- Missing `export` on a function — add `export function`
- Wrong relative path (e.g., `../design-system` should be `../../design-system` for deep files)
- Missing React hook in import list — add to the import statement

- [ ] **Step 7: Delete obsolete files**

```bash
# Remove the old placeholder styles.css (App.jsx now uses design-system/styles.css + app.css)
rm apps/frontend/src/styles.css
```

- [ ] **Step 8: Run all tests**

```bash
cd apps/frontend && npm test
```

Expected: all tests pass.

- [ ] **Step 9: Commit**

```bash
git add apps/frontend/src/main.jsx apps/frontend/index.html apps/frontend/src/app.css
git rm apps/frontend/src/styles.css
git commit -m "feat(frontend): wire main.jsx, update index.html, drop placeholder styles"
```

---

## Task 13: Lint

**Files:** All modified files

- [ ] **Step 1: Run ESLint**

```bash
cd apps/frontend && npm run lint
```

- [ ] **Step 2: Fix any lint errors**

Common issues to expect:
- Unused imports — remove them
- Missing dependency in useEffect — add to dependency array or use `// eslint-disable-next-line` with a comment explaining why
- React hooks rules violations — restructure the code

- [ ] **Step 3: Run tests one final time**

```bash
cd apps/frontend && npm test
```

Expected: all passing.

- [ ] **Step 4: Final commit**

```bash
git add -p  # stage only lint fixes
git commit -m "chore(frontend): fix lint warnings after ESM conversion"
```

---

## Self-Review

**Spec coverage check:**

| Spec section | Covered by task |
|-------------|----------------|
| DS source copy | Task 1 |
| DS barrel index.js | Task 2 |
| Icon component | Task 2 |
| seed.js named exports | Task 3 |
| Shell.jsx | Task 4 |
| Pipeline.jsx + PIPELINE_STEPS | Task 5 |
| sources views (3) | Task 6 |
| signals view | Task 7 |
| pipeline step views (7) | Task 8 |
| execution.css co-location | Task 8 |
| ExchangesView extraction | Task 9 |
| SettingsView | Task 9 |
| auth split (3 files) | Task 10 |
| auth.css | Task 10 |
| App.jsx conversion | Task 11 |
| auth state in App | Task 11 |
| tweaks removal | Task 11 |
| main.jsx + index.html | Task 12 |
| app.css | Task 12 |
| Build check | Task 12 |
| Tests | Tasks 2, 5, 10, 11 |
| Lint | Task 13 |
| `data-theme="dark"` on html | Task 12 |
| verasig-mark.svg | Task 1 |

All spec requirements covered. ✅

**RiskView.jsx:** Never copied — confirmed correct, superseded by ExecutionView.
