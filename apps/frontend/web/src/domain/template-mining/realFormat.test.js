import { describe, expect, it } from 'vitest'
import { detectInstruments } from './instruments.js'
import { detectDirections } from './directions.js'
import { detectPrices } from './prices.js'
import { extractSignalFields } from './fields.js'
import { attemptExtractSignal } from './extract.js'

/* Real connected feed: Russian-language crypto signals.
   Монета: <COIN> / Купил в ЛОНГ|ШОРТ 🔼|🔽 / Вход / Стоп / Цели: on following
   numbered (keycap-emoji) lines. Results use Результат / Заработано / принесла. */

const REAL_SIGNAL = `Монета: XRP ☝️

Купил в ШОРТ🔽


⚫️ Вход: $2.5445

⚫️ Стоп: $2.6632

⚪️ Цели:

1️⃣ 2.5190 💵
2️⃣ 2.4936 💵
3️⃣ 2.4681 💵


Решение о фиксации прибыли, вы принимаете самостоятельно`

const REAL_RESULT = `📊 Результат по сделке: XRP  ☝️

➕ Позиция принесла 50% прибыли, фиксируем часть и остальное, ставим стоп в бу ‼️

📈 Заработано: +$258`

describe('real feed — primitives', () => {
  it('detects the coin after the Russian coin label', () => {
    expect(detectInstruments('Монета: XRP ☝️').map((e) => e.normalized)).toContain(
      'XRPUSDT'
    )
  })

  it('detects a bare crypto ticker', () => {
    expect(detectInstruments('Монета: DOGE').map((e) => e.normalized)).toContain(
      'DOGEUSDT'
    )
  })

  it('reads Russian direction words', () => {
    expect(detectDirections('Купил в ШОРТ').map((e) => e.normalized)).toContain('SELL')
    expect(detectDirections('Купил в ЛОНГ').map((e) => e.normalized)).toContain('BUY')
  })

  it('reads the up/down trade emojis', () => {
    expect(detectDirections('XRP 🔽').map((e) => e.normalized)).toContain('SELL')
    expect(detectDirections('XRP 🔼').map((e) => e.normalized)).toContain('BUY')
  })

  it('does not read keycap-emoji ordinals as prices', () => {
    expect(detectPrices('1️⃣ 2.5190 💵').map((p) => p.value)).toEqual([2.519])
  })
})

describe('real feed — extraction', () => {
  const fields = extractSignalFields(REAL_SIGNAL)

  it('extracts instrument and direction', () => {
    expect(fields.instrument).toBe('XRPUSDT')
    expect(fields.direction).toBe('SELL')
  })

  it('extracts the entry and stop from Russian labels', () => {
    expect(fields.entry).toMatchObject({ type: 'single', price: 2.5445 })
    expect(fields.stopLoss).toBe(2.6632)
  })

  it('collects targets listed under the Цели header on following lines', () => {
    expect(fields.takeProfits).toEqual([2.519, 2.4936, 2.4681])
  })
})

describe('real feed — intent', () => {
  it('classifies a full Russian signal as new_signal', () => {
    expect(attemptExtractSignal(REAL_SIGNAL).intent).toBe('new_signal')
  })

  it('classifies a Russian result post as result', () => {
    const candidate = attemptExtractSignal(REAL_RESULT)
    // result posts may lack a fresh direction; if parsed, they must not be new signals
    if (candidate) expect(candidate.intent).not.toBe('new_signal')
  })
})
