// @ts-ignore
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
// @ts-ignore
export const API_KEY = import.meta.env.VITE_API_KEY || ''

export function apiHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const headers: Record<string, string> = { ...extra }
  if (API_KEY) {
    headers['X-API-Key'] = API_KEY
  }
  return headers
}
