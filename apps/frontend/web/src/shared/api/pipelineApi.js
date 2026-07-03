import { requestJson } from './client.js'

// The full backfilled history (every message, unfiltered) for the parser-first miner.
export function listFeedHistory(token, chatId) {
  return requestJson(`/feeds/${chatId}/messages/history`, { token })
}

export function getParserOverlay(token) {
  return requestJson(`/parser-overlay`, { token })
}

export function putParserOverlay(token, overlay) {
  return requestJson(`/parser-overlay`, { method: 'PUT', token, body: { overlay } })
}
