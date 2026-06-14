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
