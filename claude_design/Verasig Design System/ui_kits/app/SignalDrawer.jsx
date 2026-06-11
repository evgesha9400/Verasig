/* Verasig App — Signal detail drawer */
function SignalDrawer({ signal, onClose, onReject }) {
  const { StatusPill, ConfidenceBar, Badge, Button, Avatar } = window.VerasigDesignSystem_fd565b;
  const { sources } = window.VRS_DATA;
  if (!signal) return null;

  return (
    <>
      <div className="vrs-drawer__scrim" onClick={onClose} />
      <aside className="vrs-drawer" role="dialog" aria-label="Signal detail">
        <div className="vrs-drawer__head">
          <div>
            <div className="vrs-drawer__sym">{signal.symbol}</div>
            <div className="vrs-drawer__id">{signal.id}</div>
          </div>
          <button className="vrs-drawer__close" aria-label="Close" onClick={onClose}>×</button>
        </div>

        <div className="vrs-drawer__statusbar">
          <StatusPill status={signal.status} pulse={signal.status === 'pending'} />
          <span className="vrs-mono-faint">{signal.channel}</span>
          <span className="vrs-mono-faint" style={{ marginLeft: 'auto' }}>{signal.time}</span>
        </div>

        <div className="vrs-drawer__body">
          <section className="vrs-drawer__sec">
            <div className="vrs-drawer__sec-h">Quorum</div>
            <ConfidenceBar value={signal.confidence} threshold={80} label="Aggregate confidence" />
            <div className="vrs-quorum">
              <div className="vrs-quorum__cell"><span className="vrs-mono-faint">Sources</span><span className="vrs-quorum__v">{signal.sources}</span></div>
              <div className="vrs-quorum__cell"><span className="vrs-mono-faint">Agreed</span><span className="vrs-quorum__v" style={{ color: 'var(--verified-500)' }}>{signal.agree}</span></div>
              <div className="vrs-quorum__cell"><span className="vrs-mono-faint">Threshold</span><span className="vrs-quorum__v">≥ 80%</span></div>
            </div>
          </section>

          <section className="vrs-drawer__sec">
            <div className="vrs-drawer__sec-h">Source breakdown</div>
            <div className="vrs-srclist">
              {sources.map((s) => (
                <div className="vrs-srclist__row" key={s.name}>
                  <span className={`vrs-srclist__dot ${s.ok ? 'ok' : 'bad'}`} />
                  <span className="vrs-srclist__name">{s.name}</span>
                  <span className="vrs-srclist__val">{s.value}</span>
                  <span className={`vrs-srclist__dev ${s.ok ? '' : 'bad'}`}>{s.dev}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="vrs-drawer__sec">
            <div className="vrs-drawer__sec-h">Timeline</div>
            <div className="vrs-timeline">
              <div className="vrs-tl__item"><span className="vrs-tl__t">11:32:01</span><span className="vrs-tl__d">Ingested from {signal.provider}</span></div>
              <div className="vrs-tl__item"><span className="vrs-tl__t">11:32:02</span><span className="vrs-tl__d">Cross-checked {signal.sources} sources</span></div>
              <div className="vrs-tl__item"><span className="vrs-tl__t">11:32:04</span><span className="vrs-tl__d" style={{ color: 'var(--text-strong)' }}>Quorum {signal.status === 'rejected' ? 'failed — quarantined' : 'reached — verified'}</span></div>
            </div>
          </section>
        </div>

        <div className="vrs-drawer__foot">
          <Button variant="secondary" fullWidth>Replay</Button>
          {signal.status !== 'rejected'
            ? <Button variant="danger" fullWidth onClick={onReject}>Reject</Button>
            : <Button variant="primary" fullWidth>Re-verify</Button>}
        </div>
      </aside>
    </>
  );
}
window.SignalDrawer = SignalDrawer;
