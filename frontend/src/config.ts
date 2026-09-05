// @ts-ignore
export const API_URL: string = import.meta.env.VITE_API_URL || 'http://localhost:8000'
// @ts-ignore
export const API_KEY: string = import.meta.env.VITE_API_KEY || ''

// Fail-fast in production: a missing VITE_API_URL silently bakes
// http://localhost:8000 into the bundle; browsers block it as mixed
// content from an https:// origin -> cryptic "Failed to fetch".
if (import.meta.env.PROD && !import.meta.env.VITE_API_URL) {
  console.error(
    '[TieBreaker] VITE_API_URL is not set — this build is calling ' +
    'http://localhost:8000, which browsers block. Set VITE_API_URL in ' +
    'Vercel (Settings → Environment Variables) and REDEPLOY.'
  )
}

export function apiHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const headers: Record<string, string> = { ...extra }
  if (API_KEY) headers['X-API-Key'] = API_KEY
  return headers
}

// Turns opaque fetch TypeErrors into an actionable message.
export function friendlyFetchError(err: unknown): string {
  if (err instanceof TypeError) {
    return `Cannot reach backend at ${API_URL}. Check VITE_API_URL in Vercel, ` +
      `that the Railway service is awake, and DevTools → Console for CORS errors.`
  }
  return err instanceof Error ? err.message : 'Unknown error'
}