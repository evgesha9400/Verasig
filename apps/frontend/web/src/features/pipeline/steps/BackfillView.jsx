import { useState, useEffect, useRef } from 'react'
import { Button } from '@verasig/design-system'
import { Icon } from '@verasig/design-system'

function messageFromError(error) {
  return error?.message || 'Backfill failed.'
}

/* Verasig prototype — backfill infinite loader */
export function BackfillView({
  chat,
  onCancel = () => {},
  onComplete = () => {},
  onStart,
  onStream,
  onCancelBackfill
}) {
  const [count, setCount] = useState(chat.fetched || 0)
  const [date, setDate] = useState(chat.lastDate || 'Jun 7, 2026')
  const [logLine, setLogLine] = useState('Opening MTProto session…')
  const countRef = useRef(chat.fetched || 0)
  const handlersRef = useRef({
    onCancel,
    onCancelBackfill,
    onComplete,
    onStart,
    onStream
  })

  useEffect(() => {
    handlersRef.current = {
      onCancel,
      onCancelBackfill,
      onComplete,
      onStart,
      onStream
    }
  }, [onCancel, onCancelBackfill, onComplete, onStart, onStream])

  const hasBackendBackfill = !!onStart && !!onStream

  useEffect(() => {
    countRef.current = chat.fetched || 0
    setCount(chat.fetched || 0)
    setDate(chat.lastDate || 'Jun 7, 2026')
    setLogLine('Opening MTProto session…')

    if (hasBackendBackfill) {
      let closed = false
      let subscription = null

      async function startBackendBackfill() {
        try {
          await handlersRef.current.onStart(chat.id)
          if (closed) return
          subscription = handlersRef.current.onStream(chat.id, {
            onProgress: (progress) => {
              const nextCount = progress.fetched ?? countRef.current
              countRef.current = nextCount
              setCount(nextCount)
              if (progress.lastDate) setDate(progress.lastDate)
              if (progress.phase) setLogLine(progress.phase)
            },
            onDone: (result) => {
              const total = result.fetched ?? countRef.current
              countRef.current = total
              setCount(total)
              setLogLine('Backfill complete · finalizing index')
              handlersRef.current.onComplete(total)
            },
            onError: (error) => {
              setLogLine(error?.message || 'Backfill stopped.')
            }
          })
        } catch (error) {
          if (!closed) setLogLine(messageFromError(error))
        }
      }

      void startBackendBackfill()

      return () => {
        closed = true
        subscription && subscription.close()
      }
    }

    // Simulated, accelerating backfill that completes after a believable run.
    const TARGET = (chat.fetched || 0) + 9800 + Math.floor(Math.random() * 3000)
    let doneTimer = null
    const dates = [
      'Jun 7, 2026',
      'Jun 4, 2026',
      'May 30, 2026',
      'May 22, 2026',
      'May 11, 2026',
      'Apr 28, 2026',
      'Apr 9, 2026',
      'Mar 21, 2026',
      'Feb 28, 2026',
      'Feb 2, 2026',
      'Jan 9, 2026',
      'Dec 12, 2025',
      'Nov 18, 2025'
    ]
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
        doneTimer = setTimeout(() => handlersRef.current.onComplete(TARGET), 900)
        return
      }
      setCount(countRef.current)
      di = Math.min(
        dates.length - 1,
        Math.floor((countRef.current / TARGET) * dates.length)
      )
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
  }, [chat.fetched, chat.id, chat.lastDate, hasBackendBackfill])

  async function cancelBackfill() {
    try {
      if (handlersRef.current.onCancelBackfill) {
        await handlersRef.current.onCancelBackfill(chat.id)
      }
      handlersRef.current.onCancel(countRef.current, date)
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
        <div className="vrs-bf-title">Backfilling {chat.name}</div>
        <div className="vrs-bf-sub" style={{ marginTop: 6 }}>
          Pulling the full message history from {chat.tag}. This can take a while — you
          can leave and come back.
        </div>
      </div>

      <div className="vrs-bf-stats">
        <div>
          <div className="vrs-bf-stat__v">{count.toLocaleString()}</div>
          <div className="vrs-bf-stat__l">Messages fetched</div>
        </div>
        <div>
          <div
            className="vrs-bf-stat__v"
            style={{ fontSize: 'var(--text-2xl)', paddingTop: 14 }}
          >
            {date}
          </div>
          <div className="vrs-bf-stat__l">Oldest message reached</div>
        </div>
      </div>

      <div className="vrs-bf-track" />
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
