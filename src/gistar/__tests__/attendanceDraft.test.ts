import { describe, expect, it } from 'vitest'
import type { Schemas } from '../../shared/api/client'
import { attendanceDraft } from '../views/api/attendanceDraft'

const absent: Schemas['RecordOut'] = { id: 'record-a', session_id: 'session', enrollment_id: 'person-a', status: 'ausente', modality: null, justification: 'justificada', version: 2, updated_at: '2026-11-24T10:00:00Z' }

describe('attendance selection drafts', () => {
  it('loads a saved absence instead of silently replacing it with present', () => {
    const draft = attendanceDraft(absent)
    expect(draft.status).toBe('ausente')
    expect(draft.justification).toBe('justificada')
    expect(draft.reason).toBe('')
  })
  it('switches from an absence to the actual modality and late state of another enrollment', () => {
    const first = { ...attendanceDraft(absent), reason: 'Unsaved reason' }
    const online: Schemas['RecordOut'] = { ...absent, id: 'record-b', enrollment_id: 'person-b', status: 'retraso', modality: 'online', justification: null }
    const second = attendanceDraft(online)
    expect(second.status).toBe('retraso')
    expect(second.modality).toBe('online')
    expect(second.reason).toBe('')
    expect(first.status).toBe('ausente')
  })
  it('resets a new unrecorded selection without carrying the previous absence or reason', () => {
    const old = { ...attendanceDraft(absent), reason: 'Old correction' }
    const next = attendanceDraft()
    expect(next).toEqual({ status: 'presente', modality: 'presencial', justification: 'no_justificada', reason: '' })
    expect(old.status).toBe('ausente')
  })
  it('reloads the current server revision rather than retaining the old justification', () => {
    expect(attendanceDraft(absent).justification).toBe('justificada')
    expect(attendanceDraft({ ...absent, version: 3, justification: 'no_justificada' }).justification).toBe('no_justificada')
  })
})
