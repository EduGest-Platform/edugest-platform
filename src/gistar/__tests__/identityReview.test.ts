import { describe, expect, it } from 'vitest'
import { DIFFERENT_PERSON, emptyIdentityDraft, identityBlockerText, identityDecision, isIdentityDraftDirty } from '../identityReview'

const OFFERED = ['record-a']

describe('identity review draft', () => {
  it('sends nothing until there is both a choice and a reason', () => {
    expect(identityDecision(emptyIdentityDraft, OFFERED)).toBeNull()
    expect(identityDecision({ choice: DIFFERENT_PERSON, reason: '   ' }, OFFERED)).toBeNull()
    expect(identityDecision({ choice: '', reason: 'Checked by phone' }, OFFERED)).toBeNull()
  })

  it('links only when the chosen record is still offered', () => {
    const draft = { choice: 'record-a', reason: '  Checked by phone ' }
    expect(identityDecision(draft, OFFERED)).toEqual({ decision: 'misma_persona', reason: 'Checked by phone', linked_person_id: 'record-a' })
    expect(identityDecision(draft, [])).toBeNull()
  })

  it('never sends a record id when they are different people', () => {
    expect(identityDecision({ choice: DIFFERENT_PERSON, reason: 'Checked by phone' }, OFFERED)).toEqual({
      decision: DIFFERENT_PERSON,
      reason: 'Checked by phone',
      linked_person_id: null,
    })
  })

  it('is dirty as soon as the person has chosen or written something', () => {
    expect(isIdentityDraftDirty(emptyIdentityDraft)).toBe(false)
    expect(isIdentityDraftDirty({ choice: DIFFERENT_PERSON, reason: '' })).toBe(true)
    expect(isIdentityDraftDirty({ choice: '', reason: 'x' })).toBe(true)
  })

  it('explains why a review cannot be resolved yet', () => {
    expect(identityBlockerText(null)).toBeNull()
    expect(identityBlockerText('fuera_de_ambito')).toContain('administración')
    expect(identityBlockerText('revision_anterior_pendiente')).toContain('registro anterior')
  })
})
