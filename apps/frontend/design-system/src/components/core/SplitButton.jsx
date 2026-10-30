import { Icon } from '../../icons/Icon.jsx'
import { Menu, MenuItem } from '../feedback/Menu.jsx'
import { Button } from './Button.jsx'

/* Fuse a main action with a dropdown of alternative actions. The two halves
   share a variant and abut with a 1px seam; inner corners are flattened so they
   read as one control. */
const CSS = `
.vrs-splitbtn { display: inline-flex; gap: 1px; }
.vrs-splitbtn__main {
  border-top-right-radius: 0;
  border-bottom-right-radius: 0;
}
.vrs-splitbtn__toggle {
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
  padding-left: 9px;
  padding-right: 9px;
}
`
if (typeof document !== 'undefined' && !document.getElementById('vrs-splitbtn-css')) {
  const s = document.createElement('style')
  s.id = 'vrs-splitbtn-css'
  s.textContent = CSS
  document.head.appendChild(s)
}

/**
 * A primary/secondary action fused with a dropdown of alternatives — e.g. a
 * default "Start backfill" with a menu of history depths.
 */
export function SplitButton({
  variant = 'primary',
  size = 'md',
  disabled = false,
  onClick,
  options = [],
  value,
  onSelect,
  menuLabel = 'Choose option',
  className = '',
  children,
  ...rest
}) {
  const cls = ['vrs-splitbtn', className].filter(Boolean).join(' ')
  return (
    <span className={cls} {...rest}>
      <Button
        variant={variant}
        size={size}
        disabled={disabled}
        onClick={onClick}
        className="vrs-splitbtn__main"
      >
        {children}
      </Button>
      <Menu
        align="end"
        label={menuLabel}
        trigger={
          <Button
            variant={variant}
            size={size}
            disabled={disabled}
            aria-label={menuLabel}
            className="vrs-splitbtn__toggle"
          >
            <Icon name="arrowDown" size={14} />
          </Button>
        }
      >
        {options.map((option) => (
          <MenuItem
            key={option.value}
            onClick={() => onSelect && onSelect(option.value)}
            iconRight={option.value === value ? <Icon name="check" size={14} /> : null}
          >
            {option.label}
          </MenuItem>
        ))}
      </Menu>
    </span>
  )
}
