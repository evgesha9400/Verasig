Loading heartbeat — one family, two glyphs. `bar` (default) sweeps an accent band; `dot` pulses. With `title`/`note` renders a centered block; with neither, a bare inline glyph.

```jsx
<Loader variant="bar" size="lg" title="Loading signals" note="Reading extracted signals from verified feeds." />
<Loader variant="dot" size="sm" title="Opening review…" />
<Loader variant="bar" size="md" />  {/* bare — surrounding UI supplies the text */}
```

Sizes: `sm | md | lg` (glyph + block scale). Always `role="status"`, honours `prefers-reduced-motion`. Buttons use their own `loading` ring, not this.
