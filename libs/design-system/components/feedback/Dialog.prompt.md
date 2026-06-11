Modal dialog. Render conditionally with `open`. Scrim click + × call `onClose`.

```jsx
const [open, setOpen] = useState(false);
<Dialog open={open} onClose={() => setOpen(false)}
  title="Reject this signal?"
  description="It will be quarantined and downstream consumers won't receive it."
  footer={<>
    <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
    <Button variant="danger" onClick={confirm}>Reject signal</Button>
  </>}>
  Rejecting SIG-7F2A removes it from the live feed immediately.
</Dialog>
```
