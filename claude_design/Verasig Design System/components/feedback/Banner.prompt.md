Inline alert with semantic tone, icon, accent rail, optional dismiss + actions.

```jsx
<Banner tone="rejected" title="Signal rejected" onClose={dismiss}>
  3 of 12 sources disagreed beyond tolerance.
</Banner>
<Banner tone="pending" title="Awaiting quorum">Holding until ≥ 8 sources respond.</Banner>
<Banner tone="info">New provider “Stork” is now available.</Banner>
```

Tones: `verified | pending | rejected | info | neutral`. Pass `actions` for buttons.
