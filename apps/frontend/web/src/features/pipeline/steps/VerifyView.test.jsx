import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { VerifyView } from './VerifyView.jsx'

const samples = Array.from({ length: 6 }, (_, i) => ({
  id: String(i + 1),
  author: 'Apex',
  date: 'Jun 6',
  time: '08:42',
  text: `msg ${i + 1}`,
  media: null,
  predicted: i % 2 === 0 ? 'signal' : 'noise'
}))

function renderView(overrides = {}) {
  const onGetSamples = vi.fn().mockResolvedValue({ attempt: 1, samples })
  const onSubmit = vi.fn().mockResolvedValue({ passed: true, misclassified: [] })
  const onPass = vi.fn()
  const onStop = vi.fn()
  const onLoop = vi.fn()
  render(
    <VerifyView
      chatId="7"
      onGetSamples={onGetSamples}
      onSubmit={onSubmit}
      onPass={onPass}
      onStop={onStop}
      onLoop={onLoop}
      {...overrides}
    />
  )
  return { onGetSamples, onSubmit, onPass, onStop, onLoop }
}

describe('VerifyView', () => {
  it('loads samples from the backend', async () => {
    const { onGetSamples } = renderView()
    await waitFor(() => expect(onGetSamples).toHaveBeenCalledWith('7'))
    expect(await screen.findByText('msg 1')).toBeTruthy()
  })

  it('submits verdicts and shows the pass screen when the backend passes', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    try {
      const { onSubmit } = renderView()
      await screen.findByText('msg 1')
      // Each swipe sets a 300ms "flying" guard that blocks the next commit, so
      // advance past it between clicks (the real user waits for the animation).
      for (let i = 0; i < 6; i += 1) {
        fireEvent.click(screen.getByRole('button', { name: 'Correct' }))
        act(() => vi.advanceTimersByTime(320))
      }
      fireEvent.click(screen.getByRole('button', { name: /Finish verification/i }))
      await waitFor(() => expect(onSubmit).toHaveBeenCalled())
      expect(onSubmit.mock.calls[0][0]).toBe('7')
      expect(onSubmit.mock.calls[0][1]).toHaveLength(6)
      expect(await screen.findByText('Verification passed')).toBeTruthy()
    } finally {
      vi.useRealTimers()
    }
  })

  it('loops back to labelling when the backend fails verification', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    try {
      const onSubmit = vi
        .fn()
        .mockResolvedValue({ passed: false, misclassified: ['2'] })
      const { onLoop } = renderView({ onSubmit })
      await screen.findByText('msg 1')
      for (let i = 0; i < 6; i += 1) {
        fireEvent.click(screen.getByRole('button', { name: 'Correct' }))
        act(() => vi.advanceTimersByTime(320))
      }
      fireEvent.click(screen.getByRole('button', { name: /Finish verification/i }))
      fireEvent.click(await screen.findByRole('button', { name: /Back to labelling/i }))
      expect(onLoop).toHaveBeenCalled()
    } finally {
      vi.useRealTimers()
    }
  })

  it('shows the error card when onGetSamples rejects', async () => {
    const onGetSamples = vi.fn().mockRejectedValue(new Error('network error'))
    const onError = vi.fn()
    renderView({ onGetSamples, onError })
    expect(await screen.findByText(/Couldn.t load samples/)).toBeTruthy()
    await waitFor(() => expect(onError).toHaveBeenCalled())
  })
})
