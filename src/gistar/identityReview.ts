import type { Schemas } from '../shared/api/client'

export const DIFFERENT_PERSON = 'persona_distinta'

/** `choice` is empty, DIFFERENT_PERSON or the id of the record the staff member says is the same person. */
export type IdentityDraft = { choice: string; reason: string }

export const emptyIdentityDraft: IdentityDraft = { choice: '', reason: '' }

export function isIdentityDraftDirty(draft: IdentityDraft): boolean {
  return draft.choice !== '' || draft.reason.trim() !== ''
}

/** The decision to send, or null while it is incomplete. A record that is no longer offered never counts as chosen. */
export function identityDecision(draft: IdentityDraft, offeredIds: string[]): Schemas['IdentityDecisionCreate'] | null {
  const reason = draft.reason.trim()
  if (!reason) return null
  if (draft.choice === DIFFERENT_PERSON) return { decision: DIFFERENT_PERSON, reason, linked_person_id: null }
  if (!offeredIds.includes(draft.choice)) return null
  return { decision: 'misma_persona', reason, linked_person_id: draft.choice }
}

export function identityBlockerText(blocker: Schemas['IdentityReviewOut']['blocker']): string | null {
  if (blocker === 'fuera_de_ambito') {
    return 'Hay una coincidencia en una convocatoria que no tienes asignada. Tiene que resolverlo alguien con acceso a todas las convocatorias implicadas, o administración.'
  }
  if (blocker === 'revision_anterior_pendiente') return 'Antes hay que resolver el aviso de un registro anterior con el mismo correo.'
  return null
}
