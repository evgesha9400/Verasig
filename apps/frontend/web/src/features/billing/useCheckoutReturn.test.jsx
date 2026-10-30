import { act, renderHook } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { getCurrentUser } from '../../shared/api/authApi.js'
import { useCheckoutReturn } from './useCheckoutReturn.js'

vi.mock('../../shared/api/authApi.js', () => ({ getCurrentUser: vi.fn() }))

const free = { plan: 'free', subscriptionStatus: null }
const trader = { plan: 'trader', subscriptionStatus: 'trialing' }

function renderReturn(path) {
  const onUser = vi.fn()
  const onToast = vi.fn()
  const view = renderHook(
    () => {
      useCheckoutReturn('jwt-token', { onUser, onToast })
      return useLocation()
    },
    {
      wrapper: ({ children }) => (
        <MemoryRouter initialEntries={[path]}>{children}</MemoryRouter>
      )
    }
  )
  return { ...view, onUser, onToast }
}

async function advance(ms) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms)
  })
}

beforeEach(() => {
  vi.useFakeTimers()
  getCurrentUser.mockReset()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('useCheckoutReturn', () => {
  it('polls the account until the webhook activates Trader, then announces it', async () => {
    getCurrentUser
      .mockResolvedValueOnce(free)
      .mockResolvedValueOnce(free)
      .mockResolvedValueOnce(trader)
    const { result, onUser, onToast } = renderReturn(
      '/app?checkout=success&session_id=cs_test_1'
    )

    await advance(10_000)

    expect(getCurrentUser).toHaveBeenCalledTimes(3)
    expect(getCurrentUser).toHaveBeenCalledWith('jwt-token')
    expect(onUser).toHaveBeenCalledWith(trader)
    expect(onToast).toHaveBeenCalledWith(
      'verified',
      'Trader activated',
      expect.any(String)
    )
    expect(result.current.search).toBe('')
  })

  it('stops after about ten seconds when the webhook has not landed', async () => {
    getCurrentUser.mockResolvedValue(free)
    const { onUser, onToast } = renderReturn('/app?checkout=success')

    await advance(30_000)

    expect(getCurrentUser.mock.calls.length).toBeGreaterThan(3)
    expect(getCurrentUser.mock.calls.length).toBeLessThanOrEqual(8)
    expect(onUser).not.toHaveBeenCalled()
    expect(onToast).toHaveBeenCalledWith(
      'pending',
      'Payment received',
      expect.any(String)
    )
  })

  it('only clears the query after a cancelled Checkout', async () => {
    const { result, onToast } = renderReturn('/app?checkout=cancelled')

    await advance(10_000)

    expect(result.current.search).toBe('')
    expect(getCurrentUser).not.toHaveBeenCalled()
    expect(onToast).not.toHaveBeenCalled()
  })

  it('does nothing without a checkout query', async () => {
    const { result } = renderReturn('/app?tab=x')

    await advance(10_000)

    expect(result.current.search).toBe('?tab=x')
    expect(getCurrentUser).not.toHaveBeenCalled()
  })

  it('reports a Checkout that could not start after signup', async () => {
    const { result, onToast } = renderReturn('/app?checkout=error')

    await advance(1_000)

    expect(result.current.search).toBe('')
    expect(onToast).toHaveBeenCalledWith(
      'rejected',
      'Checkout unavailable',
      expect.any(String)
    )
    expect(getCurrentUser).not.toHaveBeenCalled()
  })
})
