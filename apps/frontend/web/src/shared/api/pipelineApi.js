import { requestJson } from './client.js'
import { streamJobProgress } from './sse.js'

export function listMessages(token, chatId, limit) {
  const query = typeof limit === 'number' ? `?limit=${limit}` : ''
  return requestJson(`/chats/${chatId}/messages${query}`, { token })
}

export function recordLabel(token, chatId, msgId, label) {
  return requestJson(`/chats/${chatId}/messages/${msgId}/label`, {
    method: 'POST',
    token,
    body: { label }
  })
}

export function getLabelCounts(token, chatId) {
  return requestJson(`/chats/${chatId}/labels`, { token })
}

export function startDistill(token, chatId) {
  return requestJson(`/chats/${chatId}/distill`, { method: 'POST', token })
}

export function streamDistillProgress(token, chatId, handlers = {}) {
  return streamJobProgress(token, `/chats/${chatId}/distill/progress`, handlers)
}

export function getRules(token, chatId) {
  return requestJson(`/chats/${chatId}/rules`, { token })
}
