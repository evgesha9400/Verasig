/* Verasig — Template Mining: adapter for the connected Telegram feed's messages.
   The demo seed's Label/Verify deck (the Apex feed history) is reshaped into the
   ChatMessage contract the miner consumes, so the prototype can run against the
   same data the rest of the app uses — not only the bundled sample. */

import { MESSAGES } from '../demo-data/seed.js'

/**
 * @param {Array} seedMessages
 * @returns {import('./types.js').ChatMessage[]}
 */
export function toChatMessages(seedMessages) {
  return (seedMessages || []).map((seed) => ({
    id: seed.id,
    date: [seed.date, seed.time].filter(Boolean).join(' ') || undefined,
    text: seed.text,
    sender: seed.author,
    replyToMessageId: seed.replyTo ? `${seed.id}-parent` : undefined
  }))
}

/** The added Telegram feed's messages (Apex Crypto Calls demo history). */
export const FEED_MESSAGES = toChatMessages(MESSAGES)
