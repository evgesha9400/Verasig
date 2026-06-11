import { useState } from 'react'
import { Badge, Button, Dialog, Input, Banner, Switch } from '../../design-system/index.js'
import { Icon } from '../../design-system/index.js'
import { EXCHANGES } from '../../data/seed.js'

export function ExchangesView({ bybitConnected, onConnect, onDisconnect }) {
  const bybit = EXCHANGES.find((d) => d.id === 'bybit');
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [configuring, setConfiguring] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [key, setKey] = useState('');
  const [secret, setSecret] = useState('');
  const valid = key.trim().length >= 12 && secret.trim().length >= 12;
  function startConfigure() { setConfiguring(true); setKey(''); setSecret(''); }
  function cancelConfigure() { if (verifying) return; setConfiguring(false); setKey(''); setSecret(''); }
  function verifyAndConnect() {
    if (!valid || verifying) return;
    setVerifying(true);
    setTimeout(() => { setVerifying(false); setConfiguring(false); setKey(''); setSecret(''); onConnect && onConnect(); }, 1700);
  }
  const ByLogo = () => (
    <span className="vrs-src-logo" style={{ background: `color-mix(in srgb, ${bybit.brand} 18%, transparent)`, color: bybit.brand }}>
      <Icon name="bybit" size={26} fill />
    </span>
  );
  return (
    <div className="vrs-page">
      {/* Connected */}
      <div>
        <div className="vrs-sec-h"><span className="vrs-sec-t">Connected exchanges</span></div>
        <div className="vrs-src-grid" style={{ marginTop: 12 }}>
          {bybitConnected ? (
            <div className="vrs-src-card is-clickable">
              <div className="vrs-src-card__top">
                <ByLogo />
                <div style={{ flex: 1 }}>
                  <div className="vrs-src-card__name">{bybit.name}</div>
                  <div className="vrs-src-card__kind">{bybit.kind}</div>
                </div>
                <Badge tone="verified" dot>Connected</Badge>
              </div>
              <div className="vrs-src-card__desc">Trade-only API key linked. Verified signals route here in real time.</div>
              <div className="vrs-src-card__foot">
                <span className="vrs-src-meta"><Icon name="key" size={13} /> {bybit.account}</span>
                <Button variant="danger" size="sm" onClick={() => setConfirmOpen(true)}>Disconnect</Button>
              </div>
            </div>
          ) : (
            <div className="vrs-src-card" style={{ borderStyle: 'dashed', alignItems: 'center', justifyContent: 'center', textAlign: 'center', minHeight: 168, color: 'var(--text-faint)' }}>
              <div className="vrs-src-card__desc" style={{ flex: 'none' }}>No exchanges connected yet.<br/>Configure {bybit.name} below to route signals.</div>
            </div>
          )}
        </div>
      </div>

      {/* Available */}
      <div>
        <div className="vrs-sec-h"><span className="vrs-sec-t">Available to configure</span></div>
        <div className="vrs-src-grid" style={{ marginTop: 12 }}>
          {!bybitConnected && (
            <div className="vrs-src-card" style={configuring ? { gridColumn: '1 / -1', maxWidth: 520 } : undefined}>
              <div className="vrs-src-card__top">
                <ByLogo />
                <div style={{ flex: 1 }}>
                  <div className="vrs-src-card__name">{bybit.name}</div>
                  <div className="vrs-src-card__kind">{bybit.kind}</div>
                </div>
                {configuring && <Badge tone="pending">Not configured</Badge>}
              </div>
              {configuring ? (
                <div className="vrs-opt__config" style={{ marginTop: 0, paddingTop: 4, borderTop: 0 }} onClick={(e) => e.stopPropagation()}>
                  {verifying ? (
                    <Banner tone="info" title="Verifying API credentials…">Checking permissions and placing a zero-value test order.</Banner>
                  ) : (
                    <Banner tone="pending" title="Use a trade-only key">Create an API key with trade permission in Bybit → API Management. Disable withdrawal — Verasig only needs read + trade.</Banner>
                  )}
                  <Input label="API Key" mono placeholder="J7n2Kp9XvR4mQ1wL" value={key} onChange={(e) => setKey(e.target.value)} disabled={verifying} iconLeft={<Icon name="key" size={15} />} required />
                  <Input label="API Secret" mono placeholder="••••••••••••••••••••••••" value={secret} onChange={(e) => setSecret(e.target.value)} disabled={verifying} iconLeft={<Icon name="lock" size={15} />} required type="password" />
                  <div className="vrs-row-between" style={{ padding: '0 2px' }}>
                    <Switch label="Use testnet first" />
                    <span className="vrs-help">Recommended for the first run.</span>
                  </div>
                  <div className="vrs-row-between">
                    <Button variant="ghost" size="sm" onClick={cancelConfigure} disabled={verifying}>Cancel</Button>
                    <Button variant="primary" size="sm" loading={verifying} disabled={!valid && !verifying} onClick={verifyAndConnect} iconLeft={verifying ? null : <Icon name="check" size={16} />}>
                      {verifying ? 'Verifying…' : 'Connect & verify'}
                    </Button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="vrs-src-card__desc">Route verified signals to Bybit for execution. Uses a trade-only API key — Verasig never withdraws funds.</div>
                  <div className="vrs-src-card__foot">
                    <span className="vrs-src-meta"><Icon name="clock" size={13} /> ~1 min setup</span>
                    <Button variant="primary" size="sm" iconLeft={<Icon name="plus" size={14} />} onClick={startConfigure}>Configure</Button>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      <Dialog
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        title="Disconnect Bybit?"
        description="Verified signals will stop routing to Bybit immediately."
        icon={<Icon name="trash" size={19} />}
        footer={<>
          <Button variant="ghost" size="sm" onClick={() => setConfirmOpen(false)}>Cancel</Button>
          <Button variant="danger" size="sm" onClick={() => { setConfirmOpen(false); onDisconnect && onDisconnect(); }}>Disconnect Bybit</Button>
        </>}
      >
        Your trade-only API key ({bybit.account}) will be removed from Verasig. Open positions are unaffected — only new signal routing stops. You can reconnect any time.
      </Dialog>
    </div>
  );
}
