import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SettingsView } from './SettingsView.jsx'

const user = {
  firstName: 'Ada',
  lastName: 'Lovelace',
  email: 'ada@example.com',
  plan: 'observer',
  pendingEmail: null,
  cancelAt: null
}

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' }
  })
}

beforeEach(() => {
  globalThis.fetch = vi.fn()
})

describe('SettingsView', () => {
  it('saves profile changes through the backend account API', async () => {
    const updated = { ...user, firstName: 'Grace', lastName: 'Hopper' }
    const onUpdateUser = vi.fn()

    fetch.mockResolvedValueOnce(jsonResponse(updated))

    render(
      <SettingsView
        authToken="jwt-token"
        user={user}
        onUpdateUser={onUpdateUser}
        onToast={() => {}}
      />
    )
    fireEvent.change(screen.getByLabelText(/first name/i), {
      target: { value: ' Grace ' }
    })
    fireEvent.change(screen.getByLabelText(/last name/i), {
      target: { value: '   Hopper  ' }
    })
    fireEvent.click(screen.getAllByRole('button', { name: 'Save' })[0])

    await waitFor(() => {
      expect(onUpdateUser).toHaveBeenCalledWith(updated)
    })
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/user', {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer jwt-token'
      },
      body: JSON.stringify({
        firstName: 'Grace',
        lastName: 'Hopper'
      })
    })
  })

  it('disables save when profile names are invalid', () => {
    const onUpdateUser = vi.fn()
    const onToast = vi.fn()

    render(
      <SettingsView
        authToken="jwt-token"
        user={user}
        onUpdateUser={onUpdateUser}
        onToast={onToast}
      />
    )
    fireEvent.change(screen.getByLabelText(/first name/i), {
      target: { value: 'Ada123' }
    })
    fireEvent.change(screen.getByLabelText(/last name/i), {
      target: { value: 'Lovelace' }
    })

    expect(screen.getAllByRole('button', { name: 'Save' })[0].disabled).toBe(true)
    expect(onUpdateUser).not.toHaveBeenCalled()
    expect(screen.getByText(/may contain only letters/)).toBeTruthy()
  })

  it('disables Resume subscription while the request is in flight', async () => {
    fetch.mockReturnValue(new Promise(() => {}))
    const cancelling = { ...user, plan: 'operator', cancelAt: 'Aug 1, 2026' }

    render(
      <SettingsView
        authToken="jwt-token"
        user={cancelling}
        onUpdateUser={vi.fn()}
        onToast={vi.fn()}
      />
    )
    const resume = screen.getByRole('button', { name: /Resume subscription/i })
    expect(resume.disabled).toBe(false)

    fireEvent.click(resume)

    await waitFor(() =>
      expect(
        screen.getByRole('button', { name: /Resume subscription/i }).disabled
      ).toBe(true)
    )
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('cancels a pending email change through the backend', async () => {
    const pending = { ...user, pendingEmail: 'next@example.com' }
    const onUpdateUser = vi.fn()

    fetch.mockResolvedValueOnce(jsonResponse(user))

    render(
      <SettingsView
        authToken="jwt-token"
        user={pending}
        onUpdateUser={onUpdateUser}
        onToast={() => {}}
      />
    )
    fireEvent.click(screen.getByRole('button', { name: 'Cancel change' }))

    await waitFor(() => {
      expect(onUpdateUser).toHaveBeenCalledWith(user)
    })
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/user/email/cancel', {
      method: 'POST',
      headers: { Authorization: 'Bearer jwt-token' }
    })
  })

  it('surfaces backend validation errors in the toast path', async () => {
    const onUpdateUser = vi.fn()
    const onToast = vi.fn()

    fetch.mockResolvedValueOnce(
      jsonResponse({ error: { message: 'Names are not valid' } }, 422)
    )

    render(
      <SettingsView
        authToken="jwt-token"
        user={user}
        onUpdateUser={onUpdateUser}
        onToast={onToast}
      />
    )
    fireEvent.change(screen.getByLabelText(/first name/i), {
      target: { value: 'Grace' }
    })
    fireEvent.change(screen.getByLabelText(/last name/i), {
      target: { value: 'Hopper' }
    })
    fireEvent.click(screen.getAllByRole('button', { name: 'Save' })[0])

    await waitFor(() => {
      expect(onUpdateUser).not.toHaveBeenCalled()
    })
    expect(onToast).toHaveBeenCalledWith(
      'rejected',
      'Account update failed',
      'Names are not valid'
    )
  })
})
