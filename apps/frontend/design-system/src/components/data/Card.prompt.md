Base surface card with optional header/footer. `interactive` for clickable, `glow` for live state.

```jsx
<Card title="Live feed" subtitle="BTC/USD · 24/7" headerActions={<Badge tone="verified" dot>Live</Badge>}>
  …content…
</Card>
<Card interactive onClick={open}>Quick stat</Card>
<Card glow title="Quorum reached">12 / 12 sources agreed</Card>
```
