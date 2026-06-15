import { createApiUrl } from './client.js'

function parseEventData(event) {
  if (!event.data) return {}
  try {
    return JSON.parse(event.data)
  } catch {
    return {}
  }
}

function progressUrl(token, path) {
  const url = new URL(createApiUrl(path))
  url.searchParams.set('token', token)
  return url.toString()
}

export function streamJobProgress(token, path, handlers = {}) {
  const source = new EventSource(progressUrl(token, path))

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
