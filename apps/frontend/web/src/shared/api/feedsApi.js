import { requestJson } from './client.js'
import { streamJobProgress } from './sse.js'

export function listFeeds(token) {
  return requestJson('/feeds', { token })
}

export function createFeed(token, tag) {
  return requestJson('/feeds', {
    method: 'POST',
    token,
    body: { tag }
  })
}

export function deleteFeed(token, feedId) {
  return requestJson(`/feeds/${feedId}`, {
    method: 'DELETE',
    token
  })
}

export function startBackfill(token, feedId, mode = 'resume') {
  return requestJson(`/feeds/${feedId}/backfill`, {
    method: 'POST',
    token,
    body: { mode }
  })
}

export function cancelBackfill(token, feedId) {
  return requestJson(`/feeds/${feedId}/backfill/cancel`, {
    method: 'POST',
    token
  })
}

export function streamBackfillProgress(token, feedId, handlers = {}) {
  return streamJobProgress(token, `/feeds/${feedId}/backfill/progress`, handlers)
}

export function startDeletionRescan(token, feedId) {
  return requestJson(`/feeds/${feedId}/deletion-rescan`, {
    method: 'POST',
    token
  })
}

export function streamDeletionRescanProgress(token, feedId, handlers = {}) {
  return streamJobProgress(token, `/feeds/${feedId}/deletion-rescan/progress`, handlers)
}
