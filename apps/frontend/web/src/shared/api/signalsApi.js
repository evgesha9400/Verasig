import { get, post } from './client.js'

function appendQueryParam(params, key, value) {
  if (value === undefined || value === null || value === '' || value === 'all') return
  params.set(key, value)
}

function createSignalsPath(filters = {}) {
  const params = new URLSearchParams()
  appendQueryParam(params, 'feedId', filters.feedId)
  appendQueryParam(params, 'status', filters.status)
  const query = params.toString()
  return query ? `/signals?${query}` : '/signals'
}

export function listSignals(token, filters = {}) {
  return get(createSignalsPath(filters), token)
}

export function linkSignalModifier(token, signalId, modId) {
  return post(`/signals/${signalId}/link-mod`, token, { modId })
}
