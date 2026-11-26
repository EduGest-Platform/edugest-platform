import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import type { Schemas } from '../../shared/api/client'
import { canOpen, menuFor } from '../config'
import { AppliedSelectionDecision } from '../views/api/ApplicantSelectionOutcome'

const pending: Schemas['OwnSelectionOutcome'] = {
  application_id: 'synthetic-application',
  stage: 'pendiente_decision_humana',
  outcome: null,
  decided_at: null,
  enrollment: null,
}

describe('applicant selection outcome', () => {
  it('does not infer a decision from the stage alone', () => {
    const html = renderToStaticMarkup(<AppliedSelectionDecision outcome={{ ...pending, stage: 'admitida' }} />)
    expect(html).toContain('Todavía no hay una decisión')
    expect(html).not.toContain('Admitida')
  })

  it('shows the applied waitlist result and date without enrollment', () => {
    const html = renderToStaticMarkup(<AppliedSelectionDecision outcome={{
      ...pending, stage: 'lista_espera', outcome: 'lista_espera', decided_at: '2026-11-26T08:00:00Z',
    }} />)
    expect(html).toContain('Estás en lista de espera')
    expect(html).toContain('2026-11-26T08:00:00Z')
    expect(html).not.toContain('Estado de matrícula')
  })

  it('shows the verified enrollment without exposing its identifier', () => {
    const html = renderToStaticMarkup(<AppliedSelectionDecision outcome={{
      ...pending, stage: 'admitida', outcome: 'admitida',
      enrollment: { cohort_id: 'COH-SYN', enrollment_id: 'SYNTHETIC-ENROLLMENT-ID', status: 'activa' },
    }} />)
    expect(html).toContain('Estado de matrícula')
    expect(html).toContain('COH-SYN')
    expect(html).not.toContain('SYNTHETIC-ENROLLMENT-ID')
  })

  it('keeps the view available to coders in API mode after enrollment', () => {
    expect(menuFor('coder', true)).toContain('candidatura')
    expect(canOpen('coder', 'candidatura', true)).toBe(true)
    expect(canOpen('coder', 'candidatura')).toBe(false)
  })
})
