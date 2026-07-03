import { act, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { BackfillView } from './BackfillView.jsx'

const feed = {
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
        feed={feed}
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
      streamHandlers.onProgress({
        fetched: 200,
        lastDate: 'Jun 1, 2026',
        phase: 'Checking deleted messages... (200 scanned)'
      })
    })

    expect(screen.getByText('Checking deleted messages... (200 scanned)')).toBeTruthy()

    act(() => {
      streamHandlers.onDone({ fetched: 12, lastDate: 'May 30, 2026' })
    })

    expect(onComplete).toHaveBeenCalledWith({
      fetched: 12,
      lastDate: 'May 30, 2026',
      status: 'succeeded'
    })
  })

  it('keeps the stream open when fetched/lastDate update mid-backfill', async () => {
    const onStart = vi.fn().mockResolvedValue()
    const close = vi.fn()
    const onStream = vi.fn(() => ({ close }))
    const noop = () => {}

    const { rerender } = render(
      <BackfillView
        feed={feed}
        onStart={onStart}
        onStream={onStream}
        onCancel={noop}
        onComplete={noop}
      />
    )

    await waitFor(() => expect(onStart).toHaveBeenCalledTimes(1))
    expect(onStream).toHaveBeenCalledTimes(1)

    rerender(
      <BackfillView
        feed={{ ...feed, fetched: 5000, lastDate: 'Jun 1, 2026' }}
        onStart={onStart}
        onStream={onStream}
        onCancel={noop}
        onComplete={noop}
      />
    )

    expect(close).not.toHaveBeenCalled()
    expect(onStart).toHaveBeenCalledTimes(1)
    expect(onStream).toHaveBeenCalledTimes(1)
  })

  it('seeds the counter at zero for a full re-fetch (wipe & recapture)', () => {
    render(
      <BackfillView
        feed={{ ...feed, fetched: 9000, lastDate: 'Jun 1, 2026' }}
        mode="full"
        onStart={vi.fn().mockResolvedValue()}
        onStream={() => ({ close: vi.fn() })}
        onComplete={() => {}}
      />
    )
    expect(screen.queryByText('9,000')).toBeNull()
    expect(screen.getByText('0')).toBeTruthy()
  })

  it('advances the stage strip from the streamed stage field', async () => {
    const onStart = vi.fn().mockResolvedValue()
    let streamHandlers
    const onStream = vi.fn((_id, handlers) => {
      streamHandlers = handlers
      return { close: vi.fn() }
    })
    render(
      <BackfillView
        feed={feed}
        onStart={onStart}
        onStream={onStream}
        onComplete={() => {}}
      />
    )
    await waitFor(() => expect(onStart).toHaveBeenCalled())

    act(() => {
      streamHandlers.onProgress({
        fetched: 200,
        stage: 'rescan',
        phase: 'Checking deleted messages...'
      })
    })

    expect(screen.getByText('Deletion scan').classList.contains('is-active')).toBe(true)
    expect(screen.getByText('Fetching history').classList.contains('is-done')).toBe(
      true
    )
  })

  it('renders an empty oldest-date placeholder until the backend reports a date', () => {
    render(
      <BackfillView
        feed={feed}
        onStart={vi.fn().mockResolvedValue()}
        onStream={() => ({ close: vi.fn() })}
        onCancel={() => {}}
        onComplete={() => {}}
      />
    )

    expect(screen.getByText('No messages yet')).toBeTruthy()
  })
})
