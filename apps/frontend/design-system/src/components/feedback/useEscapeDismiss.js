import { useEffect, useState } from 'react'

function chain(own, theirs) {
  return (event) => {
    own(event)
    theirs && theirs(event)
  }
}

/**
 * Escape-dismiss for CSS hover/focus overlays (WCAG 1.4.13). While the wrapper
 * is hovered or holds focus, Escape sets `data-dismissed`, which the overlay CSS
 * uses to hide the panel. Leaving (mouseleave, or focus moving out) clears it.
 * Returns wrapper props; pass the caller's own handlers so they still run.
 */
export function useEscapeDismiss(handlers = {}, onDismiss) {
  const [engaged, setEngaged] = useState(false)
  const [dismissed, setDismissed] = useState(false)

  useEffect(() => {
    if (!engaged) return
    function onKeyDown(event) {
      if (event.key !== 'Escape') return
      setDismissed(true)
      onDismiss && onDismiss()
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [engaged, onDismiss])

  function leave() {
    setEngaged(false)
    setDismissed(false)
  }

  return {
    'data-dismissed': dismissed || undefined,
    onMouseEnter: chain(() => setEngaged(true), handlers.onMouseEnter),
    onMouseLeave: chain(leave, handlers.onMouseLeave),
    onFocus: chain(() => setEngaged(true), handlers.onFocus),
    onBlur: chain((event) => {
      if (!event.currentTarget.contains(event.relatedTarget)) leave()
    }, handlers.onBlur)
  }
}
