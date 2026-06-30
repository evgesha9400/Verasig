import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
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
})
