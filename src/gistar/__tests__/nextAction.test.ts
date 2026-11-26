import { describe, expect, it } from 'vitest'
import {
  emptyNextAction,
  formatDueDate,
  nextActionProblem,
  nextActionState,
  teamToday,
} from '../nextAction'

describe('next action draft', () => {
  it('is optional when nothing is filled, even with blank text', () => {
    expect(nextActionState(emptyNextAction)).toBe('empty')
    expect(nextActionState({ ...emptyNextAction, description: '   ' })).toBe(
      'empty',
    )
  })

  it('must be complete once any field is filled', () => {
    expect(nextActionState({ ...emptyNextAction, due_on: '2026-12-01' })).toBe(
      'incomplete',
    )
    expect(
      nextActionState({
        description: 'Call',
        owner_user_id: 'u',
        due_on: '2026-12-01',
      }),
    ).toBe('complete')
  })

  it('blocks a hidden owner, a past deadline and a half-filled draft', () => {
    const draft = {
      description: 'Call',
      owner_user_id: 'u',
      due_on: '2026-12-01',
    }
    expect(nextActionProblem(emptyNextAction, [], '2026-11-26')).toBeNull()
    expect(nextActionProblem(draft, ['u'], '2026-12-01')).toBeNull()
    expect(nextActionProblem(draft, [], '2026-11-26')).toContain('responsable')
    expect(nextActionProblem(draft, ['u'], '2026-12-02')).toContain(
      'anterior a hoy',
    )
    expect(
      nextActionProblem({ ...draft, due_on: '' }, ['u'], '2026-11-26'),
    ).toContain('Completa')
  })

  it('reads dates in the team time zone and never shifts a deadline', () => {
    expect(teamToday(new Date('2026-11-25T23:30:00Z'))).toBe('2026-11-26')
    expect(formatDueDate('2026-12-01')).toContain('1')
    expect(formatDueDate('2026-12-01')).toContain('dic')
  })
})
