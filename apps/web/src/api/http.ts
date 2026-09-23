export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(typeof message === 'string' ? message : JSON.stringify(message))
    this.status = status
  }
}

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

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

/** Pulls a filename out of a `Content-Disposition: attachment; filename="..."`
 * header. Returns null if the header is missing or unparseable so callers
 * can fall back to a computed default. */
export function filenameFromContentDisposition(header: string | null): string | null {
  if (!header) return null
  const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(header)
  if (!match) return null
  try {
    return decodeURIComponent(match[1])
  } catch {
    return match[1]
  }
}

/** Fetches a binary response (PDF/document download) with the auth header,
 * the same way apiFetch does for JSON — apiFetch can't be reused directly
 * since it always parses the body as JSON. Errors are surfaced the same
 * way (server's `detail` message, wrapped in ApiError) whenever the server
 * manages to send a JSON error body; otherwise falls back to statusText. */
export async function apiFetchBlob(
  path: string,
  token?: string | null,
): Promise<{ blob: Blob; filename: string | null }> {
  const headers = new Headers()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const response = await fetch(`${API_BASE}${path}`, { headers })
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
  const filename = filenameFromContentDisposition(response.headers.get('Content-Disposition'))
  const blob = await response.blob()
  return { blob, filename }
}
