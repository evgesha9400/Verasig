/* Inject component styles once (self-contained, token-driven). */
const CSS = `
.vrs-textlink {
  background: none; border: 0; padding: 0; margin: 0;
  font: inherit; color: var(--link);
  text-decoration: none; cursor: pointer;
}
.vrs-textlink:hover { text-decoration: underline; }
.vrs-textlink:focus-visible {
  outline: none; border-radius: 3px; box-shadow: var(--focus-ring);
}
.vrs-textlink__accent { color: var(--accent-text); }
`
if (typeof document !== 'undefined' && !document.getElementById('vrs-textlink-css')) {
  const s = document.createElement('style')
  s.id = 'vrs-textlink-css'
  s.textContent = CSS
  document.head.appendChild(s)
}

/**
 * Inline text link / link-styled action.
 * Renders an <a> when `href` is set, otherwise a real <button> (keyboard-accessible).
 */
export function TextLink({
  as,
  href,
  tone = 'link',
  type = 'button',
  className = '',
  children,
  ...rest
}) {
  const Tag = as || (href ? 'a' : 'button')
  const cls = [
    'vrs-textlink',
    tone !== 'link' ? `vrs-textlink__${tone}` : '',
    className
  ]
    .filter(Boolean)
    .join(' ')
  return (
    <Tag
      className={cls}
      href={Tag === 'a' ? href : undefined}
      type={Tag === 'button' ? type : undefined}
      {...rest}
    >
      {children}
    </Tag>
  )
}
