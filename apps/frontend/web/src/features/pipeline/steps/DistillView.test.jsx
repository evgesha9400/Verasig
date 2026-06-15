import { act, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
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
  render(
    <DistillView
      chatId="7"
      onStartDistill={onStartDistill}
      onStreamProgress={onStreamProgress}
      onGetRules={onGetRules}
      onComplete={onComplete}
      {...overrides}
    />
  )
  return {
    onStartDistill,
    onStreamProgress,
    onGetRules,
    onComplete,
    getHandlers: () => streamHandlers
  }
}

describe('DistillView', () => {
  it('starts the distill job and streams phases', async () => {
    const { onStartDistill, getHandlers } = renderView()
    await waitFor(() => expect(getHandlers()).toBeTruthy())
    expect(onStartDistill).toHaveBeenCalledWith('7')
    act(() => getHandlers().onProgress({ phase: 'Extracting structure & tickers' }))
    expect(screen.getByText('Extracting structure & tickers')).toBeTruthy()
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
})
