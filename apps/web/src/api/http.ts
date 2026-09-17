export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(typeof message === 'string' ? message : JSON.stringify(message))
    this.status = status
  }
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

// http(s)://host -> ws(s)://host, same base the REST calls above use -
// keeps the WebSocket client (realChatApi.ts) from duplicating base-URL
// resolution or getting out of sync with VITE_API_BASE_URL.
export function apiWsUrl(path: string): string {
  const base = API_BASE || window.location.origin
  return `${base.replace(/^http/, 'ws')}${path}`
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
  token?: string | null,
): Promise<T> {
  const headers = new Headers(init.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (!(init.body instanceof URLSearchParams) && init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${API_BASE}${path}`, { ...init, headers })
  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = await response.json()
      detail = body.detail ?? detail
    } catch {
      // response had no JSON body
    }
    throw new ApiError(response.status, detail)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}
