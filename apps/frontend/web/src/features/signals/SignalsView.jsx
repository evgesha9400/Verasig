import { useState, useMemo, useEffect } from 'react'
import { Select, Tabs, Badge, Button, Icon, Pill } from '@verasig/design-system'
import {
  SIGNALS,
  SOURCES,
  MOD_KINDS,
  ORPHAN_MODS,
  ORPHAN_LINKED_MOD
} from '../../domain/demo-data/seed.js'

/* Verasig prototype — Signals page: extracted output of analyzed feeds, filterable by source & feed.
   Signals can carry `mods` — follow-up updates (close / avg down / avg up / move stop / cancel)
   the author posted as replies to the original signal message. The row shows the EFFECTIVE
   state (averaged entry, author exits baked into PnL) plus an updates chip; the full chain
   lives in the expanded detail. */
export function SignalsView({ feeds, onGoToSources, initial }) {
  // Only analyzed (backfilled + backtested) feeds produce signals.
  const analyzedFeeds = feeds.filter((f) => f.status === 'analyzed')
  const feedById = useMemo(
    () => Object.fromEntries(feeds.map((f) => [f.id, f])),
    [feeds]
  )
  const feedSource = (f) => (f && f.source) || 'telegram' // Telegram is the only connected source today

  const [source, setSource] = useState((initial && initial.source) || 'all')
  const [feed, setFeed] = useState((initial && initial.feed) || 'all')
  const [tab, setTab] = useState((initial && initial.tab) || 'all') // all | tested | untested | skipped | deleted
  const [openId, setOpenId] = useState(null)
  // Orphan update (no reply link): open → user links it to the suggestion, or dismisses.
  const [orphanState, setOrphanState] = useState('open') // open | linked | dismissed

  // Deep-link presets (e.g. the "View deleted signals" link on a scam feed) re-apply when they change.
  useEffect(() => {
    if (!initial) return
    if (initial.source != null) setSource(initial.source)
    if (initial.feed != null) setFeed(initial.feed)
    if (initial.tab != null) setTab(initial.tab)
    setOpenId(null)
  }, [initial])

  // distinct sources present across analyzed feeds
  const sourceIds = useMemo(
    () => [...new Set(analyzedFeeds.map(feedSource))],
    [analyzedFeeds]
  )

  // feed options narrow to the chosen source
  const feedOptions = useMemo(() => {
    const fs = analyzedFeeds.filter((f) => source === 'all' || feedSource(f) === source)
    return [
      { value: 'all', label: 'All feeds' },
      ...fs.map((f) => ({ value: f.id, label: f.name }))
    ]
  }, [analyzedFeeds, source])

  function changeSource(v) {
    setSource(v)
    if (feed !== 'all') {
      const f = feedById[feed]
      if (v !== 'all' && (!f || feedSource(f) !== v)) setFeed('all')
    }
  }

  // Manually linking the orphan attaches it to its suggested signal as a late (ignored) close.
  const allSignals = useMemo(() => {
    if (orphanState !== 'linked') return SIGNALS
    return SIGNALS.map((s) =>
      s.id === ORPHAN_MODS[0].suggestId
        ? { ...s, mods: [...(s.mods || []), ORPHAN_LINKED_MOD] }
        : s
    )
  }, [orphanState])

  // base set: signals from analyzed feeds, respecting source + feed (not the tab — used for tab counts)
  const scoped = useMemo(() => {
    const analyzedIds = new Set(analyzedFeeds.map((f) => f.id))
    return allSignals
      .filter((s) => analyzedIds.has(s.feedId))
      .filter((s) => source === 'all' || feedSource(feedById[s.feedId]) === source)
      .filter((s) => feed === 'all' || s.feedId === feed)
      .sort((a, b) => sortKey(b) - sortKey(a))
  }, [allSignals, analyzedFeeds, source, feed, feedById])

  // Tab buckets — Tested / Not tested / Skipped exclude deleted; Deleted is its own bucket.
  const live = scoped.filter((s) => !s.deleted)
  const testedCount = live.filter((s) => s.status === 'tested').length
  const untestedCount = live.filter((s) => s.status === 'untested').length
  const skippedCount = live.filter((s) => s.status === 'skipped').length
  const deletedCount = scoped.filter((s) => s.deleted).length
  const visible =
    tab === 'tested'
      ? live.filter((s) => s.status === 'tested')
      : tab === 'untested'
        ? live.filter((s) => s.status === 'untested')
        : tab === 'skipped'
          ? live.filter((s) => s.status === 'skipped')
          : tab === 'deleted'
            ? scoped.filter((s) => s.deleted)
            : scoped

  // Orphan card visibility: pending updates belong to a feed — show while that feed is in scope.
  const orphan = ORPHAN_MODS[0]
  const orphanFeed = feedById[orphan.feedId]
  const orphanVisible =
    orphanState === 'open' &&
    tab === 'all' &&
    (feed === 'all' || feed === orphan.feedId) &&
    (source === 'all' || feedSource(orphanFeed) === source) &&
    analyzedFeeds.some((f) => f.id === orphan.feedId)
  const suggested = allSignals.find((s) => s.id === orphan.suggestId)

  function linkOrphan() {
    setOrphanState('linked')
    setOpenId(orphan.suggestId)
  }

  // ---- empty state: nothing analyzed yet ----
  if (analyzedFeeds.length === 0) {
    return (
      <div className="vrs-page">
        <div className="vrs-empty vrs-empty--lg">
          <svg
            width="34"
            height="34"
            viewBox="0 0 40 40"
            fill="none"
            style={{ color: 'var(--text-faint)' }}
          >
            <path
              d="M4 22 L11 22 L17 30 L24 9 L30 18"
              stroke="currentColor"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <circle cx="30" cy="18" r="3" fill="currentColor" />
          </svg>
          <div className="vrs-empty__title">No signals yet</div>
          <div className="vrs-empty__note">
            Backfill and backtest a feed under Sources. Once a feed is analyzed, its
            extracted signals stream here.
          </div>
          <Button
            variant="secondary"
            size="sm"
            iconRight={<Icon name="arrowRight" size={14} />}
            onClick={onGoToSources}
          >
            Go to sources
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="vrs-page">
      {/* filter bar */}
      <div className="vrs-sig-filters">
        <div className="vrs-sig-filters__group">
          <Select
            label="Source"
            value={source}
            onChange={(e) => changeSource(e.target.value)}
            options={[
              { value: 'all', label: 'All sources' },
              ...sourceIds.map((id) => ({ value: id, label: SOURCES[id] || id }))
            ]}
          />
          <Select
            label="Feed"
            value={feed}
            onChange={(e) => setFeed(e.target.value)}
            options={feedOptions}
          />
        </div>
        <div className="vrs-sig-filters__count">
          <span className="vrs-sig-count__v">{visible.length}</span>
          <span className="vrs-sig-count__l">
            {visible.length === 1 ? 'signal' : 'signals'}
          </span>
        </div>
      </div>

      {/* tabs */}
      <div style={{ marginTop: 4 }}>
        <Tabs
          value={tab}
          onChange={setTab}
          items={[
            { id: 'all', label: 'All', count: scoped.length },
            { id: 'tested', label: 'Tested', count: testedCount },
            { id: 'untested', label: 'Not tested', count: untestedCount },
            { id: 'skipped', label: 'Skipped', count: skippedCount },
            { id: 'deleted', label: 'Deleted', count: deletedCount }
          ]}
        />
      </div>

      {/* unlinked update — parser couldn't tie it to a signal, needs a human call */}
      {orphanVisible && (
        <div className="vrs-orphan vrs-fade-in">
          <div className="vrs-orphan__main">
            <div className="vrs-orphan__head">
              <Icon name="alert" size={15} />
              <span className="vrs-orphan__t">Unlinked update</span>
              <Badge tone="pending" dot>
                Needs review
              </Badge>
            </div>
            <div className="vrs-orphan__msg">
              <span
                className="vrs-sigrow__av"
                style={{ background: orphanFeed && orphanFeed.tint }}
              >
                {orphanFeed && orphanFeed.initials}
              </span>
              <pre className="vrs-orphan__txt">{orphan.text}</pre>
              <span className="vrs-orphan__time">
                {orphan.date} · {orphan.time}
              </span>
            </div>
            <div className="vrs-orphan__why">{orphan.reason}</div>
          </div>
          <div className="vrs-orphan__side">
            {suggested && (
              <div className="vrs-orphan__sug">
                <span className="vrs-sig-lvl__k">Closest match</span>
                <span className="vrs-orphan__sugsig">
                  <span
                    className={`vrs-side vrs-side--${suggested.side.toLowerCase()}`}
                  >
                    {suggested.side}
                  </span>
                  {suggested.symbol}
                  <span className="vrs-orphan__sugid">{suggested.id}</span>
                </span>
              </div>
            )}
            <div className="vrs-orphan__btns">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setOrphanState('dismissed')}
              >
                Dismiss
              </Button>
              <Button
                variant="primary"
                size="sm"
                iconLeft={<Icon name="link" size={14} />}
                onClick={linkOrphan}
              >
                Link to {orphan.suggestId}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* column header */}
      <div className="vrs-sig-head">
        <span className="vrs-sig-head__sym">Signal</span>
        <span className="vrs-sig-head__feed">Feed</span>
        <span className="vrs-sig-head__st">Status</span>
        <span className="vrs-sig-head__time">Time</span>
      </div>

      {/* list */}
      <div className="vrs-stack-xs">
        {visible.length === 0 ? (
          <div className="vrs-empty vrs-empty--sm">
            <div className="vrs-empty__note">
              {tab === 'tested'
                ? 'No tested signals for these filters.'
                : tab === 'untested'
                  ? 'No untested signals for these filters.'
                  : tab === 'skipped'
                    ? 'No skipped signals for these filters.'
                    : tab === 'deleted'
                      ? 'No deleted signals for these filters.'
                      : 'No signals match these filters.'}
            </div>
          </div>
        ) : (
          visible.map((s) => {
            const f = feedById[s.feedId] || {}
            const open = openId === s.id
            const skipped = s.status === 'skipped' && !s.cancelled
            const untested = s.status === 'untested'
            const tested = s.status === 'tested'
            const deleted = s.deleted
            const mods = s.mods || []
            const authorExit = s.effective && s.effective.closedBy === 'author'
            return (
              <div key={s.id} className={`vrs-sig-item ${open ? 'is-open' : ''}`}>
                <button
                  className={`vrs-sigrow s-${s.status} ${deleted ? 'is-deleted' : ''} ${s.cancelled ? 'is-cancelled' : ''}`}
                  onClick={() => setOpenId(open ? null : s.id)}
                >
                  <span className="vrs-sigrow__rail" aria-hidden="true" />
                  <span className="vrs-sigrow__main">
                    <span className="vrs-sigrow__sym">
                      <span className={`vrs-side vrs-side--${s.side.toLowerCase()}`}>
                        {s.side}
                      </span>
                      {s.symbol}
                      {mods.length > 0 && (
                        <span className="vrs-modtag">
                          <Icon name="reply" size={10} />
                          <span className="vrs-modtag__t">
                            {mods.length} update{mods.length > 1 ? 's' : ''}
                          </span>
                        </span>
                      )}
                    </span>
                    <span className="vrs-sigrow__id">
                      {s.id} · {SOURCES[feedSource(f)] || 'Telegram'}
                      {authorExit ? ' · author exit' : ''}
                    </span>
                  </span>
                  <span className="vrs-sigrow__feed">
                    <span className="vrs-sigrow__av" style={{ background: f.tint }}>
                      {f.initials}
                    </span>
                    <span className="vrs-sigrow__feedname">{f.name}</span>
                  </span>
                  <span className="vrs-sigrow__st">
                    {deleted ? (
                      <Badge tone="rejected" dot>
                        Deleted
                      </Badge>
                    ) : s.cancelled ? (
                      <Badge tone="neutral" dot>
                        Cancelled
                      </Badge>
                    ) : skipped ? (
                      <Badge tone="neutral" dot>
                        Skipped
                      </Badge>
                    ) : untested ? (
                      <Badge tone="pending" dot>
                        Not tested
                      </Badge>
                    ) : (
                      <>
                        <Badge tone="verified" dot>
                          Tested
                        </Badge>
                        {s.outcome && (
                          <Pill tone={s.outcome} numeric>
                            <Icon
                              name={s.outcome === 'profit' ? 'arrowUp' : 'arrowDown'}
                              size={11}
                            />
                            {s.pnl}
                          </Pill>
                        )}
                      </>
                    )}
                  </span>
                  <span className="vrs-sigrow__time">
                    {s.date} · {s.time}
                  </span>
                  <span className="vrs-sigrow__chev" aria-hidden="true">
                    <Icon name="chevronRight" size={15} />
                  </span>
                </button>

                {open && (
                  <div className="vrs-sig-detail vrs-fade-in">
                    {/* LEFT — the raw Telegram conversation Verasig extracted this signal from */}
                    <div className="vrs-sig-pane vrs-sig-pane--msg">
                      <div className="vrs-sig-pane__eyebrow">
                        {mods.length > 0
                          ? `Conversation · ${1 + mods.length} messages`
                          : 'Original message'}
                      </div>
                      <div className="vrs-stack-xs">
                        <div className="vrs-sig-bubble">
                          <div className="vrs-sig-bubble__head">
                            <span
                              className="vrs-sigrow__av"
                              style={{ background: f.tint }}
                            >
                              {f.initials}
                            </span>
                            <span className="vrs-sig-bubble__who">
                              <span className="vrs-sig-bubble__name">{f.name}</span>
                              <span className="vrs-sig-bubble__tag">{f.tag}</span>
                            </span>
                            <span className="vrs-sig-bubble__time">
                              {s.date} · {s.time}
                            </span>
                          </div>
                          <pre className="vrs-sig-bubble__text">{rawMessage(s)}</pre>
                        </div>
                        {mods.map((m) => {
                          const k = MOD_KINDS[m.kind] || {}
                          return (
                            <div
                              key={m.id}
                              className="vrs-sig-bubble vrs-sig-bubble--mod"
                            >
                              <div className="vrs-sig-bubble__head">
                                <span
                                  className="vrs-sigrow__av"
                                  style={{ background: f.tint }}
                                >
                                  {f.initials}
                                </span>
                                <span className="vrs-sig-bubble__who">
                                  <span className="vrs-sig-bubble__name">{f.name}</span>
                                </span>
                                <Badge tone={k.tone || 'neutral'}>{k.label}</Badge>
                                <span className="vrs-sig-bubble__time">
                                  {m.date} · {m.time}
                                </span>
                              </div>
                              {m.via === 'reply' ? (
                                <div className="vrs-replyq">
                                  <span className="vrs-replyq__who">{f.name}</span>
                                  <span className="vrs-replyq__txt">
                                    {rawMessage(s).split('\n')[0]}
                                  </span>
                                </div>
                              ) : (
                                <div
                                  className={`vrs-via ${m.via === 'manual' ? 'vrs-via--manual' : ''}`}
                                >
                                  <Icon name="link" size={11} />
                                  {m.via === 'manual'
                                    ? 'Linked manually — no reply in chat'
                                    : 'Link inferred — no reply in chat'}
                                </div>
                              )}
                              <pre className="vrs-sig-bubble__text">{m.text}</pre>
                            </div>
                          )
                        })}
                      </div>
                    </div>

                    {/* RIGHT — the structured signal Verasig parsed, plus the position timeline */}
                    <div className="vrs-sig-pane vrs-sig-pane--extract">
                      <div className="vrs-sig-pane__eyebrow">Extracted signal</div>
                      <div className="vrs-sig-fields">
                        <div className="vrs-sig-field">
                          <span className="vrs-sig-lvl__k">Direction</span>
                          <span className="vrs-sig-lvl__v">
                            <span
                              className={`vrs-side vrs-side--${s.side.toLowerCase()}`}
                              style={{ marginRight: 0 }}
                            >
                              {s.side}
                            </span>
                          </span>
                        </div>
                        <div className="vrs-sig-field">
                          <span className="vrs-sig-lvl__k">Entry</span>
                          {s.effective && s.effective.entry ? (
                            <span className="vrs-sig-lvl__v">
                              <s className="vrs-eff-was">{s.entry}</s>{' '}
                              {s.effective.entry}{' '}
                              <span className="vrs-eff-note">
                                {s.effective.entryNote}
                              </span>
                            </span>
                          ) : (
                            <span className="vrs-sig-lvl__v">{s.entry}</span>
                          )}
                        </div>
                        <div className="vrs-sig-field">
                          <span className="vrs-sig-lvl__k">Stop</span>
                          {s.effective && s.effective.stop ? (
                            <span className="vrs-sig-lvl__v vrs-sig-lvl__v--stop">
                              <s className="vrs-eff-was">{s.stop}</s> {s.effective.stop}{' '}
                              <span className="vrs-eff-note">
                                {s.effective.stopNote}
                              </span>
                            </span>
                          ) : (
                            <span
                              className={`vrs-sig-lvl__v ${s.stop ? 'vrs-sig-lvl__v--stop' : 'vrs-sig-lvl__v--none'}`}
                            >
                              {s.stop || 'None'}
                            </span>
                          )}
                        </div>
                        <div className="vrs-sig-field vrs-sig-field--wide">
                          <span className="vrs-sig-lvl__k">Targets</span>
                          <span
                            className={`vrs-sig-lvl__v ${s.tp ? '' : 'vrs-sig-lvl__v--none'}`}
                          >
                            {s.tp || 'None'}
                          </span>
                        </div>
                      </div>

                      {/* position timeline — how the updates played the position */}
                      {mods.length > 0 && !s.cancelled && (
                        <div className="vrs-tl">
                          <div
                            className="vrs-sig-pane__eyebrow"
                            style={{ marginBottom: 7 }}
                          >
                            Position timeline
                          </div>
                          <div className={`vrs-tl__row ${untested ? 'is-muted' : ''}`}>
                            <span className="vrs-tl__ic">
                              <Icon name="spark" size={11} />
                            </span>
                            <span className="vrs-tl__lbl">
                              {untested
                                ? 'Entry (queued for backtest)'
                                : `Entry filled @ ${s.entry}`}
                            </span>
                            <span className="vrs-tl__time">{s.time}</span>
                          </div>
                          {mods.map((m) => {
                            const k = MOD_KINDS[m.kind] || {}
                            return (
                              <div
                                key={m.id}
                                className={`vrs-tl__row ${m.late ? 'is-late' : ''}`}
                              >
                                <span className="vrs-tl__ic">
                                  <Icon
                                    name={m.late ? 'alert' : k.icon || 'reply'}
                                    size={11}
                                  />
                                </span>
                                <span className="vrs-tl__lbl">
                                  {k.label}
                                  {m.price ? ` @ ${m.price}` : ''}
                                  <span className="vrs-tl__fx">{m.effect}</span>
                                </span>
                                <span className="vrs-tl__time">{m.time}</span>
                              </div>
                            )
                          })}
                          {authorExit && s.outcome && (
                            <div className="vrs-tl__row is-final">
                              <span className="vrs-tl__ic">
                                <Icon name="check" size={11} />
                              </span>
                              <span className="vrs-tl__lbl">
                                Closed by author
                                <Pill tone={s.outcome} numeric
                                  style={{ marginLeft: 8 }}
                                >
                                  <Icon
                                    name={
                                      s.outcome === 'profit' ? 'arrowUp' : 'arrowDown'
                                    }
                                    size={11}
                                  />
                                  {s.pnl}
                                </Pill>
                              </span>
                            </div>
                          )}
                          {!authorExit && tested && s.outcome && (
                            <div className="vrs-tl__row is-final">
                              <span className="vrs-tl__ic">
                                <Icon
                                  name={s.outcome === 'profit' ? 'check' : 'x'}
                                  size={11}
                                />
                              </span>
                              <span className="vrs-tl__lbl">
                                {s.outcome === 'profit'
                                  ? 'Closed on backtest'
                                  : 'Closed at stop'}
                                <Pill tone={s.outcome} numeric
                                  style={{ marginLeft: 8 }}
                                >
                                  <Icon
                                    name={
                                      s.outcome === 'profit' ? 'arrowUp' : 'arrowDown'
                                    }
                                    size={11}
                                  />
                                  {s.pnl}
                                </Pill>
                              </span>
                            </div>
                          )}
                          {s.effective && s.effective.note && (
                            <div className="vrs-tl__note">{s.effective.note}</div>
                          )}
                        </div>
                      )}

                      {tested && !deleted && s.outcome && mods.length === 0 && (
                        <div className={`vrs-sig-result vrs-sig-result--${s.outcome}`}>
                          <Pill tone={s.outcome} numeric>
                            <Icon
                              name={s.outcome === 'profit' ? 'arrowUp' : 'arrowDown'}
                              size={11}
                            />
                            {s.pnl}
                          </Pill>
                          <span>
                            {s.outcome === 'profit'
                              ? 'Closed in profit on backtest.'
                              : 'Closed at a loss on backtest.'}
                          </span>
                        </div>
                      )}
                      {deleted ? (
                        <div className="vrs-sig-skipnote vrs-sig-skipnote--deleted">
                          <Icon name="alert" size={13} /> Removed from the channel —
                          this signal was deleted from the feed&rsquo;s history after
                          extraction.
                        </div>
                      ) : s.cancelled ? (
                        <div className="vrs-sig-skipnote">
                          <Icon name="x" size={13} /> Cancelled by the author before
                          entry — excluded from the backtest.
                        </div>
                      ) : untested ? (
                        <div className="vrs-sig-skipnote vrs-sig-skipnote--untested">
                          <Icon name="clock" size={13} /> Queued for backtest — has risk
                          management but hasn&rsquo;t been run yet.
                        </div>
                      ) : (
                        skipped && (
                          <div className="vrs-sig-skipnote">
                            <Icon name="x" size={13} /> Skipped from backtest — no
                            stop-loss or target defined.
                          </div>
                        )
                      )}
                    </div>
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

// Stable per-id hash so each signal's reconstructed source message looks consistent across renders.
function hashId(id) {
  let h = 0
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0
  return h
}

// Reconstruct the messy, free-form Telegram post Verasig parsed this signal out of.
// Skipped signals (no stop/target) come from loose calls with no risk management —
// which is exactly why they were skipped.
function rawMessage(s) {
  const base = s.symbol.split('/')[0]
  const side = s.side
  const h = hashId(s.id)

  if (!s.stop && !s.tp) {
    const loose = [
      `${side} ${s.symbol} here ${s.entry} 🚀\nsmall size, no hard stop — mental SL only. updates to follow`,
      `quick idea — ${side.toLowerCase()} ${base} around ${s.entry}\nliking this setup, will post levels later`,
      `aping ${base} ${side.toLowerCase()} @ ${s.entry}\nmanage your own risk, NFA`
    ]
    return loose[h % loose.length]
  }

  const tmpl = h % 3
  if (tmpl === 0) {
    let m = `${side === 'LONG' ? '🟢' : '🔴'} ${side}  ${s.symbol}\nEntry  ${s.entry}\nStop-loss  ${s.stop}\nTargets  ${s.tp}`
    if (h % 2 === 0) m += `\nLeverage  5–10x`
    return m
  }
  if (tmpl === 1) {
    let m = `$${base} ${side}\nEntry: ${s.entry}\nSL: ${s.stop}\nTP: ${s.tp}`
    if (h % 2 === 1) m += `\nRisk 2% of book`
    return m
  }
  return `${side} ${s.symbol} @ ${s.entry}\nstop ${s.stop}\ntargets ${s.tp}\nclose half at first TP, then move SL to break-even`
}

// 'Jun 7' + '14:32' → sortable recency key (descending newest)
function sortKey(s) {
  const day = parseInt((s.date.match(/\d+/) || [0])[0], 10)
  const [h, m] = s.time.split(':').map((n) => parseInt(n, 10))
  return day * 10000 + h * 100 + m
}
