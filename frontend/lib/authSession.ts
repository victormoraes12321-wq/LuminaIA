export const COOKIE_SESSION_TOKEN = '__lumina_cookie_session__'

export function buildAuthHeaders(
  token: string | null,
  headers: HeadersInit = {},
): HeadersInit {
  if (!token) return headers
  return {
    ...headers,
    Authorization: `Bearer ${token}`,
  }
}

export function withAuthCredentials(init: RequestInit = {}): RequestInit {
  return {
    ...init,
    credentials: 'include',
  }
}
