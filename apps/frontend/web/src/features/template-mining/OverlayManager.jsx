import { useState } from 'react'
import { Button, Icon, Input, Select } from '@verasig/design-system'

const EMPTY = {
  instrumentAliases: {},
  directionTokens: {},
  rejectPhrases: [],
  templateThresholds: {}
}

function normalize(overlay) {
  return { ...EMPTY, ...(overlay || {}) }
}

// A taught entry (alias, direction token, or reject phrase) plus its remove
// button — the one row shape every group in this manager lists.
function OverlayRow({ label, removeLabel, onRemove }) {
  return (
    <div className="vrs-tm-overlay__row">
      <span>{label}</span>
      <Button
        variant="ghost"
        size="sm"
        aria-label={removeLabel}
        iconLeft={<Icon name="x" size={13} />}
        onClick={onRemove}
      />
    </div>
  )
}

// The shell every taught-entry group shares: a label over its rows and "add"
// controls. What's inside (the rows, the add form) differs per group and is
// passed as children rather than forced into a one-size-fits-all row renderer.
function OverlayGroup({ label, children }) {
  return (
    <div className="vrs-tm-overlay__group">
      <div className="vrs-tm-overlay__label">{label}</div>
      {children}
    </div>
  )
}

export function OverlayManager({ overlay, onSave }) {
  const current = normalize(overlay)
  const [alias, setAlias] = useState({ term: '', symbol: '' })
  const [token, setToken] = useState({ term: '', side: 'BUY' })
  const [phrase, setPhrase] = useState('')

  const save = (patch) => onSave({ ...current, ...patch })

  const removeKey = (mapName, key) => {
    const next = { ...current[mapName] }
    delete next[key]
    save({ [mapName]: next })
  }
  const addMapEntry = (mapName, key, value, resetState) => {
    save({ [mapName]: { ...current[mapName], [key]: value } })
    resetState()
  }
  const addAlias = () => {
    if (!alias.term || !alias.symbol) return
    addMapEntry('instrumentAliases', alias.term, alias.symbol, () =>
      setAlias({ term: '', symbol: '' })
    )
  }
  const addToken = () => {
    if (!token.term) return
    addMapEntry('directionTokens', token.term, token.side, () =>
      setToken({ term: '', side: 'BUY' })
    )
  }
  const addPhrase = () => {
    if (!phrase.trim()) return
    save({ rejectPhrases: [...current.rejectPhrases, phrase.trim()] })
    setPhrase('')
  }
  const removePhrase = (value) =>
    save({ rejectPhrases: current.rejectPhrases.filter((p) => p !== value) })

  return (
    <section className="vrs-tm-overlay">
      <div className="vrs-tm-section__head">
        <div>
          <div className="vrs-tm-section__title">Taught to the parser</div>
          <div className="vrs-tm-section__sub">
            Custom coins, direction tokens and reject phrases applied to every mine
          </div>
        </div>
      </div>

      <OverlayGroup label="Coin aliases">
        {Object.entries(current.instrumentAliases).map(([term, symbol]) => (
          <OverlayRow
            key={term}
            label={
              <>
                {term} → <span>{symbol}</span>
              </>
            }
            removeLabel={`Remove alias ${term}`}
            onRemove={() => removeKey('instrumentAliases', term)}
          />
        ))}
        <div className="vrs-tm-overlay__add">
          <Input
            placeholder="Alias e.g. АПТ"
            value={alias.term}
            aria-label="Alias term"
            onChange={(e) => setAlias({ ...alias, term: e.target.value })}
          />
          <Input
            placeholder="Symbol e.g. APTUSDT"
            value={alias.symbol}
            aria-label="Alias symbol"
            onChange={(e) => setAlias({ ...alias, symbol: e.target.value })}
          />
          <Button variant="secondary" size="sm" onClick={addAlias}>
            Add alias
          </Button>
        </div>
      </OverlayGroup>

      <OverlayGroup label="Direction tokens">
        {Object.entries(current.directionTokens).map(([term, side]) => (
          <OverlayRow
            key={term}
            label={
              <>
                {term} → {side}
              </>
            }
            removeLabel={`Remove direction token ${term}`}
            onRemove={() => removeKey('directionTokens', term)}
          />
        ))}
        <div className="vrs-tm-overlay__add">
          <Input
            placeholder="Token e.g. 🚀"
            value={token.term}
            aria-label="Direction token"
            onChange={(e) => setToken({ ...token, term: e.target.value })}
          />
          <Select
            aria-label="Token side"
            value={token.side}
            onChange={(e) => setToken({ ...token, side: e.target.value })}
            options={[
              { value: 'BUY', label: 'BUY' },
              { value: 'SELL', label: 'SELL' }
            ]}
          />
          <Button variant="secondary" size="sm" onClick={addToken}>
            Add token
          </Button>
        </div>
      </OverlayGroup>

      <OverlayGroup label="Reject phrases">
        {current.rejectPhrases.map((value) => (
          <OverlayRow
            key={value}
            label={value}
            removeLabel={`Remove reject phrase ${value}`}
            onRemove={() => removePhrase(value)}
          />
        ))}
        <div className="vrs-tm-overlay__add">
          <Input
            placeholder="Add reject phrase"
            value={phrase}
            aria-label="Reject phrase"
            onChange={(e) => setPhrase(e.target.value)}
          />
          <Button variant="secondary" size="sm" onClick={addPhrase}>
            Add reject phrase
          </Button>
        </div>
      </OverlayGroup>
    </section>
  )
}

export default OverlayManager
