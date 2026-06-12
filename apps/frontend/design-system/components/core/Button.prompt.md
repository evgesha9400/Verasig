Action button — the primary way users commit to something. Use one primary per view; everything else is secondary, ghost, or danger.

```jsx
<Button variant="primary" iconLeft={<CheckIcon/>}>Verify signal</Button>
<Button variant="secondary">Cancel</Button>
<Button variant="ghost" size="sm">Details</Button>
<Button variant="danger">Reject</Button>
<Button variant="primary" loading>Verifying…</Button>
```

Variants: `primary` (signal accent, dark text — the commit action), `secondary` (raised surface + border), `ghost` (quiet, toolbar use), `danger` (reject/destructive). Sizes `sm | md | lg`. Supports `iconLeft`/`iconRight`, `loading`, `fullWidth`, and `as="a"` for link buttons.
