import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Shell } from './Shell.jsx'

const user = {
  firstName: 'Mara',
  lastName: 'Voss',
  email: 'mara@northwave.io'
}

describe('Shell user menu', () => {
  it('uses shared menu semantics', () => {
    const onLogout = vi.fn()

    render(
      <Shell
        nav="sources"
        onNavigate={() => {}}
        title="Sources"
        user={user}
        onLogout={onLogout}
      >
        <div />
      </Shell>
    )

    fireEvent.click(screen.getByRole('button', { expanded: false }))
    expect(screen.getByRole('menu')).toBeTruthy()

    fireEvent.click(screen.getByRole('menuitem', { name: 'Log out' }))
    expect(onLogout).toHaveBeenCalledOnce()
  })
})
