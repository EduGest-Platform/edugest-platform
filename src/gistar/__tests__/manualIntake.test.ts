import { describe, expect, it } from 'vitest'
import { MANUAL_ORIGINS, ORIGIN_LABELS, emptyManualIntake, manualApplication, mayRegisterApplications } from '../manualIntake'

const READY = { ...emptyManualIntake, origin_channel: 'telefono' as const, nombre: 'Persona Sintética', confirmed: true }

describe('manual intake', () => {
  it('never offers the public form as a manual channel', () => {
    expect(MANUAL_ORIGINS).not.toContain('formulario')
    expect(Object.keys(ORIGIN_LABELS)).toHaveLength(MANUAL_ORIGINS.length + 1)
  })

  it('sends nothing without a call, a channel and the confirmation', () => {
    expect(manualApplication(READY, '')).toBeNull()
    expect(manualApplication({ ...READY, origin_channel: '' }, 'CALL')).toBeNull()
    expect(manualApplication({ ...READY, confirmed: false }, 'CALL')).toBeNull()
  })

  it('sends the staff confirmation, not the applicant acknowledgement', () => {
    const draft = { ...READY, email: 'synthetic@example.test', motivacion: 'Synthetic motivation', disponibilidad: 'Tarde' as const }
    expect(manualApplication(draft, 'CALL')).toStrictEqual({
      call_id: 'CALL',
      origin_channel: 'telefono',
      nombre: 'Persona Sintética',
      email: 'synthetic@example.test',
      motivacion: 'Synthetic motivation',
      disponibilidad: 'Tarde',
      confirma_datos_sinteticos: true,
    })
  })

  it('shows the form only to the roles the server accepts', () => {
    for (const role of ['seleccion', 'coordinacion', 'admin']) expect(mayRegisterApplications([{ role }])).toBe(true)
    for (const role of ['captacion', 'docente']) expect(mayRegisterApplications([{ role }])).toBe(false)
    expect(mayRegisterApplications([])).toBe(false)
  })
})
