import { requestJson } from './client.js'
import { streamJobProgress } from './sse.js'

// Starts the server-side template-mining job for a feed → { jobId }.
export function startMine(token, feedId) {
  return requestJson(`/feeds/${feedId}/mine`, {
    method: 'POST',
    token
  })
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
  return requestJson(`/feeds/${feedId}/mining/confirm`, {
    method: 'POST',
    token,
    body: { acceptedTemplateKeys }
  })
}
