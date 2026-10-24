import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ExchangesView } from './ExchangesView.jsx'

function fillKeys() {
  fireEvent.click(screen.getByRole('button', { name: /Configure/i }))
  fireEvent.change(screen.getByLabelText('API Key'), {
    target: { value: ' J7n2Kp9XvR4mQ1wL ' }
  })
  fireEvent.change(screen.getByLabelText('API Secret'), {
    target: { value: 'secret-secret-secret' }
  })
  fireEvent.click(screen.getByRole('button', { name: /Connect & verify/i }))
}

describe('ExchangesView', () => {
  it('awaits onConnect with the trimmed key pair and closes the form', async () => {
    const onConnect = vi.fn().mockResolvedValue()
    render(<ExchangesView bybitConnected={false} onConnect={onConnect} />)

    fillKeys()

    expect(onConnect).toHaveBeenCalledWith({
      apiKey: 'J7n2Kp9XvR4mQ1wL',
      secret: 'secret-secret-secret'
    })
    await waitFor(() => expect(screen.queryByLabelText('API Key')).toBeNull())
  })

  it('keeps the form open and shows the server error when connect fails', async () => {
    const onConnect = vi.fn().mockRejectedValue(new Error('Exchange keys are invalid'))
    render(<ExchangesView bybitConnected={false} onConnect={onConnect} />)

    fillKeys()

    expect(await screen.findByText('Exchange keys are invalid')).toBeTruthy()
    expect(screen.getByLabelText('API Key')).toBeTruthy()
  })

  it('shows the connected account returned by the server', () => {
    render(<ExchangesView bybitConnected bybitAccount="AAAA…ZZ" />)

    expect(screen.getByText('AAAA…ZZ', { exact: false })).toBeTruthy()
  })
})
