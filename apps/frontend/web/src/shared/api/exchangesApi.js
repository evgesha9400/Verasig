import { get, post } from './client.js'

export function listExchanges(token) {
  return get('/exchanges', token)
}

export function connectExchange(token, exchangeId, { apiKey, apiSecret }) {
  return post(`/exchanges/${exchangeId}/connect`, token, { apiKey, apiSecret })
}

export function disconnectExchange(token, exchangeId) {
  return post(`/exchanges/${exchangeId}/disconnect`, token)
}
