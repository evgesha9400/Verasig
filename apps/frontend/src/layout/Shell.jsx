import { useState, useRef, useEffect } from 'react'
import { Avatar } from '../design-system/index.js'
import { Icon } from '../design-system/index.js'

/* Verasig prototype — user account popover (Vercel-style) */
export function UserMenu({ user, theme, onThemeChange, onLogout, onOpenSettings }) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e) => { if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false); };
    const onKey = (e) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', onDoc);
    document.addEventListener('keydown', onKey);
    return () => { document.removeEventListener('mousedown', onDoc); document.removeEventListener('keydown', onKey); };
  }, [open]);

  const themes = [
    { id: 'light', icon: 'sun', label: 'Light' },
    { id: 'dark', icon: 'moon', label: 'Dark' },
  ];

  return (
    <div className="vrs-um" ref={wrapRef}>
      <button className={`vrs-um__trigger ${open ? 'is-open' : ''}`} onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        <Avatar name={`${user.firstName} ${user.lastName}`} status="verified" size="sm" />
        <div className="vrs-um__txt">
          <div className="vrs-um__name">{user.firstName} {user.lastName}</div>
          <div className="vrs-um__mail">{user.email}</div>
        </div>
        <Icon name="unfold" size={15} />
      </button>

      {open && (
        <div className="vrs-um__panel" role="menu">
          <div className="vrs-um__head">
            <Avatar name={`${user.firstName} ${user.lastName}`} status="verified" size="md" />
            <div className="vrs-um__txt">
              <div className="vrs-um__name">{user.firstName} {user.lastName}</div>
              <div className="vrs-um__mail">{user.email}</div>
            </div>
          </div>

          <div className="vrs-um__sep" />

          <button className="vrs-um__item" role="menuitem" onClick={() => { setOpen(false); onOpenSettings && onOpenSettings(); }}>
            <span>Account settings</span>
            <Icon name="settings" size={16} />
          </button>

          <div className="vrs-um__sep" />

          <div className="vrs-um__row">
            <span className="vrs-um__row-lbl">Theme</span>
            <div className="vrs-um__seg" role="radiogroup" aria-label="Theme">
              {themes.map((th) => (
                <button key={th.id} type="button" role="radio" aria-checked={theme === th.id}
                  className={`vrs-um__seg-btn ${theme === th.id ? 'is-on' : ''}`}
                  title={th.label} aria-label={th.label}
                  onClick={() => onThemeChange(th.id)}>
                  <Icon name={th.icon} size={15} />
                </button>
              ))}
            </div>
          </div>

          <div className="vrs-um__sep" />

          <button className="vrs-um__item" role="menuitem" onClick={onLogout}>
            <span>Log out</span>
            <Icon name="logout" size={16} />
          </button>
        </div>
      )}
    </div>
  );
}

/* Verasig prototype — app shell: sidebar + topbar */
export function Shell({ nav, onNavigate, title, subtitle, breadcrumb, actions, children, onExit, pipeline, theme, onThemeChange, onLogout, user, onOpenSettings }) {
  const items = [
    { id: 'sources', label: 'Sources', icon: 'sources' },
    { id: 'signals', label: 'Signals', icon: 'signals' },
    { id: 'exchanges', label: 'Exchanges', icon: 'exchanges' },
  ];
  return (
    <div className="vrs-shell">
      <aside className="vrs-sb">
        <div className="vrs-sb__brand">
          <svg width="26" height="26" viewBox="0 0 40 40" fill="none" style={{ color: 'var(--signal-500)' }}>
            <path d="M4 22 L11 22 L17 30 L24 9 L30 18" stroke="currentColor" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" />
            <circle cx="30" cy="18" r="3.4" fill="currentColor" />
          </svg>
          <span className="vrs-sb__word">Verasig<span style={{ color: 'var(--signal-500)' }}>.</span></span>
        </div>

        <nav className="vrs-sb__nav">
          {items.map((it) => (
            <button key={it.id} className={`vrs-sb__item ${nav === it.id ? 'is-active' : ''}`} onClick={() => onNavigate && onNavigate(it.id)}>
              <Icon name={it.icon} />
              <span>{it.label}</span>
            </button>
          ))}
        </nav>

        <div className="vrs-sb__foot">
          <UserMenu user={user} theme={theme} onThemeChange={onThemeChange} onLogout={onLogout} onOpenSettings={onOpenSettings} />
        </div>
      </aside>

      <main className="vrs-main">
        <header className="vrs-top">
          <div className="vrs-top__titles">
            {breadcrumb && (
              <button className="vrs-crumb" onClick={onExit}>
                <Icon name="chevronLeft" size={13} />
                <span>{breadcrumb}</span>
              </button>
            )}
            <div className="vrs-top__title">{title}</div>
            {subtitle && <div className="vrs-top__sub">{subtitle}</div>}
          </div>
          <div className="vrs-top__actions">{actions}</div>
        </header>
        {pipeline}
        <div className="vrs-scroll">{children}</div>
      </main>
    </div>
  );
}
