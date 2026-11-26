import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { api, type Schemas } from '../../../shared/api/client'
import { describeApiError, problemText } from '../../../shared/api/errors'
import { useApiSession } from '../../../shared/api/session'
import { MANUAL_ORIGINS, ORIGIN_LABELS, emptyManualIntake, manualApplication, mayRegisterApplications, type ManualIntakeDraft, type ManualOrigin } from '../../manualIntake'
import { Button, Card, Field, Notice, inputCls } from '../../ui'

type IntakeCall = Schemas['ManualIntakeCallOut']

/** KAN-275: staff register applications that arrive by phone, email and so on. */
export function ServerManualIntake({ onRegistered }: { onRegistered?: () => void }) {
  const { me } = useApiSession()
  const [open, setOpen] = useState(false)
  const [opened, setOpened] = useState(false)
  if (!mayRegisterApplications(me?.roles ?? [])) return null

  return (
    <Card title="Alta manual de candidaturas" action={<Button size="sm" variant="ghost" aria-expanded={open} onClick={() => { setOpen(!open); setOpened(true) }}>{open ? 'Ocultar' : 'Registrar candidatura'}</Button>}>
      <p className="text-sm text-muted">Para solicitudes que llegan fuera del formulario. Quedan tu cuenta, la fecha y el canal de origen.</p>
      {/* Not rendered until first opened; afterwards hidden rather than unmounted, so collapsing keeps the draft. */}
      {opened && (
        <div hidden={!open}>
          <ManualIntakeForm active={open} onRegistered={onRegistered} />
        </div>
      )}
    </Card>
  )
}

function useIntakeCalls(active: boolean) {
  const [calls, setCalls] = useState<IntakeCall[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setError(null)
    try {
      const { data, error: apiError, response } = await api.GET('/api/v1/manual-intake/calls')
      setCalls(data ?? null)
      if (!data) setError(problemText(describeApiError(response.status, apiError)))
    } catch {
      setError('No se pudieron cargar las convocatorias. Revisa tu conexión.')
    }
  }, [])

  useEffect(() => {
    if (active) void load()
  }, [active, load])

  return { calls, error, load }
}

function ManualIntakeForm({ active, onRegistered }: { active: boolean; onRegistered?: () => void }) {
  const { calls, error: callsError, load } = useIntakeCalls(active)
  const [chosenCall, setChosenCall] = useState('')
  const [draft, setDraft] = useState<ManualIntakeDraft>(emptyManualIntake)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [code, setCode] = useState<string | null>(null)
  // A call that stopped being offered never stays selected.
  const callId = calls?.some((call) => call.id === chosenCall) ? chosenCall : ''
  const body = manualApplication(draft, callId)
  const change = (values: Partial<ManualIntakeDraft>) => setDraft((previous) => ({ ...previous, ...values }))

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (busy || !body) return
    setBusy(true)
    setError(null)
    setCode(null)
    try {
      const { data, error: apiError, response } = await api.POST('/api/v1/manual-intake/applications', { body })
      if (!data) {
        setError(problemText(describeApiError(response.status, apiError)))
        // The call may have closed, or the permission may have been removed.
        void load()
        return
      }
      setCode(data.codigo)
      setDraft(emptyManualIntake)
      onRegistered?.()
    } catch {
      setError('No se pudo confirmar el registro. Puedes volver a intentarlo: si ya se guardó, aparecerá el aviso de que ya existe.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="mt-4 grid max-w-2xl gap-4">
      {callsError && (
        <div className="grid justify-items-start gap-2">
          <Notice tone="warning" live="assertive">{callsError}</Notice>
          <Button type="button" size="sm" variant="ghost" onClick={() => void load()}>Volver a cargar convocatorias</Button>
        </div>
      )}
      {calls && !calls.length && <Notice live="polite">No tienes convocatorias abiertas en las que registrar candidaturas.</Notice>}
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Convocatoria" htmlFor="manual-call">
          <select id="manual-call" className={inputCls} required value={callId} onChange={(e) => setChosenCall(e.target.value)}>
            <option value="">{calls || callsError ? 'Elige una convocatoria' : 'Cargando…'}</option>
            {calls?.map((call) => <option key={call.id} value={call.id}>{call.nombre}</option>)}
          </select>
        </Field>
        <Field label="Canal de origen" htmlFor="manual-origin">
          <select id="manual-origin" className={inputCls} required value={draft.origin_channel} onChange={(e) => change({ origin_channel: e.target.value as ManualOrigin | '' })}>
            <option value="">Elige un canal</option>
            {MANUAL_ORIGINS.map((origin) => <option key={origin} value={origin}>{ORIGIN_LABELS[origin]}</option>)}
          </select>
        </Field>
        <Field label="Nombre (ficticio)" htmlFor="manual-name">
          <input id="manual-name" className={inputCls} required minLength={2} maxLength={120} value={draft.nombre} onChange={(e) => change({ nombre: e.target.value })} />
        </Field>
        <Field label="Correo de demostración" htmlFor="manual-email" hint="Usa un dominio reservado, p. ej. @example.test">
          <input id="manual-email" type="email" className={inputCls} required value={draft.email} onChange={(e) => change({ email: e.target.value })} />
        </Field>
      </div>
      <Field label="Motivación" htmlFor="manual-motivation" hint="Sin datos de salud ni situación personal.">
        <textarea id="manual-motivation" className={`${inputCls} min-h-24`} required minLength={10} maxLength={2000} value={draft.motivacion} onChange={(e) => change({ motivacion: e.target.value })} />
      </Field>
      <Field label="Disponibilidad" htmlFor="manual-availability">
        <select id="manual-availability" className={inputCls} value={draft.disponibilidad} onChange={(e) => change({ disponibilidad: e.target.value as ManualIntakeDraft['disponibilidad'] })}>
          <option>Mañana</option>
          <option>Tarde</option>
          <option>Flexible</option>
        </select>
      </Field>
      <label className="flex items-start gap-2.5 text-sm">
        <input type="checkbox" className="mt-0.5 size-4 accent-teal" required checked={draft.confirmed} onChange={(e) => change({ confirmed: e.target.checked })} />
        Confirmo que son datos sintéticos. No es el consentimiento de la persona ni permite registrar datos reales.
      </label>
      {error && <Notice tone="warning" live="assertive">{error}</Notice>}
      {code && <Notice live="polite">Candidatura registrada con el código <b className="font-mono">{code}</b>.</Notice>}
      <div>
        <Button type="submit" disabled={busy || !body}>{busy ? 'Registrando…' : 'Registrar'}</Button>
      </div>
    </form>
  )
}
