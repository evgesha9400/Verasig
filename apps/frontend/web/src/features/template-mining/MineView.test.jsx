import { act, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../shared/api/client.js'
import { MineView } from './MineView.jsx'

const feed = { id: '7', name: 'Pilot Signals', tag: '@pilot' }

describe('MineView', () => {
  it('starts the job, streams progress, and forwards the mined result', async () => {
    const onStart = vi.fn().mockResolvedValue({ jobId: 'user:7:mine' })
    let streamed
    const onStream = vi.fn((id, handlers) => {
      streamed = handlers
      return { close: vi.fn() }
    })
    const onDone = vi.fn()

    render(
      <MineView
        feed={feed}
        onStart={onStart}
        onStream={onStream}
        onDone={onDone}
        onError={vi.fn()}
      />
    )

    await waitFor(() => expect(onStart).toHaveBeenCalledWith('7'))
    await waitFor(() =>
      expect(onStream).toHaveBeenCalledWith('7', expect.any(Object))
    )

    act(() =>
      streamed.onProgress({ stage: 'extracting', count: 128, phase: 'Extracting…' })
    )
    expect(screen.getByText('128')).toBeTruthy()

    const result = { groups: [{ template_key: 'x' }], messages: [] }
    act(() => streamed.onDone(result))
    expect(onDone).toHaveBeenCalledWith(result)
  })

  it('reports a failed start through onError', async () => {
    const onStart = vi.fn().mockRejectedValue(new Error('boom'))
    const onError = vi.fn()

    render(
      <MineView
        feed={feed}
        onStart={onStart}
        onStream={vi.fn()}
        onDone={vi.fn()}
        onError={onError}
      />
    )

    await waitFor(() =>
      expect(onError).toHaveBeenCalledWith({ message: 'boom' })
    )
  })

  it('subscribes to the stream when the job is already running (409)', async () => {
    // A 409 means the job is live (e.g. a StrictMode re-invoke re-POSTs while the
    // first job still runs). The progress stream replays its state, so the view
    // must subscribe anyway instead of hanging with nothing listening.
    const conflict = new ApiError({
      status: 409,
      code: 'JOB_ALREADY_RUNNING',
      message: 'Job is already running'
    })
    const onStart = vi.fn().mockRejectedValue(conflict)
    let streamed
    const onStream = vi.fn((id, handlers) => {
      streamed = handlers
      return { close: vi.fn() }
    })
    const onDone = vi.fn()
    const onError = vi.fn()

    render(
      <MineView
        feed={feed}
        onStart={onStart}
        onStream={onStream}
        onDone={onDone}
        onError={onError}
      />
    )

    await waitFor(() =>
      expect(onStream).toHaveBeenCalledWith('7', expect.any(Object))
    )

    const result = { groups: [{ template_key: 'x' }], messages: [] }
    act(() => streamed.onDone(result))
    expect(onDone).toHaveBeenCalledWith(result)
    expect(onError).not.toHaveBeenCalled()
  })
})
