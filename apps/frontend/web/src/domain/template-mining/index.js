/* Verasig — Template Mining: public surface of the parser-first miner.
   Pure, deterministic, local. The UI imports only from here. */

export { normalizeMessageText } from './text.js'
export { detectInstruments } from './instruments.js'
export { detectDirections } from './directions.js'
export { detectPrices, parseNumber } from './prices.js'
export { extractSignalFields, hasTradingLabel } from './fields.js'
export { classifyIntent } from './intent.js'
export { scoreCandidate } from './scoring.js'
export { validatePriceGeometry } from './geometry.js'
export { attemptExtractSignal } from './extract.js'
export { normalizeTemplate } from './template.js'
export { mineTemplateGroups } from './mining.js'
export { applyAcceptedRules, compileRuleFromTemplate, formatLabel } from './rules.js'
export { SAMPLE_MESSAGES } from './sampleMessages.js'
export { FEED_MESSAGES, toChatMessages } from './feedMessages.js'
