Text input with label, hint, error, and optional icon. Use `mono` for IDs/keys/endpoints.

```jsx
<Input label="Provider name" placeholder="e.g. Coinbase" required />
<Input label="Webhook endpoint" mono iconLeft={<LinkIcon/>} placeholder="https://…" />
<Input label="API key" error="Key is invalid" defaultValue="sk_live_…" mono />
<Input placeholder="Search signals" trailing={<span className="vrs-input__kbd">⌘K</span>} />
```

Props: `label`, `hint`, `error`, `required`, `iconLeft`, `trailing`, `mono`, plus all native input attrs.
