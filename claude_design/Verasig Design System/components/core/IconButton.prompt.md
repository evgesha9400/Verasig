Icon-only square button for toolbars, table rows, and dense headers. Always pass `label`.

```jsx
<IconButton label="Refresh" onClick={reload}><RefreshIcon/></IconButton>
<IconButton label="Settings" variant="solid"><GearIcon/></IconButton>
<IconButton label="Add source" variant="accent" size="lg"><PlusIcon/></IconButton>
```

Variants: `ghost` (default, quiet), `solid` (bordered surface), `accent` (signal tint). Sizes `sm | md | lg`.
