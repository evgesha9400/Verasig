import { useEffect, useRef, useState } from 'react'

/* Verasig — server-side template-mining loader. Starts the mine job and streams
   its staged progress until the mined families arrive, then hands the result up.
   Mirrors BackfillView's backend branch (and reuses its progress styling) so the
   two loaders read the same. Under limited resources mining can be slow — this
   screen keeps the operator informed while it runs. */

const MINE_STAGES = [
  { id: 'loading', label: 'Loading history' },
  { id: 'extracting', label: 'Extracting candidates' },
  { id: 'grouping', label: 'Grouping families' }
]

function StageStrip({ stage }) {
  const activeIndex = MINE_STAGES.findIndex((item) => item.id === stage)
  return (
    <div className="vrs-bf-stages">
      {MINE_STAGES.map((item, index) => (
        <span
          key={item.id}
          className={`vrs-bf-stage ${index === activeIndex ? 'is-active' : ''} ${
            index < activeIndex ? 'is-done' : ''
          }`.trim()}
        >
          {item.label}
        </span>
      ))}
    </div>
  )
}

export function MineView({ feed, onStart, onStream, onDone, onError }) {
  const [count, setCount] = useState(0)
  const [stage, setStage] = useState('loading')
  const [logLine, setLogLine] = useState('Starting the miner…')
  const handlersRef = useRef({ onStart, onStream, onDone, onError })

  useEffect(() => {
    handlersRef.current = { onStart, onStream, onDone, onError }
  }, [onStart, onStream, onDone, onError])

  useEffect(() => {
    let closed = false
    let subscription = null

    async function run() {
      try {
        await handlersRef.current.onStart(feed.id)
        if (closed) return
        subscription = handlersRef.current.onStream(feed.id, {
          onProgress: (progress) => {
            if (progress.stage) setStage(progress.stage)
            if (progress.phase) setLogLine(progress.phase)
            // Message count is meaningful through extraction; grouping reports a
            // family count, so leave the scanned total steady after that.
            if (
              typeof progress.count === 'number' &&
              (progress.stage === 'loading' || progress.stage === 'extracting')
            ) {
              setCount(progress.count)
            }
          },
          onDone: (result) => {
            handlersRef.current.onDone(result || { groups: [], messages: [] })
          },
          onError: (error) => {
            handlersRef.current.onError(error || {})
          }
        })
      } catch (error) {
        if (!closed) {
          handlersRef.current.onError({ message: error?.message || 'Mining failed.' })
        }
      }
    }

    void run()
    return () => {
      closed = true
      subscription && subscription.close()
    }
    // Keyed on the feed only: re-runs when the active feed changes.
  }, [feed.id])

  return (
    <div className="vrs-backfill vrs-fade-in">
      <div>
        <div className="vrs-bf-title">Mining {feed.name}</div>
        <div className="vrs-bf-sub" style={{ marginTop: 6 }}>
          Discovering the signal formats in {feed.tag}. This runs on the server — you
          can leave and come back.
        </div>
      </div>

      <div className="vrs-bf-stats">
        <div>
          <div className="vrs-bf-stat__v">{count.toLocaleString()}</div>
          <div className="vrs-bf-stat__l">Messages scanned</div>
        </div>
      </div>

      <StageStrip stage={stage} />
      <div className="vrs-bf-track" />
      <div className="vrs-bf-log">{logLine}</div>
    </div>
  )
}
