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
function OverlayRow({ label, removeLabel, onRemove, disabled }) {
  return (
    <div className="vrs-tm-overlay__row">
      <span>{label}</span>
      <Button
        variant="ghost"
        size="sm"
        aria-label={removeLabel}
        iconLeft={<Icon name="x" size={13} />}
        disabled={disabled}
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

export function OverlayManager({ overlay, onSave, pending = false, error = null }) {
  const current = normalize(overlay)
  const [alias, setAlias] = useState({ term: '', symbol: '' })
  const [token, setToken] = useState({ term: '', side: 'BUY' })
  const [phrase, setPhrase] = useState('')

  const save = (patch) => onSave({ ...current, ...patch })

  async function saveAndReset(patch, resetState) {
    try {
      await save(patch)
      resetState?.()
    } catch {
      // The owning page renders the failure. Keeping local input state intact
      // leaves the same mutation ready to retry.
    }
  }

  const removeKey = (mapName, key) => {
    const next = { ...current[mapName] }
    delete next[key]
    void saveAndReset({ [mapName]: next })
  }
  const addMapEntry = (mapName, key, value, resetState) => {
    void saveAndReset({ [mapName]: { ...current[mapName], [key]: value } }, resetState)
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
    const trimmed = phrase.trim()
    if (!trimmed || current.rejectPhrases.includes(trimmed)) return
    void saveAndReset({ rejectPhrases: [...current.rejectPhrases, trimmed] }, () =>
      setPhrase('')
    )
  }
  const removePhrase = (value) =>
    void saveAndReset({
      rejectPhrases: current.rejectPhrases.filter((p) => p !== value)
    })

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
            disabled={pending}
            onRemove={() => removeKey('instrumentAliases', term)}
          />
        ))}
        <div className="vrs-tm-overlay__add">
          <Input
            placeholder="Alias e.g. АПТ"
            value={alias.term}
            aria-label="Alias term"
            disabled={pending}
            onChange={(e) => setAlias({ ...alias, term: e.target.value })}
          />
          <Input
            placeholder="Symbol e.g. APTUSDT"
            value={alias.symbol}
            aria-label="Alias symbol"
            disabled={pending}
            onChange={(e) => setAlias({ ...alias, symbol: e.target.value })}
          />
          <Button variant="secondary" size="sm" disabled={pending} onClick={addAlias}>
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
            disabled={pending}
            onRemove={() => removeKey('directionTokens', term)}
          />
        ))}
        <div className="vrs-tm-overlay__add">
          <Input
            placeholder="Token e.g. 🚀"
            value={token.term}
            aria-label="Direction token"
            disabled={pending}
            onChange={(e) => setToken({ ...token, term: e.target.value })}
          />
          <Select
            aria-label="Token side"
            value={token.side}
            disabled={pending}
            onChange={(e) => setToken({ ...token, side: e.target.value })}
            options={[
              { value: 'BUY', label: 'BUY' },
              { value: 'SELL', label: 'SELL' }
            ]}
          />
          <Button variant="secondary" size="sm" disabled={pending} onClick={addToken}>
            Add token
          </Button>
        </div>
      </OverlayGroup>

      <OverlayGroup label="Reject phrases">
        {[...new Set(current.rejectPhrases)].map((value) => (
          <OverlayRow
            key={value}
            label={value}
            removeLabel={`Remove reject phrase ${value}`}
            disabled={pending}
            onRemove={() => removePhrase(value)}
          />
        ))}
        <div className="vrs-tm-overlay__add">
          <Input
            placeholder="Add reject phrase"
            value={phrase}
            aria-label="Reject phrase"
            disabled={pending}
            onChange={(e) => setPhrase(e.target.value)}
          />
          <Button variant="secondary" size="sm" disabled={pending} onClick={addPhrase}>
            Add reject phrase
          </Button>
        </div>
      </OverlayGroup>

      {error && (
        <div className="vrs-empty vrs-empty--sm" role="alert">
          <div className="vrs-empty__note">
            Couldn&apos;t save parser teaching. {error}
          </div>
        </div>
      )}
    </section>
  )
}

export default OverlayManager
