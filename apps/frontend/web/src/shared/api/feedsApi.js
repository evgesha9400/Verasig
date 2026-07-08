import { del, get, post } from './client.js'
import { streamJobProgress } from './sse.js'

export function listFeeds(token) {
  return get('/feeds', token)
}

export function createFeed(token, tag) {
  return post('/feeds', token, { tag })
}

export function deleteFeed(token, feedId) {
  return del(`/feeds/${feedId}`, token)
}

export function startBackfill(token, feedId, mode = 'resume', depth = null) {
  return post(`/feeds/${feedId}/backfill`, token, {
    mode,
    ...(depth != null ? { depth } : {})
  })
}

export function cancelBackfill(token, feedId) {
  return post(`/feeds/${feedId}/backfill/cancel`, token)
}

export function streamBackfillProgress(token, feedId, handlers = {}) {
  return streamJobProgress(token, `/feeds/${feedId}/backfill/progress`, handlers)
}

export function startDeletionRescan(token, feedId) {
  return post(`/feeds/${feedId}/deletion-rescan`, token)
}

export function streamDeletionRescanProgress(token, feedId, handlers = {}) {
  return streamJobProgress(token, `/feeds/${feedId}/deletion-rescan/progress`, handlers)
}
