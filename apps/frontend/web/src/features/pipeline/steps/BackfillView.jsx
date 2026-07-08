import { useState, useEffect, useRef } from 'react'
import { Button } from '@verasig/design-system'
import { Icon } from '@verasig/design-system'
import { Loader } from '@verasig/design-system'
import { StageStrip } from '../../../shared/jobs/StageStrip.jsx'

function messageFromError(error) {
  return error?.message || 'Backfill failed.'
}

const EMPTY_DATE_LABEL = 'No messages yet'

function displayDate(value) {
  return value || EMPTY_DATE_LABEL
}

function storedDate(value) {
  return value === EMPTY_DATE_LABEL ? null : value
}

function simulatedDateLabels() {
  const formatter = new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  })
  const now = new Date()
  return [0, 3, 8, 16, 27, 40, 59, 78, 99, 126, 154, 185, 213].map((days) => {
    const date = new Date(now)
    date.setDate(now.getDate() - days)
    return formatter.format(date)
  })
}

// A fetch is Fetch -> Index only, driven by the SSE `stage` field. Deletion
// detection is a separate operation (Check gaps), so no securing/deletion stages
// ever appear in the fetch strip.
const CAPTURE_STAGES = [
  { id: 'capture', label: 'Fetching history' },
  { id: 'index', label: 'Indexing' }
]

/* Verasig prototype — backfill infinite loader */
export function BackfillView({
  feed,
  mode,
  onCancel = () => {},
  onComplete = () => {},
  onError = () => {},
  onStart,
  onStream,
  onCancelBackfill
}) {
  // A full re-fetch wipes and recaptures (ADR 0014), so its counter starts at 0
  // rather than the stale pre-wipe total.
  const isFull = mode === 'full'
  const seedCount = isFull ? 0 : feed.fetched || 0
  const seedDate = isFull ? null : feed.lastDate || null
  const [count, setCount] = useState(seedCount)
  const [date, setDate] = useState(displayDate(seedDate))
  const [logLine, setLogLine] = useState('Opening MTProto session…')
  const [stage, setStage] = useState('capture')
  const countRef = useRef(seedCount)
  const dateRef = useRef(seedDate)
  const handlersRef = useRef({
    onCancel,
    onCancelBackfill,
    onComplete,
    onError,
    onStart,
    onStream
  })

  useEffect(() => {
    handlersRef.current = {
      onCancel,
      onCancelBackfill,
      onComplete,
      onError,
      onStart,
      onStream
    }
  }, [onCancel, onCancelBackfill, onComplete, onError, onStart, onStream])

  const hasBackendBackfill = !!onStart && !!onStream

  useEffect(() => {
    countRef.current = isFull ? 0 : feed.fetched || 0
    dateRef.current = isFull ? null : feed.lastDate || null
    setCount(isFull ? 0 : feed.fetched || 0)
    setDate(displayDate(isFull ? null : feed.lastDate))
    setLogLine('Opening MTProto session…')
    setStage('capture')

    if (hasBackendBackfill) {
      let closed = false
      let subscription = null

      async function startBackendBackfill() {
        try {
          await handlersRef.current.onStart(feed.id)
          if (closed) return
          subscription = handlersRef.current.onStream(feed.id, {
            onProgress: (progress) => {
              const nextCount = progress.fetched ?? countRef.current
              countRef.current = nextCount
              setCount(nextCount)
              if ('lastDate' in progress) {
                dateRef.current = progress.lastDate || null
                setDate(displayDate(progress.lastDate))
              }
              if (progress.phase) setLogLine(progress.phase)
              if (progress.stage) setStage(progress.stage)
            },
            onDone: (result) => {
              const total = result.fetched ?? countRef.current
              const completedDate = result.lastDate ?? dateRef.current
              countRef.current = total
              dateRef.current = completedDate || null
              setCount(total)
              setDate(displayDate(completedDate))
              setLogLine('Backfill complete · finalizing index')
              handlersRef.current.onComplete({
                fetched: total,
                lastDate: completedDate || null,
                status: result.status || 'succeeded'
              })
            },
            onError: (error) => {
              const nextCount = error?.fetched ?? countRef.current
              const nextDate = error?.lastDate ?? dateRef.current
              countRef.current = nextCount
              dateRef.current = nextDate || null
              setCount(nextCount)
              setDate(displayDate(nextDate))
              setLogLine(error?.message || 'Backfill stopped.')
              handlersRef.current.onError({
                ...(error || {}),
                fetched: nextCount,
                lastDate: nextDate || null,
                status: error?.status || 'failed'
              })
            }
          })
        } catch (error) {
          if (!closed) {
            const message = messageFromError(error)
            setLogLine(message)
            handlersRef.current.onError({
              message,
              fetched: countRef.current,
              lastDate: dateRef.current,
              status: 'failed'
            })
          }
        }
      }

      void startBackendBackfill()

      return () => {
        closed = true
        subscription && subscription.close()
      }
    }

    // Simulated, accelerating backfill that completes after a believable run.
    const TARGET = (feed.fetched || 0) + 9800 + Math.floor(Math.random() * 3000)
    let doneTimer = null
    const dates = simulatedDateLabels()
    const logs = [
      'Reading channel history…',
      'Decrypting message batch…',
      'Resolving media references…',
      'Backfilling older window…',
      'Indexing message bodies…'
    ]
    let di = 0
    const tick = setInterval(() => {
      countRef.current += 40 + Math.floor(Math.random() * 220)
      if (countRef.current >= TARGET) {
        countRef.current = TARGET
        setCount(TARGET)
        clearInterval(tick)
        clearInterval(logTick)
        setLogLine('Backfill complete · finalizing index')
        doneTimer = setTimeout(
          () =>
            handlersRef.current.onComplete({
              fetched: TARGET,
              lastDate: storedDate(dateRef.current),
              status: 'succeeded'
            }),
          900
        )
        return
      }
      setCount(countRef.current)
      di = Math.min(
        dates.length - 1,
        Math.floor((countRef.current / TARGET) * dates.length)
      )
      dateRef.current = dates[di]
      setDate(dates[di])
    }, 90)
    const logTick = setInterval(
      () => setLogLine(logs[Math.floor(Math.random() * logs.length)]),
      1500
    )
    return () => {
      clearInterval(tick)
      clearInterval(logTick)
      clearTimeout(doneTimer)
    }
    // Keyed on feed.id only: feed.fetched/feed.lastDate are seed values captured
    // when the active feed changes. They keep updating as the backend streams
    // progress, and re-running here would tear down the live stream mid-backfill.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [feed.id, hasBackendBackfill])

  async function cancelBackfill() {
    try {
      if (handlersRef.current.onCancelBackfill) {
        await handlersRef.current.onCancelBackfill(feed.id)
      }
      handlersRef.current.onCancel(countRef.current, storedDate(dateRef.current))
    } catch (error) {
      setLogLine(messageFromError(error))
    }
  }

  return (
    <div className="vrs-backfill vrs-fade-in">
      <svg
        className="vrs-bf-scope"
        viewBox="0 0 360 96"
        fill="none"
        preserveAspectRatio="none"
      >
        <path
          d="M0 48 H90 L108 18 L128 78 L150 30 L168 60 L186 48 H360"
          stroke="var(--signal-500)"
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ filter: 'drop-shadow(0 0 6px var(--signal-glow))' }}
          strokeDasharray="600"
          strokeDashoffset="600"
        >
          <animate
            attributeName="stroke-dashoffset"
            from="600"
            to="0"
            dur="1.6s"
            repeatCount="indefinite"
          />
        </path>
      </svg>

      <div>
        <div className="vrs-bf-title">Backfilling {feed.name}</div>
        <div className="vrs-bf-sub" style={{ marginTop: 6 }}>
          Pulling the full message history from {feed.tag}. This can take a while — you
          can leave and come back.
        </div>
      </div>

      <div className="vrs-bf-stats">
        <div>
          <div className="vrs-bf-stat__v">{count.toLocaleString()}</div>
          <div className="vrs-bf-stat__l">Messages fetched</div>
        </div>
        {/* Hidden until the first fetch reports a date; a newest-first capture then
            keeps pushing this frontier further into the past. */}
        {date !== EMPTY_DATE_LABEL && (
          <div>
            <div
              className="vrs-bf-stat__v"
              style={{ fontSize: 'var(--text-2xl)', paddingTop: 14 }}
            >
              {date}
            </div>
            <div className="vrs-bf-stat__l">Oldest message reached</div>
          </div>
        )}
      </div>

      <StageStrip stages={CAPTURE_STAGES} stage={stage} />
      <Loader variant="bar" size="md" />
      <div className="vrs-bf-log">{logLine}</div>

      <Button
        variant="ghost"
        iconLeft={<Icon name="x" size={15} />}
        onClick={cancelBackfill}
      >
        Cancel backfill
      </Button>
    </div>
  )
}
