import { get, put } from './client.js'

export function getParserOverlay(token) {
  return get('/parser-overlay', token)
}

export function putParserOverlay(token, overlay) {
  return put('/parser-overlay', token, { overlay })
}
