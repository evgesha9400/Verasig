/* Verasig App — Topbar */
function Topbar({ title, subtitle, onReject }) {
  const { Input, Button, IconButton, Tooltip, Badge } = window.VerasigDesignSystem_fd565b;
  const Search = () => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></svg>;
  const Bell = () => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0" /></svg>;
  const Docs = () => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z" /></svg>;

  return (
    <header className="vrs-top">
      <div className="vrs-top__titles">
        <h1 className="vrs-top__title">{title}</h1>
        {subtitle && <span className="vrs-top__sub">{subtitle}</span>}
      </div>
      <div className="vrs-top__search">
        <Input iconLeft={<Search />} placeholder="Search signals, providers, IDs…"
          trailing={<span className="vrs-input__kbd">⌘K</span>} />
      </div>
      <div className="vrs-top__actions">
        <Tooltip label="Documentation" side="bottom"><IconButton label="Docs"><Docs /></IconButton></Tooltip>
        <Tooltip label="Alerts" side="bottom"><IconButton label="Alerts"><Bell /></IconButton></Tooltip>
        <Button variant="primary" size="sm">New feed</Button>
      </div>
    </header>
  );
}
window.Topbar = Topbar;
