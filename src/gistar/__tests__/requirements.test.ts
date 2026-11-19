import { describe, expect, it } from 'vitest'
import { REQUIREMENT_EXAMPLES } from '../demo/requirementExamples'
import { REVIEW_STATE_TEXT, summarizeReview, type RequirementCheck } from '../requirements'

const check = (kind: RequirementCheck['kind'], status: RequirementCheck['status'], id = `${kind}-${status}`): RequirementCheck => ({
  id,
  label: id,
  kind,
  status,
})

describe('summarizeReview', () => {
  it('no checks, or nothing checked yet -> not reviewed', () => {
    expect(summarizeReview([]).state).toBe('sin_revisar')
    expect(summarizeReview([check('obligatorio', 'pendiente')]).state).toBe('sin_revisar')
  })

  it('some items still pending -> in review', () => {
    const s = summarizeReview([check('obligatorio', 'cumple', 'a'), check('obligatorio', 'pendiente', 'b')])
    expect(s).toEqual({ state: 'en_revision', total: 2, checked: 1, openIssues: 0 })
  })

  it('a required item not met -> needs a human decision, never "rejected"', () => {
    const s = summarizeReview([check('obligatorio', 'cumple', 'a'), check('obligatorio', 'no_cumple', 'b')])
    expect(s.state).toBe('necesita_decision_humana')
    expect(s.openIssues).toBe(1)
    expect(REVIEW_STATE_TEXT[s.state].hint).toMatch(/no excluye automáticamente/)
  })

  it('an open issue wins over pending items, so a person looks at it right away', () => {
    const s = summarizeReview([check('obligatorio', 'excepcion_en_revision', 'a'), check('obligatorio', 'pendiente', 'b')])
    expect(s.state).toBe('necesita_decision_humana')
  })

  it('an approved exception counts as resolved', () => {
    const s = summarizeReview([check('obligatorio', 'cumple', 'a'), check('obligatorio', 'excepcion_aprobada', 'b')])
    expect(s.state).toBe('cumple')
    expect(s.openIssues).toBe(0)
  })

  it('a recommended item that is not met does not block', () => {
    const s = summarizeReview([check('obligatorio', 'cumple', 'a'), check('recomendado', 'no_cumple', 'b')])
    expect(s.state).toBe('cumple')
  })

  it('the local examples cover every review state', () => {
    const states = new Set(Object.values(REQUIREMENT_EXAMPLES).map((c) => summarizeReview(c).state))
    expect(states).toEqual(new Set(['en_revision', 'necesita_decision_humana', 'cumple']))
  })

  it('no state text talks about rejecting or excluding a person', () => {
    for (const { title } of Object.values(REVIEW_STATE_TEXT)) expect(title).not.toMatch(/rechaz|exclu/i)
  })
})
