/* Verasig App — Providers */
function ProvidersView() {
  const { Card, StatusPill, Badge, Button, MetricStat, Avatar } = window.VerasigDesignSystem_fd565b;
  const { providers } = window.VRS_DATA;
  const Plus = () => <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M12 5v14M5 12h14" /></svg>;

  return (
    <div className="vrs-page">
      <div className="vrs-grid-metrics" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
        <Card><MetricStat label="Active providers" value="6" caption="across 4 channels" /></Card>
        <Card><MetricStat label="Avg uptime" value="99.66" unit="%" delta="+0.04" trend="up" caption="last 30 days" /></Card>
        <Card><MetricStat label="Data points · 24h" value="3.5" unit="M" delta="+120k" trend="up" caption="ingested" /></Card>
      </div>

      <Card title="Providers" subtitle="Signal sources connected to this workspace"
        headerActions={<Button variant="primary" size="sm" iconLeft={<Plus />}>Connect provider</Button>}
        padded={false}>
        <div className="vrs-provtable__head">
          <span>Provider</span><span>Channel</span><span>Uptime</span><span style={{ textAlign: 'right' }}>Status</span>
        </div>
        <div className="vrs-provtable">
          {providers.map((p) => (
            <div className="vrs-provtable__row" key={p.id}>
              <div className="vrs-provtable__name">
                <Avatar name={p.name} square tint={p.tint} size="sm" />
                <div>
                  <div className="vrs-provhealth__name">{p.name}</div>
                  <div className="vrs-provhealth__ch">{p.id}.verasig.io</div>
                </div>
              </div>
              <span className="vrs-mono-faint">{p.channel}</span>
              <span className="vrs-mono-faint">{p.uptime.toFixed(2)}%</span>
              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <StatusPill status={p.health} pulse={p.health === 'pending'} />
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
window.ProvidersView = ProvidersView;
