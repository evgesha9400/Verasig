import { get, post } from './client.js'
import { streamJobProgress } from './sse.js'

// Starts the server-side template-mining job for a feed → { jobId }.
export function startMine(token, feedId) {
  return post(`/feeds/${feedId}/mining/preview`, token)
}

// Streams the mine job's staged progress. `onDone(result)` receives
// { groups, messages }; `onProgress` gets { stage, phase, step, totalSteps, count }.
export function streamMineProgress(token, feedId, handlers = {}) {
  return streamJobProgress(token, `/feeds/${feedId}/mining/preview/progress`, handlers)
}

// Confirms accepted templates from an exact current review. The backend persists
// that review's signals and marks the feed verified →
// { feedStatus, templatesAccepted, signalsExtracted }.
export function confirmMining(token, feedId, reviewId, acceptedTemplateKeys = []) {
  return post(`/feeds/${feedId}/mining/confirm`, token, {
    reviewId,
    acceptedTemplateKeys
  })
}

// Reads the latest current review for a feed → { reviewId, inputRevision, groups,
// messages }. Rejects with a 404 ApiError when there is no current review.
export function getMineResult(token, feedId) {
  return get(`/feeds/${feedId}/mining/result`, token)
}

// Lists the accepted template keys already persisted for a feed →
// { acceptedTemplateKeys }. The Verify audit reseeds from these when a
// verified feed is reopened, so it resumes instead of re-mining from scratch.
export function getConfirmedMining(token, feedId) {
  return get(`/feeds/${feedId}/mining/confirmed`, token)
}

// Runs accepted templates over the exact current review snapshot server-side →
// { parsedSignals, ambiguousCandidates, rejectedCandidates, rareTemplates,
// potentialMisses } — the same audit shape the browser used to compute
// client-side from applyAcceptedRules.
export function getMineAudit(token, feedId, reviewId, acceptedTemplateKeys = []) {
  return post(`/feeds/${feedId}/mining/audit`, token, {
    reviewId,
    acceptedTemplateKeys
  })
}
