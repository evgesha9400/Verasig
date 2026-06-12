Styled native select. Pass `options` or `<option>` children.

```jsx
<Select label="Channel" options={['Webhook','REST','gRPC','WebSocket']} />
<Select label="Quorum policy" options={[
  {value:'majority', label:'Majority (≥50%)'},
  {value:'unanimous', label:'Unanimous'},
]} />
```
