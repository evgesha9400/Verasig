import { useState } from 'react'
import { Button, Icon, Input } from '@verasig/design-system'

const EMPTY = {
  instrumentAliases: {},
  directionTokens: {},
  rejectPhrases: [],
  templateThresholds: {}
}

function normalize(overlay) {
  return { ...EMPTY, ...(overlay || {}) }
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
  const addAlias = () => {
    if (!alias.term || !alias.symbol) return
    save({ instrumentAliases: { ...current.instrumentAliases, [alias.term]: alias.symbol } })
    setAlias({ term: '', symbol: '' })
  }
  const addToken = () => {
    if (!token.term) return
    save({ directionTokens: { ...current.directionTokens, [token.term]: token.side } })
    setToken({ term: '', side: 'BUY' })
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

      <div className="vrs-tm-overlay__group">
        <div className="vrs-tm-overlay__label">Coin aliases</div>
        {Object.entries(current.instrumentAliases).map(([term, symbol]) => (
          <div key={term} className="vrs-tm-overlay__row">
            <span>{term} → <span>{symbol}</span></span>
            <Button
              variant="ghost"
              size="sm"
              aria-label={`Remove alias ${term}`}
              iconLeft={<Icon name="x" size={13} />}
              onClick={() => removeKey('instrumentAliases', term)}
            />
          </div>
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
      </div>

      <div className="vrs-tm-overlay__group">
        <div className="vrs-tm-overlay__label">Direction tokens</div>
        {Object.entries(current.directionTokens).map(([term, side]) => (
          <div key={term} className="vrs-tm-overlay__row">
            <span>
              {term} → {side}
            </span>
            <Button
              variant="ghost"
              size="sm"
              aria-label={`Remove direction token ${term}`}
              iconLeft={<Icon name="x" size={13} />}
              onClick={() => removeKey('directionTokens', term)}
            />
          </div>
        ))}
        <div className="vrs-tm-overlay__add">
          <Input
            placeholder="Token e.g. 🚀"
            value={token.term}
            aria-label="Direction token"
            onChange={(e) => setToken({ ...token, term: e.target.value })}
          />
          <select
            aria-label="Token side"
            value={token.side}
            onChange={(e) => setToken({ ...token, side: e.target.value })}
          >
            <option value="BUY">BUY</option>
            <option value="SELL">SELL</option>
          </select>
          <Button variant="secondary" size="sm" onClick={addToken}>
            Add token
          </Button>
        </div>
      </div>

      <div className="vrs-tm-overlay__group">
        <div className="vrs-tm-overlay__label">Reject phrases</div>
        {current.rejectPhrases.map((value) => (
          <div key={value} className="vrs-tm-overlay__row">
            <span>{value}</span>
            <Button
              variant="ghost"
              size="sm"
              aria-label={`Remove reject phrase ${value}`}
              iconLeft={<Icon name="x" size={13} />}
              onClick={() => removePhrase(value)}
            />
          </div>
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
      </div>
    </section>
  )
}

export default OverlayManager
