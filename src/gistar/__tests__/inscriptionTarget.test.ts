import { describe, expect, it } from 'vitest'
import { inscriptionTarget } from '../views/api/inscriptionTarget'

describe('catalogue to application handoff', () => {
  const calls = [{ id: 'SYNTHETIC-A' }, { id: 'SYNTHETIC-B' }]
  it('pins the catalogue selection instead of the first call or another selection', () => {
    expect(inscriptionTarget(calls, 'SYNTHETIC-A', 'SYNTHETIC-B')).toEqual({ id: 'SYNTHETIC-B', available: true })
  })
  it('never silently substitutes a withdrawn or closed target', () => {
    expect(inscriptionTarget(calls, '', 'WITHDRAWN')).toEqual({ id: 'WITHDRAWN', available: false })
    expect(inscriptionTarget([], '', 'SYNTHETIC-B')).toEqual({ id: 'SYNTHETIC-B', available: false })
  })
  it('preserves ordinary registration selection and the initial default', () => {
    expect(inscriptionTarget(calls, '')).toEqual({ id: 'SYNTHETIC-A', available: true })
    expect(inscriptionTarget(calls, 'SYNTHETIC-B')).toEqual({ id: 'SYNTHETIC-B', available: true })
    expect(inscriptionTarget(calls, 'UNKNOWN').available).toBe(false)
  })
})
