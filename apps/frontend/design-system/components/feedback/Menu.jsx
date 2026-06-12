import { cloneElement, isValidElement, useEffect, useId, useRef, useState } from 'react'

const CSS = `
.vrs-menu-wrap {
  position: relative;
  display: inline-flex;
}
.vrs-menu {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  z-index: var(--z-overlay);
  min-width: 200px;
  padding: 5px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  background: var(--surface-overlay);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-pop);
}
.vrs-menu[data-side='top'] {
  top: auto;
  bottom: calc(100% + 6px);
}
.vrs-menu[data-align='start'] {
  left: 0;
  right: auto;
}
.vrs-menu__item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 9px 11px;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-body);
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: var(--text-sm);
  font-weight: var(--fw-medium);
  text-align: left;
  white-space: nowrap;
  transition:
    background var(--dur-fast) var(--ease-out),
    color var(--dur-fast) var(--ease-out);
}
.vrs-menu__item:hover:not(:disabled),
.vrs-menu__item:focus-visible {
  background: var(--surface-hover);
  color: var(--text-strong);
  outline: none;
}
.vrs-menu__item:focus-visible {
  box-shadow: var(--focus-ring);
}
.vrs-menu__item:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.vrs-menu__item--danger {
  color: var(--rejected-500);
}
.vrs-menu__item--danger:hover:not(:disabled),
.vrs-menu__item--danger:focus-visible {
  background: var(--rejected-bg);
  color: var(--rejected-500);
}
.vrs-menu__item svg {
  flex: none;
}
.vrs-menu__item-label {
  flex: 1;
  min-width: 0;
}
.vrs-menu__sep {
  height: 1px;
  margin: 4px 2px;
  background: var(--border-subtle);
}
`

if (typeof document !== 'undefined' && !document.getElementById('vrs-menu-css')) {
  const s = document.createElement('style')
  s.id = 'vrs-menu-css'
  s.textContent = CSS
  document.head.appendChild(s)
}

function mergeHandlers(first, second) {
  return (event) => {
    first && first(event)
    if (event.defaultPrevented) return
    second && second(event)
  }
}

export function Menu({
  trigger,
  label = 'Menu',
  align = 'end',
  side = 'bottom',
  className = '',
  children,
  ...rest
}) {
  const [open, setOpen] = useState(false)
  const wrapRef = useRef(null)
  const menuId = useId()

  useEffect(() => {
    if (!open) return
    function onPointerDown(event) {
      if (wrapRef.current && wrapRef.current.contains(event.target)) return
      setOpen(false)
    }
    function onKeyDown(event) {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  const resolvedTrigger = typeof trigger === 'function' ? trigger({ open }) : trigger
  const triggerNode = isValidElement(resolvedTrigger) ? (
    cloneElement(resolvedTrigger, {
      'aria-haspopup': 'menu',
      'aria-expanded': open,
      'aria-controls': open ? menuId : undefined,
      onClick: mergeHandlers(resolvedTrigger.props.onClick, (event) => {
        event.stopPropagation()
        setOpen((current) => !current)
      })
    })
  ) : (
    <button
      type="button"
      aria-label={label}
      aria-haspopup="menu"
      aria-expanded={open}
      aria-controls={open ? menuId : undefined}
      onClick={(event) => {
        event.stopPropagation()
        setOpen((current) => !current)
      }}
    >
      {label}
    </button>
  )

  return (
    <span
      className={['vrs-menu-wrap', className].filter(Boolean).join(' ')}
      ref={wrapRef}
      onClick={(event) => event.stopPropagation()}
    >
      {triggerNode}
      {open && (
        <div
          id={menuId}
          className="vrs-menu"
          role="menu"
          data-align={align}
          data-side={side}
          onClick={(event) => {
            const item = event.target.closest('[role="menuitem"]')
            if (item && !item.disabled) setOpen(false)
          }}
          {...rest}
        >
          {children}
        </div>
      )}
    </span>
  )
}

export function MenuItem({
  tone,
  iconLeft,
  iconRight,
  className = '',
  children,
  type = 'button',
  ...rest
}) {
  const cls = [
    'vrs-menu__item',
    tone === 'danger' ? 'vrs-menu__item--danger' : '',
    className
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <button className={cls} type={type} role="menuitem" {...rest}>
      {iconLeft}
      <span className="vrs-menu__item-label">{children}</span>
      {iconRight}
    </button>
  )
}

export function MenuSeparator() {
  return <span className="vrs-menu__sep" role="separator" />
}
