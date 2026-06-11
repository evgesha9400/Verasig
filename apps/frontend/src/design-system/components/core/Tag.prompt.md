Interactive chip for filters, selected channels and providers. Optional color swatch and removable ×.

```jsx
<Tag swatch="var(--viz-2)">Webhook</Tag>
<Tag onRemove={() => drop('coinbase')}>Coinbase</Tag>
<Tag onClick={toggle} swatch="var(--viz-3)">REST · 8</Tag>
```

Pass `swatch` for a color square, `onRemove` for a × button, `onClick` to make the whole chip a toggle.
