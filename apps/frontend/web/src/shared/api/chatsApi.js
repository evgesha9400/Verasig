import { createApiUrl, requestJson } from './client.js'

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

export function startBackfill(token, chatId) {
  return requestJson(`/chats/${chatId}/backfill`, {
    method: 'POST',
    token
  })
}

export function cancelBackfill(token, chatId) {
  return requestJson(`/chats/${chatId}/backfill/cancel`, {
    method: 'POST',
    token
  })
}

function parseEventData(event) {
  if (!event.data) return {}
  return JSON.parse(event.data)
}

function createProgressUrl(token, chatId) {
  const url = new URL(createApiUrl(`/chats/${chatId}/backfill/progress`))
  url.searchParams.set('token', token)
  return url.toString()
}

export function streamBackfillProgress(token, chatId, handlers = {}) {
  const source = new EventSource(createProgressUrl(token, chatId))

  source.addEventListener('progress', (event) => {
    handlers.onProgress && handlers.onProgress(parseEventData(event))
  })
  source.addEventListener('done', (event) => {
    handlers.onDone && handlers.onDone(parseEventData(event))
    source.close()
  })
  source.addEventListener('error', (event) => {
    handlers.onError && handlers.onError(parseEventData(event))
    source.close()
  })

  return {
    close: () => source.close()
  }
}
