import { Button, Icon } from '@verasig/design-system'

/* Verasig — Template Mining: shared list pager.
   Presentational — the parent owns the page state and the slice; this renders
   the controls plus a live "X–Y of N" status. Renders nothing when a single
   page covers everything. Boundary buttons use aria-disabled (not native
   disabled) so they stay focusable: paging to an end never drops keyboard
   focus, and the clamped onPageChange makes a press at the bound a no-op. */
export function Pager({ page, pageCount, windowStart, pageSize, total, onPageChange }) {
  if (pageCount <= 1) return null
  const atStart = page === 0
  const atEnd = page >= pageCount - 1
  return (
    <div className="vrs-tm-pager" role="group" aria-label="Pages">
      <Button
        variant="ghost"
        size="sm"
        aria-disabled={atStart}
        iconLeft={<Icon name="chevronLeft" size={14} />}
        onClick={() => onPageChange(Math.max(0, page - 1))}
      >
        Prev
      </Button>
      <span
        className="vrs-tm-pager__label"
        role="status"
        aria-live="polite"
        aria-atomic="true"
      >
        {windowStart + 1}–{Math.min(windowStart + pageSize, total)} of {total}
      </span>
      <Button
        variant="ghost"
        size="sm"
        aria-disabled={atEnd}
        iconRight={<Icon name="chevronRight" size={14} />}
        onClick={() => onPageChange(Math.min(pageCount - 1, page + 1))}
      >
        Next
      </Button>
    </div>
  )
}
