import createClient, { type Middleware } from 'openapi-fetch'
import type { components, paths } from './schema.gen'
import { API_URL } from './config'

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
    if (response.status === 401 && !request.url.endsWith('/auth/login')) onUnauthorized?.()
    return response
  },
}

export const api = createClient<paths>({ baseUrl: API_URL ?? '' })
api.use(auth)

/** Human-readable message from FastAPI errors (detail string or validation list). */
export function errorMessage(err: unknown, fallback = 'No se ha podido completar la operación'): string {
  const detail = (err as { detail?: unknown })?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((d: { loc?: (string | number)[]; msg?: string }) => `${d.loc?.slice(-1)[0] ?? 'campo'}: ${d.msg ?? 'no válido'}`)
      .join(' · ')
  }
  return fallback
}
