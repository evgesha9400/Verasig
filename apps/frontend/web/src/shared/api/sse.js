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
  // The base resolves a same-origin API URL such as /api (the deployed site).
  const url = new URL(createApiUrl(path), window.location.origin)
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
    // EventSource fires 'error' on transient disconnects too (it then auto-
    // reconnects). Only treat a server-sent error event (carrying data) or a
    // fully-closed stream as terminal; let transient blips reconnect.
    const terminal = event.data != null || source.readyState === EventSource.CLOSED
    if (!terminal) return
    handlers.onError && handlers.onError(parseEventData(event))
    source.close()
  })

  return {
    close: () => source.close()
  }
}
