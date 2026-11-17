import createClient, { type Middleware } from 'openapi-fetch'
import type { components, paths } from './schema.gen'
import { API_URL } from './config'
import { detailText } from './errors'

export type Schemas = components['schemas']

const TOKEN_KEY = 'gistar-api-token'

/**
 * True while someone is logged in in this tab.
 * We need it because the token can disappear (for example, it was deleted from the browser)
 * while the person still sees a private page. Then a 401 must still end the session.
 */
let sessionOpen = false

/** Call this when the API confirms the session is valid (after login, or after reloading the page). */
export function markSessionOpen() {
  sessionOpen = true
}

/** sessionStorage: one session per tab, so two tabs can act as two different users. */
export const tokenStore = {
  get: () => sessionStorage.getItem(TOKEN_KEY),
  set: (t: string) => {
    sessionStorage.setItem(TOKEN_KEY, t)
    sessionOpen = true
  },
  clear: () => {
    sessionStorage.removeItem(TOKEN_KEY)
    sessionOpen = false
  },
}

let onUnauthorized: (() => void) | null = null
export function setUnauthorizedHandler(fn: (() => void) | null) {
  onUnauthorized = fn
}

/**
 * Decides if a 401 answer means "your session has ended".
 * - On the login call, 401 only means a wrong password: never end the session.
 * - If the request sent a token, or a session was open in this tab, the session has ended.
 * - A public request from someone who never logged in (for example the inscription form): nothing to end.
 */
export function endsSession(status: number, url: string, sentToken: boolean): boolean {
  if (status !== 401 || url.endsWith('/auth/login')) return false
  return sentToken || sessionOpen
}

export const authMiddleware: Middleware = {
  onRequest({ request }) {
    const t = tokenStore.get()
    if (t) request.headers.set('Authorization', `Bearer ${t}`)
    return request
  },
  onResponse({ response, request }) {
    if (endsSession(response.status, request.url, request.headers.has('Authorization'))) {
      sessionOpen = false
      onUnauthorized?.()
    }
    return response
  },
}

export const api = createClient<paths>({ baseUrl: API_URL ?? '' })
api.use(authMiddleware)

/** Human-readable message from FastAPI errors (detail string or validation list). */
export function errorMessage(err: unknown, fallback = 'No se ha podido completar la operación'): string {
  return detailText(err) ?? fallback
}
