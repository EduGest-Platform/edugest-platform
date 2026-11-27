import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'
import { canOpen, menuFor } from '../config'
import { emptyManualIntake, sendManualApplication, type IntakeOutcome } from '../manualIntake'
import { GistarProvider } from '../store'
import { ApiCoordinationDashboard } from '../views/api/ApiCoordinationDashboard'
import { ManualIntakeFields } from '../views/api/ServerManualIntake'

const dashboard = vi.hoisted(() => ({ onRegistered: undefined as undefined | (() => void) }))

vi.mock('../views/api/ServerManualIntake', async (original) => ({
  ...(await original<typeof import('../views/api/ServerManualIntake')>()),
  ServerManualIntake: (props: { onRegistered?: () => void }) => {
    dashboard.onRegistered = props.onRegistered
    return null
  },
}))

const DRAFT = { ...emptyManualIntake, origin_channel: 'telefono' as const, nombre: 'Persona Sintética', confirmed: true }

function render(over: { busy?: boolean; outcome?: IntakeOutcome | null } = {}) {
  return renderToStaticMarkup(
    <ManualIntakeFields
      calls={[{ id: 'CALL', nombre: 'Convocatoria sintética' }]} callsError={null} onReloadCalls={() => {}}
      callId="CALL" onCallChange={() => {}} draft={DRAFT} onChange={() => {}}
      busy={over.busy ?? false} canSubmit outcome={over.outcome ?? null} onSubmit={() => {}}
    />,
  )
}

describe('manual intake form', () => {
  it('locks every field while the request is pending, so nothing typed can be wiped by the answer', () => {
    const html = render({ busy: true })
    // One fieldset wraps all the controls: disabling it disables each of them.
    expect(html).toMatch(/<fieldset disabled=""[^>]*>.*id="manual-call".*id="manual-motivation".*type="checkbox".*<\/fieldset>/s)
    expect(html).toContain('aria-busy="true"')
    expect(html).toContain('Registrando…')
    expect(html).toContain('value="Persona Sintética"')
  })

  it('leaves the fields editable when nothing is being sent', () => {
    const html = render()
    expect(html).not.toContain('<fieldset disabled')
    expect(html).not.toContain('Registrando…')
  })

  it('shows the code of a registered application', () => {
    const html = render({ outcome: { kind: 'registered', code: 'IA27A-9999' } })
    expect(html).toContain('IA27A-9999')
    expect(html).not.toContain('role="alert"')
  })

  it('announces a failure and keeps what was typed', () => {
    const html = render({ outcome: { kind: 'rejected', message: 'Ya existe una candidatura sintética' } })
    expect(html).toContain('role="alert"')
    expect(html).toContain('Ya existe una candidatura sintética')
    expect(html).toContain('value="Persona Sintética"')
  })
})

describe('sending a manual application', () => {
  const answer = (status: number, data?: { codigo: string }, error?: unknown) => ({ data, error, response: { status } })

  it('does not report anything while the request is still pending', async () => {
    let finish: (value: ReturnType<typeof answer>) => void = () => {}
    let reported: IntakeOutcome | null = null
    const sending = sendManualApplication(() => new Promise((resolve) => { finish = resolve })).then((result) => { reported = result })
    await Promise.resolve()
    expect(reported).toBeNull()
    finish(answer(201, { codigo: 'IA27A-0001' }))
    await sending
    expect(reported).toEqual({ kind: 'registered', code: 'IA27A-0001' })
  })

  it('reports a server refusal with its reason', async () => {
    const result = await sendManualApplication(async () => answer(409, undefined, { detail: 'Ya existe una candidatura sintética' }))
    expect(result).toMatchObject({ kind: 'rejected', message: expect.stringContaining('Ya existe una candidatura sintética') })
  })

  it.each([500, 502, 504])('does not call a %i a refusal, because the row may have been saved', async (status) => {
    const result = await sendManualApplication(async () => answer(status))
    expect(result.kind).toBe('unconfirmed')
  })

  it('says it cannot confirm when the connection drops', async () => {
    const result = await sendManualApplication(async () => { throw new TypeError('network down') })
    expect(result).toMatchObject({ kind: 'unconfirmed' })
  })
})

describe('where each registrar finds the form', () => {
  it('gives administration the applications screen with the server only', () => {
    expect(menuFor('admin', true)).toContain('candidaturas')
    expect(canOpen('admin', 'candidaturas', true)).toBe(true)
    expect(menuFor('admin', false)).not.toContain('candidaturas')
    expect(canOpen('admin', 'candidaturas')).toBe(false)
  })

  it('does not change the menu of the other roles in server mode', () => {
    for (const role of ['seleccion', 'coordinacion', 'docente', 'fundacion', 'aspirante'] as const) expect(menuFor(role, true)).toEqual(menuFor(role, false))
  })
})

describe('coordination dashboard', () => {
  // The refresh itself is checked in a browser by e2e/coordination-dashboard.mjs, which CI runs.
  it('is told about each registration', () => {
    renderToStaticMarkup(<GistarProvider><ApiCoordinationDashboard /></GistarProvider>)
    expect(dashboard.onRegistered).toBeTypeOf('function')
  })
})
