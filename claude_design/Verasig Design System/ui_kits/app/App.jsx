/* Verasig App — shell */
function EmptyView({ label }) {
  return (
    <div className="vrs-page">
      <div className="vrs-empty">
        <svg width="34" height="34" viewBox="0 0 40 40" fill="none" style={{ color: 'var(--text-faint)' }}>
          <path d="M4 22 L11 22 L17 30 L24 9 L30 18" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
          <circle cx="30" cy="18" r="3" fill="currentColor" />
        </svg>
        <div className="vrs-empty__t">{label}</div>
        <div className="vrs-empty__s">This area is part of the Verasig kit — wire it up to your data.</div>
      </div>
    </div>
  );
}

function App() {
  const { Sidebar, Topbar, OverviewView, SignalsView, ProvidersView, SignalDrawer } = window;
  const { Dialog, Button, Toast, ToastStack } = window.VerasigDesignSystem_fd565b;
  const { useState } = React;
  const [nav, setNav] = useState('overview');
  const [signal, setSignal] = useState(null);
  const [confirmReject, setConfirmReject] = useState(false);
  const [toast, setToast] = useState(null);

  const TITLES = {
    overview: ['Overview', 'Real-time verification across every channel'],
    signals: ['Signals', '248 signals in the last hour'],
    providers: ['Providers', '6 sources connected'],
    channels: ['Channels', 'Webhook · REST · gRPC · WebSocket'],
    settings: ['Settings', 'Workspace & verification policy'],
  };

  function openSignal(s) {
    if (s === null) { setNav('signals'); return; }
    setSignal(s);
  }
  function doReject() {
    setConfirmReject(false);
    setSignal(null);
    setToast({ tone: 'rejected', title: 'Signal rejected', msg: 'Quarantined and removed from the live feed.', time: '11:32:40' });
    setTimeout(() => setToast(null), 4200);
  }

  let view;
  if (nav === 'overview') view = <OverviewView onOpenSignal={openSignal} />;
  else if (nav === 'signals') view = <SignalsView onOpenSignal={openSignal} />;
  else if (nav === 'providers') view = <ProvidersView />;
  else view = <EmptyView label={TITLES[nav][0]} />;

  return (
    <div className="vrs-shell">
      <Sidebar active={nav} onNavigate={setNav} />
      <main className="vrs-main">
        <Topbar title={TITLES[nav][0]} subtitle={TITLES[nav][1]} />
        <div className="vrs-scroll">{view}</div>
      </main>

      <SignalDrawer signal={signal} onClose={() => setSignal(null)} onReject={() => setConfirmReject(true)} />

      <Dialog open={confirmReject} onClose={() => setConfirmReject(false)}
        title="Reject this signal?"
        description="It will be quarantined and downstream consumers won't receive it."
        footer={<>
          <Button variant="ghost" onClick={() => setConfirmReject(false)}>Cancel</Button>
          <Button variant="danger" onClick={doReject}>Reject signal</Button>
        </>}>
        Rejecting <strong style={{ color: 'var(--text-strong)', fontFamily: 'var(--font-mono)' }}>{signal && signal.id}</strong> removes it from the live feed immediately.
      </Dialog>

      {toast && (
        <ToastStack>
          <Toast tone={toast.tone} title={toast.title} time={toast.time} onClose={() => setToast(null)}>{toast.msg}</Toast>
        </ToastStack>
      )}
    </div>
  );
}
window.App = App;
