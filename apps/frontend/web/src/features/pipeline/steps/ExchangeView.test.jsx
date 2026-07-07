import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ExchangeView } from './ExchangeView.jsx'

describe('ExchangeView', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  // The verify uses a setTimeout; unmounting mid-verify must clear it so its
  // callback never fires a setState (or onConnected) after the view is gone.
  it('does not fire onConnected after unmount (verify timer cleared)', () => {
    const onConnected = vi.fn()
    const { unmount } = render(
      <ExchangeView onConnected={onConnected} bybitConnected={false} />
    )

    fireEvent.click(screen.getByRole('button', { name: /Connect Bybit & verify/i }))
    unmount()
    act(() => vi.advanceTimersByTime(3000))

    expect(onConnected).not.toHaveBeenCalled()
  })
})
