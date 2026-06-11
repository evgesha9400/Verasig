/* Verasig App — Sidebar */
const VRS_ICONS = {
  overview: <><rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/></>,
  signals: <><path d="M3 12h3l2 6 4-14 3 10 2-4h4"/></>,
  providers: <><circle cx="6" cy="6" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="12" cy="18" r="2.5"/><path d="M7.7 7.7 11 15M16.3 7.7 13 15"/></>,
  channels: <><path d="M4 7h16M4 12h16M4 17h16"/><circle cx="8" cy="7" r="1.6" fill="currentColor" stroke="none"/><circle cx="15" cy="12" r="1.6" fill="currentColor" stroke="none"/><circle cx="10" cy="17" r="1.6" fill="currentColor" stroke="none"/></>,
  settings: <><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-2.7 1.1V21a2 2 0 1 1-4 0v-.1A1.6 1.6 0 0 0 7 19.4a1.6 1.6 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1A1.6 1.6 0 0 0 2.6 14H2.5a2 2 0 1 1 0-4h.1A1.6 1.6 0 0 0 4 7.4l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1A1.6 1.6 0 0 0 9 4.6V4.5a2 2 0 1 1 4 0v.1A1.6 1.6 0 0 0 17 4.6l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8V9.5a1.6 1.6 0 0 0 1.4 1h.1a2 2 0 1 1 0 4h-.1a1.6 1.6 0 0 0-1.4 1Z"/></>,
};

function VrsIcon({ name }) {
  return <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{VRS_ICONS[name]}</svg>;
}

function Sidebar({ active, onNavigate }) {
  const { Avatar } = window.VerasigDesignSystem_fd565b;
  const items = [
    { id: 'overview', label: 'Overview' },
    { id: 'signals', label: 'Signals', count: 248 },
    { id: 'providers', label: 'Providers' },
    { id: 'channels', label: 'Channels' },
    { id: 'settings', label: 'Settings' },
  ];
  return (
    <aside className="vrs-sb">
      <div className="vrs-sb__brand">
        <svg width="26" height="26" viewBox="0 0 40 40" fill="none" style={{ color: 'var(--signal-500)' }}>
          <path d="M4 22 L11 22 L17 30 L24 9 L30 18" stroke="currentColor" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" />
          <circle cx="30" cy="18" r="3.4" fill="currentColor" />
        </svg>
        <span className="vrs-sb__word">Verasig<span style={{ color: 'var(--signal-500)' }}>.</span></span>
      </div>

      <div className="vrs-sb__ws">
        <Avatar name="Northwave" square tint="var(--viz-2)" size="sm" />
        <div className="vrs-sb__ws-txt">
          <div className="vrs-sb__ws-name">Northwave</div>
          <div className="vrs-sb__ws-plan">Production · EU</div>
        </div>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--text-faint)' }}><path d="m8 9 4-4 4 4M16 15l-4 4-4-4" /></svg>
      </div>

      <nav className="vrs-sb__nav">
        {items.map((it) => (
          <button key={it.id} className={`vrs-sb__item ${active === it.id ? 'is-active' : ''}`} onClick={() => onNavigate(it.id)}>
            <VrsIcon name={it.id} />
            <span>{it.label}</span>
            {it.count != null && <span className="vrs-sb__count">{it.count}</span>}
          </button>
        ))}
      </nav>

      <div className="vrs-sb__foot">
        <div className="vrs-sb__live">
          <span className="vrs-sb__live-dot" />
          <span>All systems verified</span>
        </div>
        <div className="vrs-sb__user">
          <Avatar name="Mara Voss" status="verified" size="sm" />
          <div className="vrs-sb__ws-txt">
            <div className="vrs-sb__ws-name">Mara Voss</div>
            <div className="vrs-sb__ws-plan">mara@northwave.io</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
window.Sidebar = Sidebar;
