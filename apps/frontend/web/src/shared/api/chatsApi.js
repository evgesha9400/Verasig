import { requestJson } from './client.js'
import { streamJobProgress } from './sse.js'

export function listChats(token) {
  return requestJson('/chats', { token })
}

export function createChat(token, tag) {
  return requestJson('/chats', {
    method: 'POST',
    token,
    body: { tag }
  })
}

export function deleteChat(token, chatId) {
  return requestJson(`/chats/${chatId}`, {
    method: 'DELETE',
    token
  })
}

export function startBackfill(token, chatId, mode = 'resume') {
  return requestJson(`/chats/${chatId}/backfill`, {
    method: 'POST',
    token,
    body: { mode }
  })
}

export function cancelBackfill(token, chatId) {
  return requestJson(`/chats/${chatId}/backfill/cancel`, {
    method: 'POST',
    token
  })
}

export function streamBackfillProgress(token, chatId, handlers = {}) {
  return streamJobProgress(token, `/chats/${chatId}/backfill/progress`, handlers)
}
