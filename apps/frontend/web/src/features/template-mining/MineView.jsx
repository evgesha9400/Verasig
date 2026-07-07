import { useState } from 'react'
import { StageStrip } from '../../shared/jobs/StageStrip.jsx'
import { useJobStream } from '../../shared/jobs/useJobStream.js'

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

export function MineView({ feed, onStart, onStream, onDone, onError }) {
  const [count, setCount] = useState(0)
  const [stage, setStage] = useState('loading')
  const [logLine, setLogLine] = useState('Starting the miner…')

  useJobStream({
    feedId: feed.id,
    start: onStart,
    stream: onStream,
    tolerate409: true,
    onProgress: (progress) => {
      if (progress.stage) setStage(progress.stage)
      if (progress.phase) setLogLine(progress.phase)
      // Message count is meaningful through extraction; grouping reports a family
      // count, so leave the scanned total steady after that.
      if (
        typeof progress.count === 'number' &&
        (progress.stage === 'loading' || progress.stage === 'extracting')
      ) {
        setCount(progress.count)
      }
    },
    onDone: (result) => onDone(result || { groups: [], messages: [] }),
    onError: (error) => onError(error || {})
  })

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

      <StageStrip stages={MINE_STAGES} stage={stage} />
      <div className="vrs-bf-track" />
      <div className="vrs-bf-log">{logLine}</div>
    </div>
  )
}
