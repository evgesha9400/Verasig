import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { TelegramSetup } from './TelegramSetup.jsx'

describe('TelegramSetup', () => {
  function fillCredentials() {
    fireEvent.change(screen.getByLabelText('API ID'), {
      target: { value: '2040315' }
    })
    fireEvent.change(screen.getByLabelText('API Hash'), {
      target: { value: 'a1b2c3d4e5f6079a8b7c6d5e4f30219a' }
    })
    fireEvent.change(screen.getByLabelText('Phone number'), {
      target: { value: '+44 7700 900142' }
    })
  }

  it('captures login code digits through the shared OTP input', async () => {
    render(<TelegramSetup onConnected={() => {}} onCancel={() => {}} />)
    fillCredentials()

    fireEvent.click(screen.getByRole('button', { name: /send login code/i }))

    await waitFor(
      () => {
        expect(screen.getByLabelText('Digit 1')).toBeTruthy()
      },
      { timeout: 1800 }
    )

    fireEvent.change(screen.getByLabelText('Digit 1'), { target: { value: '1' } })
    fireEvent.change(screen.getByLabelText('Digit 2'), { target: { value: '2' } })

    expect(screen.getByLabelText('Digit 1').value).toBe('1')
    expect(screen.getByLabelText('Digit 2').value).toBe('2')
  })

  it('connects after any five digits are entered', async () => {
    const onConnected = vi.fn()
    render(<TelegramSetup onConnected={onConnected} onCancel={() => {}} />)
    fillCredentials()

    fireEvent.click(screen.getByRole('button', { name: /send login code/i }))

    await waitFor(() => expect(screen.getByLabelText('Digit 1')).toBeTruthy(), {
      timeout: 1800
    })

    for (let i = 1; i <= 5; i += 1) {
      fireEvent.change(screen.getByLabelText(`Digit ${i}`), {
        target: { value: String(i) }
      })
    }

    fireEvent.click(screen.getByRole('button', { name: /verify & connect/i }))

    await waitFor(() => expect(onConnected).toHaveBeenCalledOnce(), { timeout: 1800 })
  })

  it('resends the code without leaving the code phase or unmounting the OTP', async () => {
    const onConnect = vi.fn().mockResolvedValue()
    render(
      <TelegramSetup onConnected={() => {}} onCancel={() => {}} onConnect={onConnect} />
    )
    fillCredentials()
    fireEvent.click(screen.getByRole('button', { name: /send login code/i }))

    await waitFor(() => expect(screen.getByLabelText('Digit 1')).toBeTruthy(), {
      timeout: 1800
    })
    fireEvent.change(screen.getByLabelText('Digit 1'), { target: { value: '1' } })
    onConnect.mockClear()

    fireEvent.click(screen.getByText('Resend code'))

    // Still on the code phase: OTP stays mounted, the creds form never returns.
    expect(screen.getByLabelText('Digit 1')).toBeTruthy()
    expect(screen.getByLabelText('Digit 1').value).toBe('1')
    expect(screen.queryByLabelText('API ID')).toBeNull()
    await waitFor(() => expect(onConnect).toHaveBeenCalledTimes(1))
  })

  it('shows a verification failure in the code phase', async () => {
    const onVerify = vi.fn().mockRejectedValueOnce(new Error('Invalid login code'))
    render(
      <TelegramSetup onConnected={() => {}} onCancel={() => {}} onVerify={onVerify} />
    )
    fillCredentials()
    fireEvent.click(screen.getByRole('button', { name: /send login code/i }))
    await waitFor(() => expect(screen.getByLabelText('Digit 1')).toBeTruthy(), {
      timeout: 1800
    })
    for (let i = 1; i <= 5; i += 1) {
      fireEvent.change(screen.getByLabelText(`Digit ${i}`), {
        target: { value: String(i) }
      })
    }

    fireEvent.click(screen.getByRole('button', { name: /verify & connect/i }))

    expect(await screen.findByText('Invalid login code')).toBeTruthy()
    expect(screen.getByLabelText('Digit 1')).toBeTruthy()
  })

  it('requests Telegram two-factor password when the server asks for it', async () => {
    const onVerify = vi
      .fn()
      .mockRejectedValueOnce(
        Object.assign(new Error('Two-factor password required'), {
          code: 'TELEGRAM_TWO_FACTOR_REQUIRED'
        })
      )
      .mockResolvedValueOnce()
    const onConnected = vi.fn()

    render(
      <TelegramSetup
        onConnected={onConnected}
        onCancel={() => {}}
        onVerify={onVerify}
      />
    )
    fillCredentials()

    fireEvent.click(screen.getByRole('button', { name: /send login code/i }))

    await waitFor(() => expect(screen.getByLabelText('Digit 1')).toBeTruthy(), {
      timeout: 1800
    })

    for (let i = 1; i <= 5; i += 1) {
      fireEvent.change(screen.getByLabelText(`Digit ${i}`), {
        target: { value: String(i) }
      })
    }

    fireEvent.click(screen.getByRole('button', { name: /verify & connect/i }))

    await waitFor(() => expect(screen.getByLabelText('Telegram password')).toBeTruthy())

    fireEvent.change(screen.getByLabelText('Telegram password'), {
      target: { value: 'two-factor-password' }
    })
    fireEvent.click(screen.getByRole('button', { name: /verify & connect/i }))

    await waitFor(() => expect(onConnected).toHaveBeenCalledOnce())

    expect(onVerify).toHaveBeenCalledTimes(2)
    expect(onVerify).toHaveBeenNthCalledWith(1, '12345')
    expect(onVerify).toHaveBeenNthCalledWith(2, '12345', 'two-factor-password')
  })
})
