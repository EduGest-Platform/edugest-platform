import { useEffect, useRef, useState, type FormEvent } from 'react'
import { api, type Schemas } from '../../../shared/api/client'
import { describeApiError, problemText } from '../../../shared/api/errors'
import { useApiSession } from '../../../shared/api/session'
import { Button, Field, Notice, inputCls } from '../../ui'

type Appointment = Schemas['AppointmentOut']
type Kind = Appointment['kind']
type Draft =
  | { mode: 'schedule'; kind: Kind; time: string; location: string; previous?: Appointment }
  | { mode: 'outcome'; appointment: Appointment; result: Schemas['AppointmentOutcome']['result']; conclusions: string; assessment: string }

const kinds = { group_day: 'Jornada de selección', individual_interview: 'Entrevista individual' }
const states = { scheduled: 'Programada', attended: 'Asistió', no_show: 'Ausencia registrada', rescheduled: 'Reprogramada' }
const formatDate = new Intl.DateTimeFormat('es-ES', { dateStyle: 'medium', timeStyle: 'short' })

export function SelectionAppointments({ applicationId, onDirty }: { applicationId: string; onDirty: (dirty: boolean) => void }) {
  const { me } = useApiSession()
  const allowed = !!me?.roles.some(role => role.role === 'admin' || role.role === 'seleccion')
  const [data, setData] = useState<Schemas['AppointmentList']>()
  const [draft, setDraft] = useState<Draft>()
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [busy, setBusy] = useState(false)
  const write = useRef<AbortController | null>(null)

  useEffect(() => () => write.current?.abort(), [])
  const dirty = Boolean(draft)
  useEffect(() => {
    onDirty(dirty)
    return () => onDirty(false)
  }, [dirty, onDirty])
  useEffect(() => {
    if (!allowed) return
    const controller = new AbortController()
    setData(undefined)
    void api.GET('/api/v1/applications/{application_id}/selection-appointments', {
      params: { path: { application_id: applicationId } },
      signal: controller.signal,
    }).then(result => {
      if (controller.signal.aborted) return
      if (result.data) setData(result.data)
      else setError(problemText(describeApiError(result.response.status, result.error)))
    }).catch(() => {
      if (!controller.signal.aborted) setError('No se pudieron cargar las citaciones.')
    })
    return () => controller.abort()
  }, [allowed, applicationId, attempt])

  if (!allowed) return null
  const items = data?.items ?? []
  const pendingKinds = new Set(items.filter(item => item.state === 'scheduled').map(item => item.kind))
  const replacedIds = new Set(items.map(item => item.previous_id))
  const availableKinds = (Object.keys(kinds) as Kind[]).filter(kind => !pendingKinds.has(kind))
  const timeZone = formatDate.resolvedOptions().timeZone
  const byId = new Map(items.map(item => [item.id, item]))

  const staleDraft = Boolean(draft && data && (draft.mode === 'outcome'
    ? byId.get(draft.appointment.id)?.state !== 'scheduled'
    : draft.previous
      ? byId.get(draft.previous.id)?.state !== draft.previous.state
        || (draft.previous.state === 'no_show' && (replacedIds.has(draft.previous.id) || pendingKinds.has(draft.kind)))
      : pendingKinds.has(draft.kind)))

  function schedule(kind: Kind, previous?: Appointment) {
    setError('')
    setNotice('')
    setDraft({ mode: 'schedule', kind, time: '', location: previous?.location ?? '', previous })
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!data?.can_edit || !draft || staleDraft || write.current) return
    const controller = new AbortController()
    const path = { application_id: applicationId }
    write.current = controller
    setBusy(true)
    setError('')
    setNotice('')
    try {
      let result
      if (draft.mode === 'schedule') {
        const time = new Date(draft.time)
        if (!Number.isFinite(time.getTime())) {
          setError('Introduce una fecha y hora válidas.')
          return
        }
        result = await api.POST('/api/v1/applications/{application_id}/selection-appointments', {
          params: { path },
          body: {
            kind: draft.kind,
            scheduled_at: time.toISOString(),
            location: draft.location.trim() || null,
            previous_id: draft.previous?.id,
          },
          signal: controller.signal,
        })
      } else {
        result = await api.POST('/api/v1/applications/{application_id}/selection-appointments/{appointment_id}/outcome', {
          params: { path: { ...path, appointment_id: draft.appointment.id } },
          body: {
            result: draft.result,
            conclusions: draft.result === 'attended' ? draft.conclusions.trim() || null : null,
            assessment: draft.result === 'attended' ? draft.assessment.trim() || null : null,
          },
          signal: controller.signal,
        })
      }
      if (controller.signal.aborted) return
      if (result.data) {
        setDraft(undefined)
        setNotice(draft.mode === 'schedule' ? 'Cita registrada en el expediente.' : 'Resultado guardado en el expediente.')
        setAttempt(previous => previous + 1)
      } else {
        setError(problemText(describeApiError(result.response.status, result.error)))
        if (result.response.status === 409) {
          setData(undefined)
          setAttempt(value => value + 1)
        }
      }
    } catch {
      if (!controller.signal.aborted) setError('No se pudo confirmar el cambio. Actualiza las citas antes de volver a intentarlo.')
    } finally {
      write.current = null
      if (!controller.signal.aborted) setBusy(false)
    }
  }

  return (
    <section className="grid gap-3 rounded-xl border border-line p-3" aria-label="Citaciones de selección">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-semibold">Citaciones de selección</h3>
        <Button size="sm" variant="ghost" disabled={busy} onClick={() => { setError(''); setAttempt(value => value + 1) }}>Actualizar citas</Button>
      </div>
      {error && <Notice tone="warning" live="assertive">{error}</Notice>}
      {notice && <Notice live="polite">{notice}</Notice>}
      {!data && !error && <p role="status">Cargando citaciones…</p>}
      {data && items.length === 0 && <p className="text-muted">Aún no hay citaciones.</p>}
      {items.length > 0 && <ul className="grid gap-2">
        {items.map(item => {
          const previous = item.previous_id ? byId.get(item.previous_id) : undefined
          const canReplace = item.state === 'scheduled' || (item.state === 'no_show' && !replacedIds.has(item.id) && !pendingKinds.has(item.kind))
          return <li key={item.id} className="grid gap-1 rounded-lg border border-line p-3">
            <p className="font-medium">{kinds[item.kind]} · {states[item.state]}</p>
            <time dateTime={item.scheduled_at}>{formatDate.format(new Date(item.scheduled_at))}</time>
            {item.location && <p className="break-words">{item.location}</p>}
            {previous && <p className="text-muted">Cita anterior: {formatDate.format(new Date(previous.scheduled_at))}</p>}
            {item.conclusions && <p className="whitespace-pre-wrap break-words"><b>Conclusiones</b> {item.conclusions}</p>}
            {item.assessment && <p className="whitespace-pre-wrap break-words"><b>Valoración</b> {item.assessment}</p>}
            {data?.can_edit && <div className="flex flex-wrap gap-2">
              {canReplace && <Button type="button" size="sm" variant="ghost" disabled={!!draft}
                onClick={() => schedule(item.kind, item)}>{item.state === 'no_show' ? 'Agendar segunda oportunidad' : 'Reprogramar cita'}</Button>}
              {item.state === 'scheduled' && <Button type="button" size="sm" variant="ghost" disabled={!!draft}
                onClick={() => {
                  setError('')
                  setNotice('')
                  setDraft({ mode: 'outcome', appointment: item, result: 'attended', conclusions: '', assessment: '' })
                }}>Registrar resultado</Button>}
            </div>}
          </li>
        })}
      </ul>}
      {data?.can_edit && !draft && availableKinds.length > 0 &&
        <Button className="justify-self-start" size="sm" onClick={() => schedule(availableKinds[0])}>Agendar cita</Button>}
      {draft && <form className="grid gap-3 rounded-lg border border-line p-3" onSubmit={submit}>
        {staleDraft && <Notice tone="warning" live="assertive">La cita ha cambiado desde que abriste el formulario. Revisa el historial y copia tus notas antes de cancelar el borrador.</Notice>}
        <fieldset className="grid min-w-0 gap-3" disabled={busy || !data?.can_edit}>
          {draft.mode === 'schedule' ? <>
            <legend className="mb-3 font-medium">{draft.previous ? 'Nueva fecha para la cita' : 'Nueva cita'}</legend>
            {draft.previous ? <p>{kinds[draft.kind]}</p> : <Field label="Tipo de cita" htmlFor="selection-appointment-kind">
              <select id="selection-appointment-kind" className={inputCls} value={draft.kind}
                onChange={event => setDraft({ ...draft, kind: event.target.value as Kind })}>
                {availableKinds.map(kind => <option key={kind} value={kind}>{kinds[kind]}</option>)}
              </select>
            </Field>}
            <Field label={`Fecha y hora (${timeZone})`} htmlFor="selection-appointment-time">
              <input id="selection-appointment-time" className={inputCls} type="datetime-local" required
                value={draft.time} onChange={event => setDraft({ ...draft, time: event.target.value })} />
            </Field>
            <Field label="Lugar o modalidad (opcional)" htmlFor="selection-appointment-location">
              <input id="selection-appointment-location" className={inputCls} maxLength={250}
                value={draft.location} onChange={event => setDraft({ ...draft, location: event.target.value })} />
            </Field>
          </> : <>
            <legend className="mb-3 font-medium">Resultado · {kinds[draft.appointment.kind]}</legend>
            <p className="text-muted">Disponible a partir de la hora de la cita.</p>
            <Field label="Asistencia" htmlFor="selection-appointment-outcome">
              <select id="selection-appointment-outcome" className={inputCls} value={draft.result}
                onChange={event => setDraft({ ...draft, result: event.target.value as 'attended' | 'no_show' })}>
                <option value="attended">Asistió</option>
                <option value="no_show">Ausencia</option>
              </select>
            </Field>
            {draft.result === 'attended' && <>
              <Field label="Conclusiones (opcional)" htmlFor="selection-appointment-conclusions">
                <textarea id="selection-appointment-conclusions" className={inputCls} maxLength={1000}
                  value={draft.conclusions} onChange={event => setDraft({ ...draft, conclusions: event.target.value })} />
              </Field>
              <Field label="Valoración (opcional)" htmlFor="selection-appointment-assessment">
                <textarea id="selection-appointment-assessment" className={inputCls} maxLength={500}
                  value={draft.assessment} onChange={event => setDraft({ ...draft, assessment: event.target.value })} />
              </Field>
            </>}
          </>}
        </fieldset>
        <div className="flex flex-wrap gap-2">
          <Button type="submit" size="sm" disabled={busy || !data?.can_edit || staleDraft}>{draft.mode === 'schedule' ? 'Guardar cita' : 'Guardar resultado'}</Button>
          <Button type="button" size="sm" variant="ghost" disabled={busy} onClick={() => { setDraft(undefined); setError('') }}>Cancelar</Button>
        </div>
      </form>}
    </section>
  )
}
