import { Button, Card, Icon, SegmentedControl } from '@verasig/design-system'

/* Verasig — Template Mining: source selector + run trigger.
   Works fully offline: the connected feed's history, a bundled sample, or pasted
   text (one message per blank line). */
const SOURCE_OPTIONS = [
  { value: 'feed', label: 'Telegram feed' },
  { value: 'sample', label: 'Sample dataset' },
  { value: 'paste', label: 'Paste messages' }
]

function sourceHint(source, feedLabel, feedCount, sampleCount, pastedCount) {
  if (source === 'feed') {
    return `${feedCount} messages from ${feedLabel}`
  }
  if (source === 'sample') {
    return `${sampleCount} representative messages across signal, update, result and noise formats`
  }
  return `${pastedCount} message${pastedCount === 1 ? '' : 's'} detected — separate each with a blank line`
}

export function MiningSourcePanel({
  source,
  onSourceChange,
  pasted,
  onPastedChange,
  feedLabel,
  feedCount,
  sampleCount,
  pastedCount,
  running,
  canRun,
  onRun
}) {
  return (
    <Card title="Source" subtitle="Choose what to mine, then run the parser-first pass">
      <div className="vrs-tm-source">
        <div className="vrs-tm-source__row">
          <SegmentedControl
            value={source}
            onChange={onSourceChange}
            options={SOURCE_OPTIONS}
            label="Message source"
          />
          <span className="vrs-tm-source__hint">
            {sourceHint(source, feedLabel, feedCount, sampleCount, pastedCount)}
          </span>
        </div>

        {source === 'paste' && (
          <textarea
            className="vrs-tm-source__area"
            value={pasted}
            onChange={(event) => onPastedChange(event.target.value)}
            placeholder={
              'XAUUSD BUY NOW\nSL 2312\nTP 2340\nTP 2355\n\nSell EURUSD 1.0860-1.0870\nSL 1.0900\nTP 1.0800'
            }
            spellCheck={false}
          />
        )}

        <div className="vrs-tm-source__row">
          <Button
            variant="primary"
            iconLeft={<Icon name="sparkles" size={16} />}
            onClick={onRun}
            loading={running}
            disabled={!canRun}
          >
            Run template mining
          </Button>
        </div>
      </div>
    </Card>
  )
}
