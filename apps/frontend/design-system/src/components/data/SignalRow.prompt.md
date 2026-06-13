The core list item of the Verasig app — symbol, source, channel, confidence, status, time. Composes StatusPill + ConfidenceBar.

```jsx
<SignalRow symbol="BTC/USD" signalId="SIG-7F2A" provider="Coinbase" channel="WebSocket"
  confidence={99.4} status="verified" time="11:32:04" onClick={open} />
<SignalRow symbol="ELECTION-2028" provider="Polymarket" providerTint="var(--viz-3)" channel="REST"
  confidence={62} status="pending" time="11:31:58" />
```

Status `verified | pending | rejected | observing`. Pending rows auto-pulse.
