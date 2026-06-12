/* Verasig prototype — Telegram connect flow: credentials -> verification code */
import { useState, useRef } from 'react'
import { Input, Button, Banner } from '@verasig/design-system'
import { Icon } from '@verasig/design-system'

export function TelegramSetup({ onConnected, onCancel }) {
  const [phase, setPhase] = useState('creds') // creds | sending | code | verifying
  // Prototype: pre-filled with valid demo credentials so the flow is walkable without real Telegram keys.
  const [apiId, setApiId] = useState('2040315')
  const [apiHash, setApiHash] = useState('a1b2c3d4e5f6079a8b7c6d5e4f30219a')
  const [phone, setPhone] = useState('+44 7700 900142')
  const [code, setCode] = useState(['', '', '', '', ''])
  const [err, setErr] = useState(null)
  const codeRefs = useRef([])

  const credsValid =
    apiId.trim().length >= 5 &&
    apiHash.trim().length >= 16 &&
    /^\+?[0-9\s]{8,}$/.test(phone.trim())

  function sendCode() {
    if (!credsValid) {
      setErr('Check your API ID, API Hash and phone number.')
      return
    }
    setErr(null)
    setPhase('sending')
    setTimeout(() => {
      setPhase('code')
      setTimeout(() => codeRefs.current[0] && codeRefs.current[0].focus(), 60)
    }, 1400)
  }

  function setDigit(i, v) {
    v = v.replace(/[^0-9]/g, '').slice(-1)
    const next = [...code]
    next[i] = v
    setCode(next)
    if (v && i < 4) codeRefs.current[i + 1] && codeRefs.current[i + 1].focus()
  }
  function onCodeKey(i, e) {
    if (e.key === 'Backspace' && !code[i] && i > 0)
      codeRefs.current[i - 1] && codeRefs.current[i - 1].focus()
  }
  const codeComplete = code.every((d) => d !== '')
  function verify() {
    if (!codeComplete) return
    setPhase('verifying')
    setTimeout(() => onConnected(), 1500)
  }

  return (
    <div className="vrs-page vrs-page--center">
      <div className="vrs-setup vrs-fade-in">
        <div className="vrs-setup__hero">
          <span
            className="vrs-src-logo"
            style={{
              width: 52,
              height: 52,
              background: 'color-mix(in srgb, #2AABEE 22%, transparent)',
              color: '#3CB4F0'
            }}
          >
            <Icon name="telegram" size={30} fill />
          </span>
          <div>
            <div className="vrs-setup__title">Connect Telegram</div>
            <div className="vrs-setup__sub">
              Verasig uses your Telegram API credentials to read channel history. Keys
              are encrypted at rest.
            </div>
          </div>
        </div>

        {(phase === 'creds' || phase === 'sending') && (
          <>
            {err && (
              <Banner tone="rejected" title="Couldn’t continue">
                {err}
              </Banner>
            )}
            <div className="vrs-form">
              <Input
                label="API ID"
                mono
                placeholder="2040315"
                value={apiId}
                onChange={(e) => setApiId(e.target.value)}
                disabled={phase === 'sending'}
                required
              />
              <Input
                label="API Hash"
                mono
                placeholder="a1b2c3d4e5f6079a8b7c6d5e4f30219a"
                value={apiHash}
                onChange={(e) => setApiHash(e.target.value)}
                disabled={phase === 'sending'}
                iconLeft={<Icon name="key" size={15} />}
                required
              />
              <Input
                label="Phone number"
                mono
                placeholder="+44 7700 900142"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                disabled={phase === 'sending'}
                iconLeft={<Icon name="telegram" size={15} />}
                required
              />
              <div className="vrs-help">
                Get your credentials from{' '}
                <span className="vrs-link">
                  my.telegram.org → API development tools
                </span>
                . We request a login code, never your password.
              </div>
              <div className="vrs-form__actions">
                <Button variant="ghost" onClick={onCancel}>
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  loading={phase === 'sending'}
                  onClick={sendCode}
                  iconRight={
                    phase === 'sending' ? null : <Icon name="arrowRight" size={15} />
                  }
                >
                  {phase === 'sending' ? 'Sending code…' : 'Send login code'}
                </Button>
              </div>
            </div>
          </>
        )}

        {(phase === 'code' || phase === 'verifying') && (
          <>
            <Banner tone="info" title="Code sent">
              We sent a 5-digit login code to{' '}
              <span className="vrs-mono" style={{ color: 'var(--text-strong)' }}>
                {phone || '+44 •••• •••142'}
              </span>{' '}
              on Telegram. Enter it below.
            </Banner>
            <div className="vrs-form">
              <div className="vrs-code">
                {code.map((d, i) => (
                  <input
                    key={i}
                    ref={(el) => (codeRefs.current[i] = el)}
                    value={d}
                    inputMode="numeric"
                    className={d ? 'is-filled' : ''}
                    disabled={phase === 'verifying'}
                    onChange={(e) => setDigit(i, e.target.value)}
                    onKeyDown={(e) => onCodeKey(i, e)}
                  />
                ))}
              </div>
              <div className="vrs-help" style={{ textAlign: 'center' }}>
                Demo: enter any 5 digits. Didn’t get it?{' '}
                <span className="vrs-link">Resend code</span> ·{' '}
                <span className="vrs-link" onClick={() => setPhase('creds')}>
                  Change number
                </span>
              </div>
              <div className="vrs-form__actions" style={{ justifyContent: 'center' }}>
                <Button
                  variant="primary"
                  size="lg"
                  disabled={!codeComplete && phase !== 'verifying'}
                  loading={phase === 'verifying'}
                  onClick={verify}
                  iconLeft={
                    phase === 'verifying' ? null : <Icon name="check" size={16} />
                  }
                >
                  {phase === 'verifying' ? 'Verifying…' : 'Verify & connect'}
                </Button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
