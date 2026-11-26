import type { Schemas } from '../shared/api/client'

export type ManualOrigin = Schemas['ManualApplicationCreate']['origin_channel']
export type OriginChannel = Schemas['ApplicationSummary']['origin_channel']

export const ORIGIN_LABELS: Record<OriginChannel, string> = {
  formulario: 'Formulario',
  correo: 'Correo',
  telefono: 'Teléfono',
  derivacion: 'Derivación',
  registro_manual: 'Registro manual',
  redes: 'Redes',
}

/** «formulario» is reserved for the public form, so staff cannot pick it. */
export const MANUAL_ORIGINS: ManualOrigin[] = ['correo', 'telefono', 'derivacion', 'registro_manual', 'redes']

/** API roles that may register applications. The server decides; this only avoids showing a form that would be refused. */
const REGISTRAR_ROLES = ['seleccion', 'coordinacion', 'admin']

export function mayRegisterApplications(roles: readonly { role: string }[]): boolean {
  return roles.some((assignment) => REGISTRAR_ROLES.includes(assignment.role))
}

export type ManualIntakeDraft = {
  origin_channel: ManualOrigin | ''
  nombre: string
  email: string
  motivacion: string
  disponibilidad: 'Mañana' | 'Tarde' | 'Flexible'
  confirmed: boolean
}

export const emptyManualIntake: ManualIntakeDraft = {
  origin_channel: '',
  nombre: '',
  email: '',
  motivacion: '',
  disponibilidad: 'Flexible',
  confirmed: false,
}

/** The request to send, or null until the call, the channel and the staff confirmation are there. */
export function manualApplication(draft: ManualIntakeDraft, callId: string): Schemas['ManualApplicationCreate'] | null {
  if (!callId || !draft.origin_channel || !draft.confirmed) return null
  return {
    call_id: callId,
    origin_channel: draft.origin_channel,
    nombre: draft.nombre,
    email: draft.email,
    motivacion: draft.motivacion,
    disponibilidad: draft.disponibilidad,
    confirma_datos_sinteticos: true,
  }
}
