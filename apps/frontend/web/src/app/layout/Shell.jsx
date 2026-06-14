import {
  Avatar,
  Button,
  Menu,
  MenuItem,
  MenuSeparator,
  ThemeToggle,
  Icon
} from '@verasig/design-system'

/* Verasig prototype — user account popover (Vercel-style) */
export function UserMenu({ user, theme, onThemeChange, onLogout, onOpenSettings }) {
  return (
    <Menu
      className="vrs-um"
      side="top"
      align="start"
      trigger={({ open }) => (
        <button type="button" className={`vrs-um__trigger ${open ? 'is-open' : ''}`}>
          <Avatar
            name={`${user.firstName} ${user.lastName}`}
            status="verified"
            size="sm"
          />
          <div className="vrs-um__txt">
            <div className="vrs-um__name">
              {user.firstName} {user.lastName}
            </div>
            <div className="vrs-um__mail">{user.email}</div>
          </div>
          <Icon name="unfold" size={15} />
        </button>
      )}
    >
      <div className="vrs-um__head">
        <Avatar
          name={`${user.firstName} ${user.lastName}`}
          status="verified"
          size="md"
        />
        <div className="vrs-um__txt">
          <div className="vrs-um__name">
            {user.firstName} {user.lastName}
          </div>
          <div className="vrs-um__mail">{user.email}</div>
        </div>
      </div>

      <MenuSeparator />

      <MenuItem
        iconRight={<Icon name="settings" size={16} />}
        onClick={() => {
          onOpenSettings && onOpenSettings()
        }}
      >
        Account settings
      </MenuItem>

      <MenuSeparator />

      <div className="vrs-um__row">
        <span className="vrs-um__row-lbl">Theme</span>
        <ThemeToggle value={theme} onChange={onThemeChange} />
      </div>

      <MenuSeparator />

      <MenuItem iconRight={<Icon name="logout" size={16} />} onClick={onLogout}>
        Log out
      </MenuItem>
    </Menu>
  )
}

/* Verasig prototype — app shell: sidebar + topbar */
export function Shell({
  nav,
  onNavigate,
  title,
  subtitle,
  breadcrumb,
  actions,
  children,
  onExit,
  pipeline,
  theme,
  onThemeChange,
  onLogout,
  user,
  onOpenSettings
}) {
  const items = [
    { id: 'sources', label: 'Sources', icon: 'sources' },
    { id: 'signals', label: 'Signals', icon: 'signals' },
    { id: 'exchanges', label: 'Exchanges', icon: 'exchanges' }
  ]
  return (
    <div className="vrs-shell">
      <aside className="vrs-sb">
        <div className="vrs-sb__brand">
          <svg
            width="26"
            height="26"
            viewBox="0 0 40 40"
            fill="none"
            style={{ color: 'var(--signal-500)' }}
          >
            <path
              d="M4 22 L11 22 L17 30 L24 9 L30 18"
              stroke="currentColor"
              strokeWidth="3.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <circle cx="30" cy="18" r="3.4" fill="currentColor" />
          </svg>
          <span className="vrs-sb__word">
            Verasig<span style={{ color: 'var(--signal-500)' }}>.</span>
          </span>
        </div>

        <nav className="vrs-sb__nav">
          {items.map((it) => (
            <button
              key={it.id}
              className={`vrs-sb__item ${nav === it.id ? 'is-active' : ''}`}
              onClick={() => onNavigate && onNavigate(it.id)}
            >
              <Icon name={it.icon} />
              <span>{it.label}</span>
            </button>
          ))}
        </nav>

        <div className="vrs-sb__foot">
          <UserMenu
            user={user}
            theme={theme}
            onThemeChange={onThemeChange}
            onLogout={onLogout}
            onOpenSettings={onOpenSettings}
          />
        </div>
      </aside>

      <main className="vrs-main">
        <header className="vrs-top">
          <div className="vrs-top__titles">
            {breadcrumb && (
              <Button
                variant="ghost"
                size="sm"
                className="vrs-backbtn"
                iconLeft={<Icon name="chevronLeft" size={14} />}
                onClick={onExit}
              >
                {breadcrumb}
              </Button>
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
  )
}
