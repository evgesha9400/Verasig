import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { BacktestView } from './BacktestView.jsx'

describe('BacktestView', () => {
  // A legitimate score of 0 must render as 0, not be treated as missing and
  // replaced by the demo default.
  it('renders a zero score instead of falling back to the demo default', () => {
    const onComplete = vi.fn()
    render(
      <BacktestView
        chat={{ name: 'Zero Feed', score: 0, winRate: 0, pnl: 0 }}
        skipRun
        onComplete={onComplete}
      />
    )
    fireEvent.click(screen.getByRole('button', { name: /Finish/i }))
    expect(onComplete).toHaveBeenCalledWith({ score: 0, winRate: 0, pnl: 0 })
  })
})
