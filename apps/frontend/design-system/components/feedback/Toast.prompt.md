Toast notification (presentational) + a `ToastStack` container. Wire your own queue.

```jsx
<ToastStack>
  <Toast tone="verified" title="Signal verified" time="11:32:04" onClose={dismiss}>
    SIG-7F2A reached quorum across 12 sources.
  </Toast>
  <Toast tone="rejected" title="Signal rejected" time="11:30:51">
    BTC/USD diverged beyond tolerance.
  </Toast>
</ToastStack>
```

Tones: `verified | pending | rejected | info`.
