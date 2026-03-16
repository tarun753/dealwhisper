const BACKEND_TOKEN = import.meta.env.VITE_DEALWHISPER_BACKEND_TOKEN?.trim() ?? ''

function normalizeWsBase(wsBase: string) {
  return wsBase.replace(/\/$/, '')
}

export function buildWsEndpoint(wsBase: string, callId: string) {
  const endpoint = new URL(`${normalizeWsBase(wsBase)}/${callId}`)
  if (BACKEND_TOKEN) {
    endpoint.searchParams.set('token', BACKEND_TOKEN)
  }
  return endpoint.toString()
}

export function buildApiEndpoint(wsBase: string, path: string) {
  const httpBase = normalizeWsBase(wsBase)
    .replace(/^wss:/i, 'https:')
    .replace(/^ws:/i, 'http:')
    .replace(/\/ws\/call$/, '')

  return `${httpBase}${path.startsWith('/') ? path : `/${path}`}`
}

export function getBackendAuthHeaders() {
  return BACKEND_TOKEN ? { Authorization: `Bearer ${BACKEND_TOKEN}` } : {}
}

export async function fetchJsonWithAuth<T>(url: string, init?: RequestInit) {
  const headers = new Headers(init?.headers)
  headers.set('Content-Type', 'application/json')
  Object.entries(getBackendAuthHeaders()).forEach(([key, value]) => {
    headers.set(key, value)
  })

  const response = await fetch(url, {
    ...init,
    headers,
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `Request failed with ${response.status}`)
  }

  return (await response.json()) as T
}
