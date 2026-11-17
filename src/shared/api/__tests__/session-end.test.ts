import { beforeEach, describe, expect, it, vi } from 'vitest'

// The tests run in Node, which has no sessionStorage. This small copy is enough for tokenStore.
const storage = new Map<string, string>()
vi.stubGlobal('sessionStorage', {
  getItem: (k: string) => storage.get(k) ?? null,
  setItem: (k: string, v: string) => void storage.set(k, v),
  removeItem: (k: string) => void storage.delete(k),
})

const { authMiddleware, setUnauthorizedHandler, tokenStore } = await import('../client')
const { describeApiError, problemText } = await import('../errors')

const API = 'http://api.test/api/v1'

/** Sends one fake request through the same middleware the app uses, and gets a fake answer back. */
async function call(path: string, status: number) {
  const request = (await authMiddleware.onRequest!({ request: new Request(`${API}${path}`) } as never)) as Request
  await authMiddleware.onResponse!({ request, response: new Response(null, { status }) } as never)
  return request
}

describe('when the session ends, the app goes back to the login screen with a notice', () => {
  let notice: string | null
  const onUnauthorized = vi.fn(() => {
    // The same steps the session provider does: forget the token and leave a message for the login screen.
    tokenStore.clear()
    notice = problemText(describeApiError(401))
  })

  beforeEach(() => {
    storage.clear()
    tokenStore.clear()
    notice = null
    onUnauthorized.mockClear()
    setUnauthorizedHandler(onUnauthorized)
  })

  it('active session -> token deleted -> 401 -> session ends and the notice is shown', async () => {
    tokenStore.set('token-123') // logged in
    const first = await call('/applications', 200)
    expect(first.headers.get('Authorization')).toBe('Bearer token-123')

    storage.delete('gistar-api-token') // the token disappears from the browser
    const second = await call('/applications', 401)
    expect(second.headers.has('Authorization')).toBe(false)

    expect(onUnauthorized).toHaveBeenCalledTimes(1)
    expect(notice).toMatch(/sesión ha caducado/)
  })

  it('an expired token (401 with token) also ends the session', async () => {
    tokenStore.set('old-token')
    await call('/applications', 401)
    expect(onUnauthorized).toHaveBeenCalledTimes(1)
  })

  it('ends the session only once, even if several requests fail together', async () => {
    tokenStore.set('token-123')
    await call('/applications', 401)
    await call('/audit-events', 401)
    expect(onUnauthorized).toHaveBeenCalledTimes(1)
  })

  it('a wrong password on login is not a session end', async () => {
    await call('/auth/login', 401)
    expect(onUnauthorized).not.toHaveBeenCalled()
    expect(notice).toBeNull()
  })

  it('a public request from someone who never logged in does not show the notice', async () => {
    await call('/applications', 401)
    expect(onUnauthorized).not.toHaveBeenCalled()
  })
})
