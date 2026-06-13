Confidence meter — 0–100 score vs quorum threshold. Color shifts red→amber→green across threshold.

```jsx
<ConfidenceBar value={99.4} threshold={80} />
<ConfidenceBar value={62} threshold={80} label="Quorum" />
<ConfidenceBar value={88} segments={12} showValue={false} />
```
