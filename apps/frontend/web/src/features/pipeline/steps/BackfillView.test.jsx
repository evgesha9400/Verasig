import { act, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { BackfillView } from './BackfillView.jsx'

const chat = {
  id: '7',
  name: 'Pilot Signals',
  tag: '@pilot',
  fetched: 0,
  lastDate: null
}

describe('BackfillView', () => {
  it('starts a backend backfill and renders streamed progress', async () => {
    const onStart = vi.fn().mockResolvedValue()
    const onComplete = vi.fn()
    const close = vi.fn()
    let streamHandlers

    const onStream = vi.fn((_chatId, handlers) => {
      streamHandlers = handlers
      return { close }
    })

    render(
      <BackfillView
        chat={chat}
        onStart={onStart}
        onStream={onStream}
        onCancel={() => {}}
        onComplete={onComplete}
      />
    )

    await waitFor(() => {
      expect(onStart).toHaveBeenCalledWith('7')
    })
    expect(onStream).toHaveBeenCalledWith('7', expect.any(Object))

    act(() => {
      streamHandlers.onProgress({
        fetched: 5,
        lastDate: 'Jun 1, 2026',
        phase: 'Reading channel history...'
      })
    })

    expect(screen.getByText('5')).toBeTruthy()
    expect(screen.getByText('Jun 1, 2026')).toBeTruthy()
    expect(screen.getByText('Reading channel history...')).toBeTruthy()

    act(() => {
      streamHandlers.onDone({ fetched: 12 })
    })

    expect(onComplete).toHaveBeenCalledWith(12)
  })
})
