/* Verasig — Parser-first Template Mining: shared shapes.
   This is a JavaScript codebase, so types are documented as JSDoc typedefs and
   consumed by the editor / type-checker; there is no emitted code. */

/**
 * A raw Telegram message, the unit of input to the miner.
 * @typedef {Object} ChatMessage
 * @property {string} id
 * @property {string} [date]
 * @property {string} text
 * @property {string} [sender]
 * @property {string} [groupId]
 * @property {string} [replyToMessageId]
 */

/**
 * Whitespace/number-normalized view of a message, with the original kept for display.
 * @typedef {Object} NormalizedText
 * @property {string} original   raw input, untouched (display)
 * @property {string} clean      unicode/whitespace/comma-normalized, case preserved
 * @property {string} lower      clean lowercased (matching)
 * @property {string[]} lines    clean split into trimmed, non-empty lines
 */

/**
 * A detected primitive entity (instrument or direction) with its source span.
 * @typedef {Object} DetectedEntity
 * @property {string} raw
 * @property {string} normalized
 * @property {number} [start]
 * @property {number} [end]
 * @property {number} confidence
 */

/**
 * A detected price token — a single level or a min/max range.
 * @typedef {Object} DetectedPrice
 * @property {string} raw
 * @property {number} [value]
 * @property {number} [min]
 * @property {number} [max]
 * @property {'single'|'range'} type
 * @property {number} [start]
 * @property {number} [end]
 */

/** @typedef {'BUY'|'SELL'} Direction */
/** @typedef {'market'|'limit'|'range'|'unknown'} OrderType */
/** @typedef {'new_signal'|'update'|'result'|'commentary'|'unknown'} SignalIntent */

/**
 * A parsed entry level.
 * @typedef {Object} SignalEntry
 * @property {'single'|'range'|'market'|'unknown'} type
 * @property {number} [price]
 * @property {number} [min]
 * @property {number} [max]
 * @property {string} [raw]
 */

/**
 * The structured signal a message parses into.
 * @typedef {Object} StructuredSignal
 * @property {string[]} sourceMessageIds
 * @property {string} instrument
 * @property {string} [instrumentRaw]
 * @property {Direction} direction
 * @property {OrderType} orderType
 * @property {SignalEntry|null} entry
 * @property {number|null} stopLoss
 * @property {number[]} takeProfits
 * @property {number} confidence
 * @property {string} [parserRuleId]
 * @property {SignalIntent} intent
 */

/**
 * A candidate: a message that cleared the minimum bar (instrument + direction)
 * plus everything the miner extracted from it.
 * @typedef {Object} Candidate
 * @property {ChatMessage} message
 * @property {DetectedEntity[]} instruments
 * @property {DetectedEntity[]} directions
 * @property {DetectedPrice[]} prices
 * @property {Partial<StructuredSignal>} fields
 * @property {SignalIntent} intent
 * @property {number} confidence
 * @property {string[]} rejectionReasons
 * @property {string} templateKey
 * @property {string} normalizedTemplate
 */

/**
 * A family of candidates that share one normalized template.
 * @typedef {Object} TemplateGroup
 * @property {string} id
 * @property {string} templateKey
 * @property {string} normalizedTemplate
 * @property {Candidate[]} candidates
 * @property {Candidate[]} examples
 * @property {number} count
 * @property {{from?: string, to?: string}} [dateRange]
 * @property {number} confidenceAvg
 * @property {{new_signal:number, update:number, result:number, commentary:number, unknown:number}} intentDistribution
 * @property {'unreviewed'|'accepted'|'rejected'} status
 * @property {'accept'|'review'|'reject'} suggestedAction
 * @property {ParserRule} [compiledRule]
 */

/**
 * A deterministic parser rule compiled from an accepted template group.
 * @typedef {Object} ParserRule
 * @property {string} id
 * @property {string} name
 * @property {string} templateKey
 * @property {string[]} required
 * @property {{instrument:string, direction:string, entry?:string, stopLoss?:string, takeProfits?:string}} fields
 * @property {string[]} rejectIfContains
 * @property {number} confidenceThreshold
 */

export {}
