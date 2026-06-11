/* Verasig App — Signals (table + filters) */
function SignalsView({ onOpenSignal }) {
  const { Tabs, Tag, SignalRow, Input, Button } = window.VerasigDesignSystem_fd565b;
  const { useState } = React;
  const { signals } = window.VRS_DATA;
  const [tab, setTab] = useState('all');
  const [chans, setChans] = useState({ Webhook: true, REST: true, gRPC: true, WebSocket: true });

  const counts = {
    all: signals.length,
    verified: signals.filter((s) => s.status === 'verified').length,
    pending: signals.filter((s) => s.status === 'pending').length,
    rejected: signals.filter((s) => s.status === 'rejected').length,
  };
  const filtered = signals.filter((s) => tab === 'all' || s.status === tab);

  const Filter = () => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 5h18l-7 8v6l-4 2v-8L3 5Z" /></svg>;

  return (
    <div className="vrs-page">
      <div className="vrs-signals__bar">
        <Tabs value={tab} onChange={setTab} items={[
          { id: 'all', label: 'All', count: counts.all },
          { id: 'verified', label: 'Verified', count: counts.verified },
          { id: 'pending', label: 'Pending', count: counts.pending },
          { id: 'rejected', label: 'Rejected', count: counts.rejected },
        ]} />
        <div className="vrs-signals__filters">
          {Object.keys(chans).map((c) => (
            <Tag key={c} swatch={chans[c] ? 'var(--signal-500)' : 'var(--ink-600)'}
              onClick={() => setChans({ ...chans, [c]: !chans[c] })}
              style={{ opacity: chans[c] ? 1 : 0.5 }}>{c}</Tag>
          ))}
          <Button variant="secondary" size="sm" iconLeft={<Filter />}>Filters</Button>
        </div>
      </div>

      <div className="vrs-table">
        <div className="vrs-table__head">
          <span style={{ gridColumn: '1 / 3' }}>Signal</span>
          <span>Source</span>
          <span>Confidence</span>
          <span style={{ textAlign: 'right' }}>Status · time</span>
        </div>
        <div className="vrs-feed">
          {filtered.map((s) => (
            <SignalRow key={s.id} symbol={s.symbol} signalId={s.id} provider={s.provider}
              providerTint={s.tint} channel={s.channel} confidence={s.confidence}
              status={s.status} time={s.time} onClick={() => onOpenSignal(s)} />
          ))}
        </div>
      </div>
    </div>
  );
}
window.SignalsView = SignalsView;
