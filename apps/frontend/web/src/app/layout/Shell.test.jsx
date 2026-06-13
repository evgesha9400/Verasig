import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Shell } from './Shell.jsx'

const user = {
  firstName: 'Mara',
  lastName: 'Voss',
  email: 'mara@northwave.io'
}

describe('Shell user menu', () => {
  it('uses shared menu and theme-toggle semantics', () => {
    const onThemeChange = vi.fn()

    render(
      <Shell
        nav="sources"
        onNavigate={() => {}}
        title="Sources"
        theme="dark"
        onThemeChange={onThemeChange}
        user={user}
        onLogout={() => {}}
      >
        <div />
      </Shell>
    )

    fireEvent.click(screen.getByRole('button', { expanded: false }))
    fireEvent.click(screen.getByRole('radio', { name: 'Light' }))

    expect(screen.getByRole('menu')).toBeTruthy()
    expect(onThemeChange).toHaveBeenCalledWith('light')
  })
})
