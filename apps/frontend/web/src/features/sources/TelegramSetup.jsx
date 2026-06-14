/* Verasig prototype — Telegram connect flow: credentials -> verification code */
import { useState } from 'react'
import { Input, Button, Banner, OTPInput } from '@verasig/design-system'
import { Icon } from '@verasig/design-system'

async function noop() {}

function errorMessage(error) {
  return error?.message || 'Telegram connection failed. Try again.'
}

export function TelegramSetup({
  onConnected,
  onCancel,
  onConnect = noop,
  onVerify = noop
}) {
  const [phase, setPhase] = useState('creds') // creds | sending | code | verifying
  const [apiId, setApiId] = useState('')
  const [apiHash, setApiHash] = useState('')
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [twoFactorPassword, setTwoFactorPassword] = useState('')
  const [needsPassword, setNeedsPassword] = useState(false)
  const [err, setErr] = useState(null)

  const credsValid =
    apiId.trim().length >= 5 &&
    apiHash.trim().length >= 16 &&
    /^\+?[0-9\s]{8,}$/.test(phone.trim())

  async function sendCode() {
    if (!credsValid) {
      setErr('Check your API ID, API Hash and phone number.')
      return
    }
    setErr(null)
    setPhase('sending')

    try {
      await onConnect({
        apiId: Number(apiId.trim()),
        apiHash: apiHash.trim(),
        phone: phone.trim()
      })
      setNeedsPassword(false)
      setTwoFactorPassword('')
      setPhase('code')
    } catch (error) {
      setErr(errorMessage(error))
      setPhase('creds')
    }
  }

  const codeComplete = code.length === 5
  async function verify() {
    if (!codeComplete) return
    setPhase('verifying')

    try {
      if (needsPassword) {
        await onVerify(code, twoFactorPassword)
      } else {
        await onVerify(code)
      }
      await onConnected()
    } catch (error) {
      if (error?.code === 'TELEGRAM_TWO_FACTOR_REQUIRED') {
        setNeedsPassword(true)
        setErr('Two-factor password required. Enter your Telegram password.')
      } else {
        setErr(errorMessage(error))
      }
      setPhase('code')
    }
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
                <a
                  className="vrs-link"
                  href="https://core.telegram.org/api/obtaining_api_id"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  core.telegram.org/api/obtaining_api_id
                </a>
                . We request a login code to start; two-step password is requested only
                if your account uses it.
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
              <OTPInput
                length={5}
                value={code}
                onChange={setCode}
                disabled={phase === 'verifying'}
                className="vrs-code"
              />
              {needsPassword && (
                <Input
                  label="Telegram password"
                  type="password"
                  placeholder="Telegram two-factor password"
                  value={twoFactorPassword}
                  onChange={(e) => setTwoFactorPassword(e.target.value)}
                  disabled={phase === 'verifying'}
                  required={needsPassword}
                />
              )}
              <div className="vrs-help" style={{ textAlign: 'center' }}>
                Demo: enter any 5 digits. Didn’t get it?{' '}
                <button type="button" className="vrs-link" onClick={sendCode}>
                  Resend code
                </button>{' '}
                ·{' '}
                <button
                  type="button"
                  className="vrs-link"
                  onClick={() => {
                    setErr(null)
                    setNeedsPassword(false)
                    setTwoFactorPassword('')
                    setCode('')
                    setPhase('creds')
                  }}
                >
                  Change number
                </button>
              </div>
              <div className="vrs-form__actions" style={{ justifyContent: 'center' }}>
                <Button
                  variant="primary"
                  size="lg"
                  disabled={
                    (!codeComplete || (needsPassword && !twoFactorPassword)) &&
                    phase !== 'verifying'
                  }
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
