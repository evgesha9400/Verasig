Tab bar for switching views. Controlled (`value` + `onChange`). Underline or pill style.

```jsx
const [tab, setTab] = useState('all');
<Tabs value={tab} onChange={setTab} items={[
  { id: 'all', label: 'All signals', count: 248 },
  { id: 'pending', label: 'Pending', count: 12 },
  { id: 'rejected', label: 'Rejected', count: 3 },
]} />

<Tabs variant="pill" value={range} onChange={setRange} items={['1H','24H','7D']} />
```

`line` for page nav, `pill` for segmented controls. Items can be strings or `{id, label, count}`.
