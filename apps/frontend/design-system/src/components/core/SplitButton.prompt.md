# SplitButton

A default action fused with a dropdown of alternatives. The main half runs the
primary action immediately; the caret opens a menu of related options and marks
the active one.

Use when one action has a sensible default plus a few variants that shouldn't
each get their own button — e.g. "Start backfill" defaulting to 1 year, with 6
months / all history in the caret menu.

- `variant` / `size` apply to both halves.
- `onClick` fires the main action; `options` + `onSelect` drive the menu.
- `value` marks the active option with a check.
- Not for unrelated actions — use separate buttons or a plain Menu for those.
