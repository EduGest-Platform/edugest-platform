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

/**
 * Goes up by one every time a session starts or ends.
 * Each request remembers the number it was sent with, so a late 401 from an old session
 * can never close a newer one.
 */
let sessionGeneration = 0

/** Call this when the API confirms the session is valid (after login, or after reloading the page). */
export function markSessionOpen() {
  sessionOpen = true
}

function endSession() {
  sessionOpen = false
  sessionGeneration += 1
}

/** sessionStorage: one session per tab, so two tabs can act as two different users. */
export const tokenStore = {
  get: () => sessionStorage.getItem(TOKEN_KEY),
  set: (t: string) => {
    sessionStorage.setItem(TOKEN_KEY, t)
    sessionOpen = true
    sessionGeneration += 1
  },
  clear: () => {
    sessionStorage.removeItem(TOKEN_KEY)
    endSession()
  },
}

let onUnauthorized: (() => void) | null = null
export function setUnauthorizedHandler(fn: (() => void) | null) {
  onUnauthorized = fn
}

/** What we know about a request at the moment it was sent. */
interface SentWith {
  /** A session was open, or a token was sent. */
  hadSession: boolean
  /** The session number when the request was sent. */
  generation: number
}

const sentWith = new WeakMap<Request, SentWith>()

/**
 * Decides if a 401 answer means "your session has ended".
 * - On the login call, 401 only means a wrong password: never end the session.
 * - A public request from someone who was not logged in: nothing to end.
 * - A request sent during an older session: that session is already over, so ignore it.
 */
export function endsSession(status: number, url: string, request: SentWith | undefined): boolean {
  if (status !== 401 || url.endsWith('/auth/login') || !request) return false
  return request.hadSession && request.generation === sessionGeneration
}

export const authMiddleware: Middleware = {
  onRequest({ request }) {
    const t = tokenStore.get()
    if (t) request.headers.set('Authorization', `Bearer ${t}`)
    sentWith.set(request, { hadSession: sessionOpen || !!t, generation: sessionGeneration })
    return request
  },
  onResponse({ response, request }) {
    if (endsSession(response.status, request.url, sentWith.get(request))) {
      endSession()
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
