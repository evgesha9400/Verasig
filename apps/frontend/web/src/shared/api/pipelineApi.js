import { requestJson } from './client.js'

export function listMessages(token, chatId, limit) {
  const query = limit ? `?limit=${limit}` : ''
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
