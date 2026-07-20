import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { SignalsView } from './SignalsView.jsx'

const feeds = [
  {
    id: '7',
    name: 'Pilot Signals',
    tag: '@pilot',
    initials: 'PS',
    tint: '#5197ff',
    source: 'telegram',
    status: 'verified'
  },
  {
    id: '8',
    name: 'Whale Room',
    tag: '@whale',
    initials: 'WR',
    tint: '#38bdf8',
    source: 'telegram',
    status: 'analyzed'
  }
]

const btcSignal = {
  id: 'sig-1',
  feedId: '7',
  feedName: 'Pilot Signals',
  feedTag: '@pilot',
  feedInitials: 'PS',
  feedTint: '#5197ff',
  source: 'telegram',
  side: 'LONG',
  symbol: 'BTCUSDT',
  status: 'untested',
  outcome: null,
  pnl: null,
  date: 'Jun 6',
  time: '12:00',
  entry: '100',
  stop: '95',
  tp: ['110'],
  text: 'BTC long entry',
  deleted: false,
  cancelled: false,
  mods: [],
  effective: { entry: '100', stop: '95', tp: ['110'] }
}

const ethSignal = {
  ...btcSignal,
  id: 'sig-2',
  feedId: '8',
  feedName: 'Whale Room',
  feedTag: '@whale',
  feedInitials: 'WR',
  feedTint: '#38bdf8',
  side: 'SHORT',
  symbol: 'ETHUSDT',
  status: 'tested',
  outcome: 'profit',
  pnl: 1.5,
  text: 'ETH short entry'
}

const deletedSignal = {
  ...btcSignal,
  id: 'sig-3',
  status: 'deleted',
  deleted: true,
  symbol: 'SOLUSDT',
  text: 'SOL long entry'
}

const orphan = {
  id: '3',
  feedId: '7',
  feedName: 'Pilot Signals',
  feedTag: '@pilot',
  feedInitials: 'PS',
  feedTint: '#5197ff',
  source: 'telegram',
  symbol: 'BTCUSDT',
  date: 'Jun 6',
  time: '12:30',
  text: 'close BTC',
  suggestId: 'sig-1',
  reason: 'No reply link found'
}

function backendBody(overrides = {}) {
  return {
    signals: [btcSignal, ethSignal, deletedSignal],
    orphanMods: [orphan],
    limitReached: false,
    ...overrides
  }
}

function manySignals(count) {
  return Array.from({ length: count }, (_, index) => ({
    ...btcSignal,
    id: `sig-${index + 1}`,
    time: `12:${String(index).padStart(2, '0')}`
  }))
}

function renderView({
  authToken = 'jwt-token',
  onListSignals = vi.fn().mockResolvedValue(backendBody()),
  onLinkSignalModifier = vi.fn().mockResolvedValue({}),
  viewFeeds = feeds,
  plan = 'operator',
  onUpgrade = vi.fn(),
  initial
} = {}) {
  const utils = render(
    <SignalsView
      authToken={authToken}
      feeds={viewFeeds}
      initial={initial}
      plan={plan}
      onUpgrade={onUpgrade}
      onListSignals={onListSignals}
      onLinkSignalModifier={onLinkSignalModifier}
      onGoToSources={() => {}}
    />
  )
  return { ...utils, onListSignals, onLinkSignalModifier, onUpgrade }
}

describe('SignalsView', () => {
  it('loads backend signals', async () => {
    let resolveSignals
    const onListSignals = vi.fn(
      () =>
        new Promise((resolve) => {
          resolveSignals = resolve
        })
    )

    renderView({ onListSignals })

    expect(screen.getByText('Loading signals')).toBeTruthy()
    resolveSignals(backendBody())

    expect((await screen.findAllByText('BTC/USDT')).length).toBeGreaterThan(0)
    expect(onListSignals).toHaveBeenCalledWith('jwt-token')
  })

  it('filters by feed and tab', async () => {
    renderView()

    expect((await screen.findAllByText('BTC/USDT')).length).toBeGreaterThan(0)

    const feedSelect = screen.getAllByRole('combobox')[1]
    fireEvent.change(feedSelect, { target: { value: '8' } })

    expect(screen.queryByText('BTC/USDT')).toBeNull()
    expect(screen.getByText('ETH/USDT')).toBeTruthy()

    fireEvent.click(screen.getByRole('tab', { name: /Not tested/i }))

    expect(screen.getByText('No untested signals for these filters.')).toBeTruthy()
  })

  it('shows the no-signals state until a feed is verified or analyzed', () => {
    renderView({
      authToken: null,
      viewFeeds: [{ ...feeds[0], status: 'backfilled' }]
    })

    expect(screen.getByText('No signals yet')).toBeTruthy()
  })

  it('expands a signal detail with original raw text', async () => {
    renderView()

    fireEvent.click(await screen.findByRole('button', { name: /BTC\/USDT/i }))

    expect(screen.getByText('Original message')).toBeTruthy()
    expect(screen.getByText('BTC long entry')).toBeTruthy()
    expect(screen.getByText('Queued for backtest', { exact: false })).toBeTruthy()
  })

  it('dismisses an orphan update locally', async () => {
    renderView()

    expect(await screen.findByText('Unlinked update')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Dismiss' }))

    expect(screen.queryByText('Unlinked update')).toBeNull()
  })

  it('links an orphan update and keeps the active filters', async () => {
    const linkedSignal = {
      ...btcSignal,
      mods: [
        {
          id: '3',
          kind: 'close',
          date: 'Jun 6',
          time: '12:30',
          via: 'inferred',
          text: 'close BTC',
          effect: 'Closed by author'
        }
      ],
      effective: { ...btcSignal.effective, closedBy: 'author' }
    }
    const onListSignals = vi
      .fn()
      .mockResolvedValueOnce(backendBody())
      .mockResolvedValueOnce(
        backendBody({ signals: [linkedSignal, ethSignal], orphanMods: [] })
      )
    const onLinkSignalModifier = vi.fn().mockResolvedValue(linkedSignal)

    renderView({ onListSignals, onLinkSignalModifier })

    await screen.findByText('Unlinked update')
    const feedSelect = screen.getAllByRole('combobox')[1]
    fireEvent.change(feedSelect, { target: { value: '7' } })
    fireEvent.click(screen.getByRole('button', { name: /Link to sig-1/i }))

    await waitFor(() => {
      expect(onLinkSignalModifier).toHaveBeenCalledWith('jwt-token', 'sig-1', '3')
    })
    expect(feedSelect.value).toBe('7')
    expect(await screen.findByText('Closed by author')).toBeTruthy()
  })

  it('paginates the list at 25 per page and advances on Next', async () => {
    const onListSignals = vi
      .fn()
      .mockResolvedValue(backendBody({ signals: manySignals(30), orphanMods: [] }))
    const { container } = renderView({ onListSignals })

    await screen.findAllByText('BTC/USDT')
    const label = () => container.querySelector('.vrs-pager__label').textContent

    expect(container.querySelectorAll('.vrs-sigrow').length).toBe(25)
    expect(label()).toContain('of 30')
    expect(label().startsWith('1')).toBe(true)

    fireEvent.click(screen.getByRole('button', { name: /Next/i }))

    expect(container.querySelectorAll('.vrs-sigrow').length).toBe(5)
    expect(label().startsWith('26')).toBe(true)
  })

  it('renders the plan-limit notice with the full total when capped', async () => {
    const onListSignals = vi.fn().mockResolvedValue(
      backendBody({
        signals: manySignals(3),
        limitReached: true,
        total: 644,
        limit: 200
      })
    )
    renderView({ onListSignals, plan: 'observer' })

    expect(
      await screen.findByText(/200 most recent of 644 detected signals/)
    ).toBeTruthy()
    expect(screen.getByText(/Observer/)).toBeTruthy()
  })

  it('does not render the plan-limit notice when under the limit', async () => {
    renderView()

    await screen.findByRole('button', { name: /BTC\/USDT/i })
    expect(screen.queryByText(/most recent of/)).toBeNull()
  })

  it('calls onUpgrade when the notice Upgrade action is clicked', async () => {
    const onListSignals = vi.fn().mockResolvedValue(
      backendBody({
        signals: manySignals(3),
        limitReached: true,
        total: 644,
        limit: 200
      })
    )
    const { onUpgrade } = renderView({ onListSignals, plan: 'observer' })

    fireEvent.click(await screen.findByRole('button', { name: 'Upgrade' }))
    expect(onUpgrade).toHaveBeenCalledTimes(1)
  })
})
