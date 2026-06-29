import { Button, Card, Icon, SegmentedControl, Select } from '@verasig/design-system'

/* Verasig — Template Mining: source selector + run trigger.
   The Telegram-feed source reuses the messages already stored for the connected
   feed (fetched on run); offline it falls back to the bundled demo history. A
   sample dataset and a paste box keep the prototype usable with no backend. */
const SOURCE_OPTIONS = [
  { value: 'feed', label: 'Telegram feed' },
  { value: 'sample', label: 'Sample dataset' },
  { value: 'paste', label: 'Paste messages' }
]

function feedHint(authenticated, selectedFeedName, demoFeedCount) {
  const name = selectedFeedName || 'the connected feed'
  return authenticated
    ? `Stored messages from ${name}`
    : `${demoFeedCount} demo messages from ${name}`
}

function sourceHint(props) {
  if (props.source === 'feed') {
    return feedHint(props.authenticated, props.selectedFeedName, props.demoFeedCount)
  }
  if (props.source === 'sample') {
    return `${props.sampleCount} representative messages across signal, update, result and noise formats`
  }
  const { pastedCount } = props
  return `${pastedCount} message${pastedCount === 1 ? '' : 's'} detected — separate each with a blank line`
}

export function MiningSourcePanel(props) {
  const {
    source,
    onSourceChange,
    pasted,
    onPastedChange,
    feeds,
    feedId,
    onFeedChange,
    running,
    canRun,
    onRun
  } = props

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
          {source === 'feed' && feeds.length > 1 && (
            <Select
              label="Feed"
              value={feedId || ''}
              onChange={(event) => onFeedChange(event.target.value)}
              options={feeds.map((feed) => ({ value: feed.id, label: feed.name }))}
            />
          )}
          <span className="vrs-tm-source__hint">{sourceHint(props)}</span>
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
            disabled={!canRun || running}
          >
            Run template mining
          </Button>
        </div>
      </div>
    </Card>
  )
}
