import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { DistillView } from './DistillView.jsx'

function renderView(overrides = {}) {
  const onStartDistill = vi.fn().mockResolvedValue({ jobId: 'u:7:distill' })
  let streamHandlers
  const onStreamProgress = vi.fn((_chatId, handlers) => {
    streamHandlers = handlers
    return { close: vi.fn() }
  })
  const onGetRules = vi.fn().mockResolvedValue({
    rules: [
      { id: 'r:0', label: 'Has a directional verb', detail: 'LONG/SHORT', match: 94 }
    ]
  })
  const onComplete = vi.fn()
  const onError = vi.fn()
  render(
    <DistillView
      chatId="7"
      onStartDistill={onStartDistill}
      onStreamProgress={onStreamProgress}
      onGetRules={onGetRules}
      onComplete={onComplete}
      onError={onError}
      {...overrides}
    />
  )
  return {
    onStartDistill,
    onStreamProgress,
    onGetRules,
    onComplete,
    onError,
    getHandlers: () => streamHandlers
  }
}

describe('DistillView', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('starts the distill job and renders structured progress', async () => {
    const { onStartDistill, getHandlers } = renderView()
    await waitFor(() => expect(getHandlers()).toBeTruthy())
    expect(onStartDistill).toHaveBeenCalledWith('7')
    act(() =>
      getHandlers().onProgress({
        stage: 'filter_distilling',
        phase: 'Distilling filter rules',
        step: 2,
        totalSteps: 6,
        signalLabels: 5,
        noiseLabels: 2
      })
    )
    expect(screen.getByText('Distilling filter rules')).toBeTruthy()
    expect(screen.getByText('Step 2 of 6')).toBeTruthy()
    expect(screen.getByText('5 signal labels')).toBeTruthy()
    expect(screen.getByText('2 non-signal labels')).toBeTruthy()
  })

  it('advances for legacy phase-only progress payloads', async () => {
    const { getHandlers } = renderView()
    await waitFor(() => expect(getHandlers()).toBeTruthy())
    act(() => getHandlers().onProgress({ phase: 'Extracting structure & tickers' }))
    expect(screen.getByText('Extracting structure & tickers')).toBeTruthy()
    expect(screen.getByText('Step 2 of 6')).toBeTruthy()
  })

  it('shows elapsed time without waiting on wall clock time', async () => {
    vi.useFakeTimers()
    const { getHandlers } = renderView()
    await act(async () => {
      await Promise.resolve()
    })
    expect(getHandlers()).toBeTruthy()
    expect(screen.getByText('Elapsed 0:00')).toBeTruthy()
    act(() => vi.advanceTimersByTime(2000))
    expect(screen.getByText('Elapsed 0:02')).toBeTruthy()
  })

  it('fetches and renders real rules on done, with match as a percentage', async () => {
    const { getHandlers, onGetRules } = renderView()
    await waitFor(() => expect(getHandlers()).toBeTruthy())
    await act(async () => {
      getHandlers().onDone({ rules: 1 })
      await Promise.resolve()
    })
    await waitFor(() => expect(onGetRules).toHaveBeenCalledWith('7'))
    expect(await screen.findByText('Has a directional verb')).toBeTruthy()
    expect(screen.getByText('94%')).toBeTruthy()
  })

  it('recovers rules when the stream errors (job already evicted)', async () => {
    const { getHandlers, onGetRules } = renderView()
    await waitFor(() => expect(getHandlers()).toBeTruthy())
    await act(async () => {
      getHandlers().onError({})
      await Promise.resolve()
    })
    await waitFor(() => expect(onGetRules).toHaveBeenCalledWith('7'))
    expect(await screen.findByText('Has a directional verb')).toBeTruthy()
  })

  it('shows error screen on a named backend error event without calling onGetRules', async () => {
    const { getHandlers, onGetRules } = renderView()
    await waitFor(() => expect(getHandlers()).toBeTruthy())
    await act(async () => {
      getHandlers().onError({ message: 'job exploded' })
      await Promise.resolve()
    })
    expect(await screen.findByText("Distillation didn't complete")).toBeTruthy()
    expect(screen.getByText('job exploded')).toBeTruthy()
    expect(onGetRules).not.toHaveBeenCalled()
  })

  it('shows the last progress phase after a backend error event', async () => {
    const { getHandlers } = renderView()
    await waitFor(() => expect(getHandlers()).toBeTruthy())
    act(() =>
      getHandlers().onProgress({
        stage: 'parser_distilling',
        phase: 'Distilling parser rules',
        step: 4,
        totalSteps: 6,
        signalLabels: 5,
        noiseLabels: 2
      })
    )
    await act(async () => {
      getHandlers().onError({
        message: 'parser distillation failed deterministic validation'
      })
      await Promise.resolve()
    })
    expect(await screen.findByText('Last progress')).toBeTruthy()
    expect(screen.getByText('Distilling parser rules')).toBeTruthy()
  })

  it('retries distillation from the failure screen', async () => {
    const { getHandlers, onStartDistill, onStreamProgress } = renderView()
    await waitFor(() => expect(getHandlers()).toBeTruthy())
    await act(async () => {
      getHandlers().onError({ message: 'job exploded' })
      await Promise.resolve()
    })

    fireEvent.click(await screen.findByRole('button', { name: 'Retry distillation' }))

    await waitFor(() => expect(onStartDistill).toHaveBeenCalledTimes(2))
    expect(onStreamProgress).toHaveBeenCalledTimes(2)
    expect(screen.getByText('Distilling signal rules')).toBeTruthy()
  })

  it('shows error screen when onGetRules resolves an empty ruleset', async () => {
    const { getHandlers } = renderView({
      onGetRules: vi.fn().mockResolvedValue({ rules: [] })
    })
    await waitFor(() => expect(getHandlers()).toBeTruthy())
    await act(async () => {
      getHandlers().onDone()
      await Promise.resolve()
    })
    expect(await screen.findByText("Distillation didn't complete")).toBeTruthy()
  })
})
