/* Verasig App — Overview (dashboard) */
function MiniTrace({ color = 'var(--signal-500)' }) {
  // tiny static sparkline-ish verified trace
  return (
    <svg viewBox="0 0 120 36" fill="none" preserveAspectRatio="none" style={{ width: '100%', height: '36px' }}>
      <path d="M0 26 L18 24 L30 27 L44 14 L58 20 L72 9 L86 17 L100 7 L120 12" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" opacity="0.9" />
    </svg>
  );
}

function OverviewView({ onOpenSignal }) {
  const { Card, MetricStat, SignalRow, Badge, StatusPill, ConfidenceBar, Button } = window.VerasigDesignSystem_fd565b;
  const { signals, providers } = window.VRS_DATA;

  return (
    <div className="vrs-page">
      <div className="vrs-grid-metrics">
        <Card><MetricStat label="Verified · 24h" value="11,204" delta="+4.2%" trend="up" caption="of 11,247 signals" /><div style={{ marginTop: 10 }}><MiniTrace /></div></Card>
        <Card><MetricStat label="Median latency" value="182" unit="ms" delta="−12ms" trend="up" caption="p50 across channels" /><div style={{ marginTop: 10 }}><MiniTrace color="var(--viz-2)" /></div></Card>
        <Card><MetricStat label="Quorum rate" value="99.6" unit="%" delta="+0.1" trend="up" caption="reached threshold" /><div style={{ marginTop: 10 }}><MiniTrace color="var(--viz-5)" /></div></Card>
        <Card><MetricStat label="Rejected · 24h" value="43" delta="+7" trend="down" caption="quarantined" /><div style={{ marginTop: 10 }}><MiniTrace color="var(--rejected-500)" /></div></Card>
      </div>

      <div className="vrs-grid-two">
        <Card title="Live verification" subtitle="Most recent signals across all channels"
          headerActions={<Badge tone="verified" dot>Live</Badge>} padded={false}>
          <div className="vrs-feed">
            {signals.slice(0, 5).map((s) => (
              <SignalRow key={s.id} symbol={s.symbol} signalId={s.id} provider={s.provider}
                providerTint={s.tint} channel={s.channel} confidence={s.confidence}
                status={s.status} time={s.time} onClick={() => onOpenSignal(s)} />
            ))}
          </div>
          <div style={{ padding: '12px 16px' }}>
            <Button variant="ghost" size="sm" onClick={() => onOpenSignal(null)}>View all signals →</Button>
          </div>
        </Card>

        <Card title="Provider health" subtitle="Source uptime & quorum" padded={false}>
          <div className="vrs-provhealth">
            {providers.map((p) => (
              <div className="vrs-provhealth__row" key={p.id}>
                <span className="vrs-prov__sw" style={{ background: p.tint }}>{p.name.slice(0, 2)}</span>
                <div className="vrs-provhealth__main">
                  <div className="vrs-provhealth__name">{p.name}</div>
                  <div className="vrs-provhealth__ch">{p.channel}</div>
                </div>
                <span className="vrs-mono-faint">{p.uptime.toFixed(2)}%</span>
                <StatusPill status={p.health} pulse={p.health === 'pending'} />
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
window.OverviewView = OverviewView;
