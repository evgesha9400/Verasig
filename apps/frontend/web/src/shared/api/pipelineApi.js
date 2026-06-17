import { requestJson } from './client.js'
import { streamJobProgress } from './sse.js'

export function listMessages(token, chatId, limit) {
  const query = typeof limit === 'number' ? `?limit=${limit}` : ''
  return requestJson(`/feeds/${chatId}/messages${query}`, { token })
}

export function recordLabel(token, chatId, msgId, label) {
  return requestJson(`/feeds/${chatId}/messages/${msgId}/label`, {
    method: 'POST',
    token,
    body: { label }
  })
}

export function getLabelCounts(token, chatId) {
  return requestJson(`/feeds/${chatId}/labels`, { token })
}

export function startDistill(token, chatId) {
  return requestJson(`/feeds/${chatId}/distill`, { method: 'POST', token })
}

export function streamDistillProgress(token, chatId, handlers = {}) {
  return streamJobProgress(token, `/feeds/${chatId}/distill/progress`, handlers)
}

export function getRules(token, chatId) {
  return requestJson(`/feeds/${chatId}/rules`, { token })
}

export function getVerifySamples(token, chatId) {
  return requestJson(`/feeds/${chatId}/verify/samples`, { token })
}

export function submitVerify(token, chatId, verdicts) {
  return requestJson(`/feeds/${chatId}/verify`, {
    method: 'POST',
    token,
    body: { verdicts }
  })
}
