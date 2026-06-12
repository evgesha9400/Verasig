import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { TelegramSetup } from './TelegramSetup.jsx'

describe('TelegramSetup', () => {
  it('captures login code digits through the shared OTP input', async () => {
    render(<TelegramSetup onConnected={() => {}} onCancel={() => {}} />)

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
})
