import createClient, { type Middleware } from 'openapi-fetch'
import type { components, paths } from './schema.gen'
import { API_URL } from './config'
import { detailText } from './errors'

export type Schemas = components['schemas']

const TOKEN_KEY = 'gistar-api-token'
/** sessionStorage: one session per tab, so two tabs can act as two different users. */
export const tokenStore = {
  get: () => sessionStorage.getItem(TOKEN_KEY),
  set: (t: string) => sessionStorage.setItem(TOKEN_KEY, t),
  clear: () => sessionStorage.removeItem(TOKEN_KEY),
}

let onUnauthorized: (() => void) | null = null
export function setUnauthorizedHandler(fn: (() => void) | null) {
  onUnauthorized = fn
}

const auth: Middleware = {
  onRequest({ request }) {
    const t = tokenStore.get()
    if (t) request.headers.set('Authorization', `Bearer ${t}`)
    return request
  },
  onResponse({ response, request }) {
    // Error 401 means the session has ended (it expired, or the person logged out in another place).
    // We skip the login call itself: there, 401 only means a wrong password.
    const sentToken = request.headers.has('Authorization')
    if (response.status === 401 && sentToken && !request.url.endsWith('/auth/login')) onUnauthorized?.()
    return response
  },
}

export const api = createClient<paths>({ baseUrl: API_URL ?? '' })
api.use(auth)

/** Human-readable message from FastAPI errors (detail string or validation list). */
export function errorMessage(err: unknown, fallback = 'No se ha podido completar la operación'): string {
  return detailText(err) ?? fallback
}
