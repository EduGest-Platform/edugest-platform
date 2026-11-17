import { describe, expect, it } from 'vitest'
import { describeApiError, detailText, problemKindFor, problemText } from '../errors'

describe('problemKindFor', () => {
  it.each([
    [401, 'unauthorized'],
    [403, 'forbidden'],
    [404, 'not_found'],
    [409, 'conflict'],
    [400, 'invalid'],
    [422, 'invalid'],
    [429, 'rate_limited'],
    [500, 'server'],
    [503, 'server'],
    [0, 'network'],
    [undefined, 'network'],
    [418, 'unknown'],
  ] as const)('status %s → %s', (status, kind) => {
    expect(problemKindFor(status)).toBe(kind)
  })
})

describe('describeApiError', () => {
  it('uses our own text for 403 and never leaks the server detail', () => {
    const p = describeApiError(403, { detail: 'role seleccion lacks scope call:IA-2027A' })
    expect(p.kind).toBe('forbidden')
    expect(problemText(p)).not.toContain('scope')
    expect(p.title).toMatch(/permiso/)
  })

  it('tells the person to sign in again on 401', () => {
    const p = describeApiError(401, { detail: 'Invalid token' })
    expect(p.hint).toMatch(/iniciar sesión/)
    expect(problemText(p)).not.toContain('Invalid token')
  })

  it('keeps the field names from a 422 so the person knows what to fix', () => {
    const p = describeApiError(422, { detail: [{ loc: ['body', 'email'], msg: 'value is not a valid email' }] })
    expect(p.kind).toBe('invalid')
    expect(p.hint).toBe('email: value is not a valid email')
  })

  it('falls back to a friendly hint when the server sends no detail', () => {
    expect(describeApiError(500).hint).toMatch(/minutos/)
    expect(describeApiError(undefined).kind).toBe('network')
  })
})

describe('detailText', () => {
  it('returns null for empty or missing detail', () => {
    expect(detailText(undefined)).toBeNull()
    expect(detailText({ detail: '' })).toBeNull()
    expect(detailText({ detail: [] })).toBeNull()
  })
})
