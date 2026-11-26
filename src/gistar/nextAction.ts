// A next action is optional on a contact, but never half filled (PO decision, KAN-272).
export type NextActionDraft = {
  description: string
  owner_user_id: string
  due_on: string
}

export const emptyNextAction: NextActionDraft = {
  description: '',
  owner_user_id: '',
  due_on: '',
}

export type NextActionState = 'empty' | 'incomplete' | 'complete'

export function nextActionState(draft: NextActionDraft): NextActionState {
  const filled = [
    draft.description.trim(),
    draft.owner_user_id,
    draft.due_on,
  ].filter(Boolean).length
  if (filled === 0) return 'empty'
  return filled === 3 ? 'complete' : 'incomplete'
}

/** Why a draft cannot be saved yet, or null. An owner that is not on screen must never be sent. */
export function nextActionProblem(
  draft: NextActionDraft,
  offeredOwnerIds: string[],
  today: string,
): string | null {
  const state = nextActionState(draft)
  if (state === 'empty') return null
  if (state === 'incomplete')
    return 'Completa la acción, la persona responsable y el plazo, o deja los tres vacíos.'
  if (!offeredOwnerIds.includes(draft.owner_user_id))
    return 'Elige de nuevo la persona responsable: no está en la lista disponible.'
  if (draft.due_on < today) return 'El plazo no puede ser anterior a hoy.'
  return null
}

/** Today in the team's time zone, as YYYY-MM-DD (the same rule the API applies to deadlines). */
export function teamToday(now: Date = new Date()): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Madrid' }).format(
    now,
  )
}

/** Formats a calendar date without shifting it to another day. */
export function formatDueDate(isoDate: string): string {
  return new Intl.DateTimeFormat('es-ES', {
    dateStyle: 'medium',
    timeZone: 'UTC',
  }).format(new Date(`${isoDate}T00:00:00Z`))
}
