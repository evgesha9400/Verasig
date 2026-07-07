import { get, post } from './client.js'
import { streamJobProgress } from './sse.js'

// Starts the server-side template-mining job for a feed → { jobId }.
export function startMine(token, feedId) {
  return post(`/feeds/${feedId}/mine`, token)
}

// Streams the mine job's staged progress. `onDone(result)` receives
// { groups, messages }; `onProgress` gets { stage, phase, step, totalSteps, count }.
export function streamMineProgress(token, feedId, handlers = {}) {
  return streamJobProgress(token, `/feeds/${feedId}/mine/progress`, handlers)
}

// Confirms the accepted templates. The backend re-mines (identical template keys
// by parity), persists the miner's signals, and marks the feed verified →
// { feedStatus, templatesAccepted, signalsExtracted }.
export function confirmMining(token, feedId, acceptedTemplateKeys = []) {
  return post(`/feeds/${feedId}/mining/confirm`, token, { acceptedTemplateKeys })
}

// Reads the last cached mine result for a feed → { groups, messages }. Reopening
// a verified feed hydrates the Verify audit from this instead of re-mining;
// rejects with a 404 ApiError when no snapshot is cached (fall back to a live mine).
export function getMineResult(token, feedId) {
  return get(`/feeds/${feedId}/mine/result`, token)
}

// Lists the accepted template keys already persisted for a feed →
// { acceptedTemplateKeys }. The Verify audit reseeds from these when a
// verified feed is reopened, so it resumes instead of re-mining from scratch.
export function getConfirmedMining(token, feedId) {
  return get(`/feeds/${feedId}/mining/confirmed`, token)
}
