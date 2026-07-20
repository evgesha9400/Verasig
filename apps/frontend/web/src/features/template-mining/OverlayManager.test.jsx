import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { OverlayManager } from './OverlayManager.jsx'

const OVERLAY = {
  instrumentAliases: { АПТ: 'APTUSDT' },
  directionTokens: { '🚀': 'BUY' },
  rejectPhrases: ['giveaway'],
  templateThresholds: {}
}

describe('OverlayManager', () => {
  it('lists current overlay entries', () => {
    render(<OverlayManager overlay={OVERLAY} onSave={vi.fn()} />)
    expect(screen.getByText('APTUSDT')).toBeTruthy()
    expect(screen.getByText('giveaway')).toBeTruthy()
  })

  it('removing a reject phrase saves the overlay without it', async () => {
    const user = userEvent.setup()
    const onSave = vi.fn()
    render(<OverlayManager overlay={OVERLAY} onSave={onSave} />)
    await user.click(
      screen.getByRole('button', { name: /Remove reject phrase giveaway/i })
    )
    expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ rejectPhrases: [] }))
  })

  it('adding a reject phrase saves the overlay with it', async () => {
    const user = userEvent.setup()
    const onSave = vi.fn()
    render(<OverlayManager overlay={OVERLAY} onSave={onSave} />)
    await user.type(screen.getByPlaceholderText(/Add reject phrase/i), 'promo')
    await user.click(screen.getByRole('button', { name: /^Add reject phrase$/i }))
    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({ rejectPhrases: ['giveaway', 'promo'] })
    )
  })

  it('renders duplicate reject phrases only once (stable, deduped keys)', () => {
    render(
      <OverlayManager
        overlay={{ ...OVERLAY, rejectPhrases: ['giveaway', 'giveaway'] }}
        onSave={vi.fn()}
      />
    )
    expect(
      screen.getAllByRole('button', { name: /Remove reject phrase giveaway/i })
    ).toHaveLength(1)
  })

  it('does not re-add an existing reject phrase', async () => {
    const user = userEvent.setup()
    const onSave = vi.fn()
    render(<OverlayManager overlay={OVERLAY} onSave={onSave} />)
    await user.type(screen.getByPlaceholderText(/Add reject phrase/i), 'giveaway')
    await user.click(screen.getByRole('button', { name: /^Add reject phrase$/i }))
    expect(onSave).not.toHaveBeenCalled()
  })

  it('retains an edited phrase when save fails and permits retry', async () => {
    const user = userEvent.setup()
    const onSave = vi
      .fn()
      .mockRejectedValueOnce(new Error('Overlay unavailable.'))
      .mockResolvedValueOnce()
    const { rerender } = render(<OverlayManager overlay={OVERLAY} onSave={onSave} />)
    const input = screen.getByPlaceholderText(/Add reject phrase/i)
    await user.type(input, 'promo')
    await user.click(screen.getByRole('button', { name: /^Add reject phrase$/i }))
    rerender(
      <OverlayManager overlay={OVERLAY} onSave={onSave} error="Overlay unavailable." />
    )

    expect((await screen.findByRole('alert')).textContent).toContain(
      'Overlay unavailable.'
    )
    expect(input.value).toBe('promo')

    await user.click(screen.getByRole('button', { name: /^Add reject phrase$/i }))
    await waitFor(() => expect(onSave).toHaveBeenCalledTimes(2))
  })

  it('disables every overlay mutation while a save is pending', () => {
    render(<OverlayManager overlay={OVERLAY} onSave={vi.fn()} pending />)

    expect(screen.getByRole('button', { name: /^Add alias$/i }).disabled).toBe(true)
    expect(screen.getByRole('button', { name: /^Add token$/i }).disabled).toBe(true)
    expect(screen.getByRole('button', { name: /^Add reject phrase$/i }).disabled).toBe(
      true
    )
    expect(
      screen.getByRole('button', { name: /Remove reject phrase giveaway/i }).disabled
    ).toBe(true)
  })
})
