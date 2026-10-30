const DEFAULT_API_URL = 'http://localhost:8000'
const API_URL = import.meta.env.VITE_VERASIG_API_URL || DEFAULT_API_URL

export class ApiError extends Error {
  constructor({ status, code, message, details }) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

export function createApiUrl(path) {
  if (/^https?:\/\//.test(path)) return path

  const base = API_URL.replace(/\/$/, '')
  const apiPath = path.startsWith('/') ? path : `/${path}`
  return `${base}${apiPath}`
}

function isFormData(body) {
  return typeof FormData !== 'undefined' && body instanceof FormData
}

function createHeaders({ body, headers = {}, token }) {
  const nextHeaders = { ...headers }

  if (body !== undefined && !isFormData(body) && !nextHeaders['Content-Type']) {
    nextHeaders['Content-Type'] = 'application/json'
  }

  if (token) {
    nextHeaders.Authorization = `Bearer ${token}`
  }

  return nextHeaders
}

function createBody(body) {
  if (body === undefined || isFormData(body)) return body
  return JSON.stringify(body)
}

async function readResponseBody(response) {
  const text = await response.text()
  if (!text) return undefined

  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

function createErrorMessage(payload, fallback) {
  if (payload?.error?.message) return payload.error.message
  if (typeof payload?.detail === 'string') return payload.detail
  if (Array.isArray(payload?.detail)) {
    const validationError = payload.detail.find((item) => typeof item?.msg === 'string')
    if (validationError) {
      const field = validationError.loc
        ?.filter((part) => part !== 'body')
        .map((part) => String(part))
        .join('.')
      if (field) return `${createFieldLabel(field)}: ${validationError.msg}`
      return validationError.msg
    }
  }
  if (typeof payload === 'string') return payload
  return fallback
}

function createFieldLabel(field) {
  return field.charAt(0).toUpperCase() + field.slice(1)
}

function createErrorCode(payload, fallback) {
  if (payload?.error?.code) return payload.error.code
  return fallback
}

function createApiError(response, payload) {
  return new ApiError({
    status: response.status,
    code: createErrorCode(payload, `HTTP_${response.status}`),
    message: createErrorMessage(payload, response.statusText || 'Request failed'),
    details: payload?.detail
  })
}

// Method verbs over requestJson so call sites read as one line. `token` is
// optional (the auth endpoints call without one); a missing `body` sends no body.
export const get = (path, token) => requestJson(path, { token })
export const post = (path, token, body) =>
  requestJson(path, { method: 'POST', token, body })
export const put = (path, token, body) =>
  requestJson(path, { method: 'PUT', token, body })
export const patch = (path, token, body) =>
  requestJson(path, { method: 'PATCH', token, body })
export const del = (path, token) => requestJson(path, { method: 'DELETE', token })

export async function requestJson(path, options = {}) {
  const { body, headers, method = 'GET', token } = options
  const response = await fetch(createApiUrl(path), {
    method,
    headers: createHeaders({ body, headers, token }),
    ...(body !== undefined ? { body: createBody(body) } : {})
  })
  const payload = await readResponseBody(response)

  if (!response.ok) {
    throw createApiError(response, payload)
  }

  return payload
}
