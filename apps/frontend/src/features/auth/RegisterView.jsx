import { useState } from 'react'
import { Button, Input } from '../../design-system/index.js'
import { Icon } from '../../design-system/index.js'
import { BrandPanel } from './BrandPanel.jsx'
import './auth.css'

export function RegisterView({ onRegister, onLogin }) {
  const [name, setName] = useState('Mara Voss')
  const [email, setEmail] = useState('mara@northwave.io')
  const [password, setPassword] = useState('verasig-demo-2026')

  function handleSubmit(e) {
    e.preventDefault()
    onRegister()
  }

  return (
    <div className="auth-wrap">
      <BrandPanel />
      <main className="auth-main">
        <div className="auth-form-wrap">
          <a className="auth-form-wrap__logo" href="#">
            <Icon name="sources" size={24} />Verasig<span style={{ color: 'var(--signal-500)' }}>.</span>
          </a>
          <div className="auth-eyebrow">Get started</div>
          <h1 className="auth-title">Create your account</h1>
          <p className="auth-lede">Connect a source and verify your first channel in a couple of minutes.</p>
          <form className="auth-form" onSubmit={handleSubmit}>
            <Input label="Full name" required value={name} onChange={e => setName(e.target.value)}
              iconLeft={<Icon name="users" size={16} />} placeholder="e.g. Mara Voss" />
            <Input label="Email" type="email" required value={email} onChange={e => setEmail(e.target.value)}
              iconLeft={<Icon name="users" size={16} />} placeholder="you@company.com" />
            <Input label="Password" type="password" required value={password} onChange={e => setPassword(e.target.value)}
              iconLeft={<Icon name="lock" size={16} />} placeholder="••••••••" hint="At least 10 characters." />
            <Button type="submit" variant="primary" fullWidth size="lg"
              iconRight={<Icon name="arrowRight" size={16} />}>Create account</Button>
          </form>
          <p className="auth-legal">
            By creating an account you agree to our <a href="#">Terms</a> and <a href="#">Privacy Policy</a>.
          </p>
          <div className="auth-switch">
            Already have an account?{' '}
            <button type="button" className="auth-link" onClick={onLogin}>Log in</button>
          </div>
        </div>
      </main>
    </div>
  )
}
