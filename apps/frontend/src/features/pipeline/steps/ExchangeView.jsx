import { useState } from 'react'
import { Button, Input, Banner, Badge } from '@verasig/design-system'
import { Icon } from '@verasig/design-system'
import { EXCHANGES } from '../../../data/seed.js'

/* Verasig prototype — Exchange select + in-place API configuration.
   Connection truth is the app-level `bybitConnected` (single source of truth);
   this view only holds ephemeral form state. */
export function ExchangeView({ onConnected, bybitConnected }) {
  const [selected, setSelected] = useState('bybit')
  const [reconfiguringId, setReconfiguringId] = useState(null) // a connected exchange being re-keyed in place
  const [connectingId, setConnectingId] = useState(null) // verify in progress
  const [key, setKey] = useState('J7n2Kp9XvR4mQ1wL')
  const [secret, setSecret] = useState('x9Tt3FqLm2Vb8RkD5cWnA1pZ')
  const valid = key.trim().length >= 12 && secret.trim().length >= 12
  const selectedDest = EXCHANGES.find((d) => d.id === selected)
  // Only Bybit exists today; its connection state is owned by the app, not duplicated here.
  const isConnectedId = (id) => id === 'bybit' && bybitConnected
  const isConnected = isConnectedId(selected)

  function selectExchange(id) {
    if (connectingId) return
    setSelected(id)
    setReconfiguringId(null)
  }

  function startReconfigure(id) {
    if (connectingId) return
    setSelected(id)
    setReconfiguringId(id)
    setKey('')
    setSecret('')
  }

  function cancelConfig() {
    if (connectingId) return
    setReconfiguringId(null)
    setKey('')
    setSecret('')
  }

  function submitConfig(id) {
    if (!valid || connectingId) return
    const wasConnected = isConnectedId(id)
    setConnectingId(id)
    setTimeout(() => {
      setConnectingId(null)
      if (wasConnected) {
        // reconfigured in place — collapse, stay on the chooser (truth already true)
        setReconfiguringId(null)
        setKey('')
        setSecret('')
      } else {
        onConnected(id) // flips app-level bybitConnected + advances
      }
    }, 1700)
  }

  return (
    <div className="vrs-page vrs-page--center vrs-fade-in">
      <div className="vrs-setup__hero" style={{ alignItems: 'flex-start' }}>
        <div>
          <div className="vrs-setup__title" style={{ fontSize: 'var(--text-xl)' }}>
            Choose an exchange
          </div>
          <div className="vrs-setup__sub">
            Verified signals are forwarded to your exchange to execute. Pick where
            Verasig should route them.
          </div>
        </div>
      </div>
      <div className="vrs-opt-grid">
        {EXCHANGES.map((d) => {
          const dConnected = isConnectedId(d.id)
          const isReconfig = reconfiguringId === d.id
          const dConnecting = connectingId === d.id
          // Config is shown in place when an unconfigured exchange is selected, or a connected one is being reconfigured.
          const dOpen =
            d.status === 'available' &&
            (isReconfig || (selected === d.id && !dConnected))
          return (
            <div
              key={d.id}
              className={`vrs-opt ${selected === d.id ? 'is-selected' : ''} ${d.status === 'soon' ? 'is-soon' : ''}`}
              onClick={() => d.status === 'available' && selectExchange(d.id)}
            >
              <span className="vrs-opt__radio" />
              <span
                className="vrs-src-logo"
                style={{
                  width: 40,
                  height: 40,
                  background: `color-mix(in srgb, ${d.brand} 18%, transparent)`,
                  color: d.brand
                }}
              >
                <Icon name={d.id} size={22} fill />
              </span>
              <div className="vrs-opt__body">
                <div className="vrs-opt__head">
                  <div style={{ flex: 1 }}>
                    <div className="vrs-opt__title">
                      {d.name}
                      {d.status === 'soon' && (
                        <span className="vrs-soon-tag">Soon</span>
                      )}
                      {dConnected && (
                        <Badge tone="verified" dot>
                          Connected
                        </Badge>
                      )}
                      {!dConnected && d.status === 'available' && (
                        <Badge tone="pending">Not configured</Badge>
                      )}
                    </div>
                    <div className="vrs-opt__desc">
                      {dConnected && d.account ? (
                        <span className="vrs-mono">{d.account}</span>
                      ) : (
                        d.kind
                      )}
                    </div>
                  </div>
                  {dConnected && d.status === 'available' && !isReconfig && (
                    <button
                      type="button"
                      className="vrs-link vrs-opt__action"
                      onClick={(e) => {
                        e.stopPropagation()
                        startReconfigure(d.id)
                      }}
                    >
                      Reconfigure
                    </button>
                  )}
                </div>
                {dOpen && (
                  <div className="vrs-opt__config" onClick={(e) => e.stopPropagation()}>
                    {dConnecting ? (
                      <Banner tone="info" title="Verifying API credentials…">
                        Checking permissions and placing a zero-value test order.
                      </Banner>
                    ) : (
                      <Banner tone="pending" title="Use a trade-only key">
                        Create an API key with trade permission in {d.name} → API
                        Management. Disable withdrawal — Verasig only needs read +
                        trade.
                      </Banner>
                    )}
                    <Input
                      label="API Key"
                      mono
                      placeholder="J7n2Kp9XvR4mQ1wL"
                      value={key}
                      onChange={(e) => setKey(e.target.value)}
                      disabled={dConnecting}
                      iconLeft={<Icon name="key" size={15} />}
                      required
                    />
                    <Input
                      label="API Secret"
                      mono
                      placeholder="••••••••••••••••••••••••"
                      value={secret}
                      onChange={(e) => setSecret(e.target.value)}
                      disabled={dConnecting}
                      iconLeft={<Icon name="lock" size={15} />}
                      required
                      type="password"
                    />
                    <div className="vrs-row-between">
                      {isReconfig ? (
                        <Button
                          variant="ghost"
                          onClick={cancelConfig}
                          disabled={dConnecting}
                        >
                          Cancel
                        </Button>
                      ) : (
                        <span />
                      )}
                      <Button
                        variant="primary"
                        loading={dConnecting}
                        disabled={!valid && !dConnecting}
                        onClick={() => submitConfig(d.id)}
                        iconLeft={dConnecting ? null : <Icon name="check" size={16} />}
                      >
                        {dConnecting
                          ? 'Verifying…'
                          : isReconfig
                            ? 'Save & verify'
                            : `Connect ${d.name} & verify`}
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
      <div className="vrs-form__actions">
        {isConnected && reconfiguringId !== selected && (
          <Button
            variant="primary"
            size="lg"
            iconRight={<Icon name="arrowRight" size={16} />}
            onClick={() => onConnected(selected)}
          >
            Use {selectedDest.name} &amp; continue
          </Button>
        )}
      </div>
    </div>
  )
}
