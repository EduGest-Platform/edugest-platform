/**
 * Requirement review of one application (KAN-145).
 *
 * Each call (convocatoria) has its own requirements, for example a minimum age or living in the project area.
 * The team checks each requirement by hand. This file turns those checks into one overall status for the dossier.
 *
 * Important rule (AS-IS and EU AI Act): the platform never rejects anyone automatically.
 * If a required item is not met, the result is "needs a human decision", never "rejected".
 *
 * The data shape is a proposal to agree with the backend (KAN-128). Keep it small so it is easy to change.
 */

/** Required items block the process until a person decides. Recommended items only add information. */
export type RequirementKind = 'obligatorio' | 'recomendado'

export type RequirementStatus =
  | 'pendiente' // nobody has checked it yet
  | 'cumple' // checked: it is met
  | 'no_cumple' // checked: it is not met
  | 'excepcion_en_revision' // not met, but the team is studying an exception
  | 'excepcion_aprobada' // not met, but the team approved an exception

export interface RequirementCheck {
  id: string
  /** What is checked, in plain words. Never personal or health details. */
  label: string
  kind: RequirementKind
  status: RequirementStatus
  /** Short note from the team. Never health data or personal situation details. */
  note?: string | null
  reviewedBy?: string | null
  reviewedAt?: string | null
}

/** The overall status we show on the dossier. */
export type ReviewState = 'sin_revisar' | 'en_revision' | 'necesita_decision_humana' | 'cumple'

export interface ReviewSummary {
  state: ReviewState
  total: number
  checked: number
  /** Required items that are not met and have no approved exception. */
  openIssues: number
}

/** Shown to people. Each state says what it means and what happens next. */
export const REVIEW_STATE_TEXT: Record<ReviewState, { title: string; hint: string }> = {
  sin_revisar: { title: 'Requisitos sin revisar', hint: 'Nadie ha revisado todavía los requisitos de esta candidatura.' },
  en_revision: { title: 'Requisitos en revisión', hint: 'El equipo está revisando los requisitos. Faltan algunos por comprobar.' },
  necesita_decision_humana: {
    title: 'Necesita una decisión del equipo',
    hint: 'Hay requisitos obligatorios sin cumplir o con una excepción en estudio. Una persona debe decidir; la plataforma no excluye automáticamente.',
  },
  cumple: { title: 'Requisitos revisados', hint: 'Todos los requisitos obligatorios se cumplen o tienen una excepción aprobada.' },
}

export const REQUIREMENT_STATUS_TEXT: Record<RequirementStatus, string> = {
  pendiente: 'Pendiente',
  cumple: 'Cumple',
  no_cumple: 'No cumple',
  excepcion_en_revision: 'Excepción en estudio',
  excepcion_aprobada: 'Excepción aprobada',
}

const isChecked = (c: RequirementCheck) => c.status !== 'pendiente'

/** A required item that a person still has to decide about. */
const isOpenIssue = (c: RequirementCheck) => c.kind === 'obligatorio' && (c.status === 'no_cumple' || c.status === 'excepcion_en_revision')

/**
 * Works out the overall status from the individual checks.
 * Order matters: an open issue on a required item wins, because a person must look at it
 * even if other items are still pending.
 */
export function summarizeReview(checks: readonly RequirementCheck[]): ReviewSummary {
  const total = checks.length
  const checked = checks.filter(isChecked).length
  const openIssues = checks.filter(isOpenIssue).length

  let state: ReviewState
  if (total === 0 || checked === 0) state = 'sin_revisar'
  else if (openIssues > 0) state = 'necesita_decision_humana'
  else if (checked < total) state = 'en_revision'
  else state = 'cumple'

  return { state, total, checked, openIssues }
}
