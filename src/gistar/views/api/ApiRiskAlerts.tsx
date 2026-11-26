import { useEffect, useRef, useState, type FormEvent } from 'react'
import { api, errorMessage, type Schemas } from '../../../shared/api/client'
import { Modal } from '../../components/Modal'
import { Button, Card, Field, Notice, PageTitle, inputCls } from '../../ui'
import { useAcademicCohorts } from './ApiCohorts'

type Alert = Schemas['RiskAlertOut']
type ReviewState = Alert['review_state']
type Intervention = Schemas['InterventionWrite']['kind']

const labels: Record<ReviewState, string> = { pending: 'Pendiente', in_review: 'En revisión', closed: 'Cerrada' }
const actions: Record<Intervention, string> = { contact: 'Contacto', support: 'Apoyo', closure: 'Cierre' }
const number = new Intl.NumberFormat('es-ES', { maximumFractionDigits: 2 })
const time = new Intl.DateTimeFormat('es-ES', { dateStyle: 'short', timeStyle: 'short', timeZone: 'Europe/Madrid' })
const pageSize = 25
const value = (amount: number | null) => amount === null ? 'Sin dato' : number.format(amount)

function ReviewAlert({ cohortId, id, onClose, onSaved }: {
  cohortId: string; id: string; onClose: () => void; onSaved: () => void
}) {
  const [details, setDetails] = useState<Schemas['AlertReviewOut']>()
  const [attempt, setAttempt] = useState(0)
  const [kind, setKind] = useState<Intervention>('contact')
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const pending = useRef<AbortController | null>(null)
  useEffect(() => () => pending.current?.abort(), [])

  useEffect(() => {
    const controller = new AbortController()
    void api.GET('/api/v1/cohorts/{cohort_id}/risk-alerts/{alert_id}', {
      params: { path: { cohort_id: cohortId, alert_id: id } }, signal: controller.signal,
    }).then(result => {
      if (controller.signal.aborted) return
      if (result.data) setDetails(result.data)
      else setError(errorMessage(result.error, 'No se pudo leer esta alerta.'))
    }).catch(() => {
      if (!controller.signal.aborted) setError('No se pudo conectar con el servidor.')
    })
    return () => controller.abort()
  }, [cohortId, id, attempt])

  function reload() {
    setDetails(undefined)
    setError('')
    setAttempt(value => value + 1)
  }

  async function record(event: FormEvent) {
    event.preventDefault()
    if (!details || details.alert.review_state === 'closed' || !note.trim() || pending.current) return
    const controller = new AbortController()
    pending.current = controller
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const result = await api.POST('/api/v1/cohorts/{cohort_id}/risk-alerts/{alert_id}/interventions', {
        params: { path: { cohort_id: cohortId, alert_id: id } }, signal: controller.signal,
        body: { kind, note: note.trim(), expected_state: details.alert.review_state },
      })
      if (controller.signal.aborted) return
      if (result.data) {
        setNotice(kind === 'closure' ? 'Alerta cerrada.' : 'Intervención registrada.')
        setNote('')
        reload()
        onSaved()
      } else setError(errorMessage(result.error, 'No se pudo registrar la intervención.'))
    } catch {
      if (!controller.signal.aborted) setError('No se pudo confirmar el registro. Actualiza la alerta antes de reintentar.')
    } finally {
      pending.current = null
      if (!controller.signal.aborted) setBusy(false)
    }
  }

  const alert = details?.alert
  return (
    <Modal open onClose={onClose} placement="end" title="Revisar alerta sintética"
      subtitle={alert?.learner_name} dirty={Boolean(note.trim() || busy)}>
      <div className="grid gap-4">
        <Notice>Datos sintéticos para revisión humana. El modelo carece de validación para decisiones sobre personas.</Notice>
        {error && <Notice tone="warning" live="assertive">{error}</Notice>}
        {notice && <Notice live="polite">{notice}</Notice>}
        <Button variant="ghost" className="justify-self-start" onClick={reload} disabled={busy}>Actualizar alerta</Button>
        {!details && !error && <p role="status">Cargando alerta…</p>}
        {alert && details && <>
          <div className="grid gap-2 text-sm">
            <p>{labels[alert.review_state]} · Modelo {alert.model_version} · Corte {alert.cutoff}</p>
            <p>Responsable: {alert.assigned_to ?? 'Sin asignar'}</p>
            <p>{alert.status === 'abstained' ? `El modelo se abstuvo: ${alert.abstention_reason ?? 'evidencia insuficiente'}.`
              : alert.experimental_support_signal ? 'Señal experimental de apoyo disponible.' : 'Sin señal experimental de apoyo en este corte.'}</p>
            <dl className="grid grid-cols-[1fr_auto] gap-2 rounded-xl border border-line p-3">
              <dt>Días de ausencia sin justificar</dt><dd>{value(alert.unjustified_absence_days)}</dd>
              <dt>Días de ausencia justificada</dt><dd>{value(alert.justified_absence_days)}</dd>
              <dt>Asistencia sin registrar</dt><dd>{alert.attendance_unknown_fraction === null ? 'Sin dato' : `${value(alert.attendance_unknown_fraction * 100)} %`}</dd>
              <dt>Nivel medio de competencias</dt><dd>{value(alert.mean_competency_level)}</dd>
            </dl>
          </div>
          <h3 className="font-semibold">Historial de apoyo</h3>
          {details.interventions.length ? <ol className="grid gap-2">
            {details.interventions.map(item => <li key={item.id} className="rounded-xl border border-line p-3 text-sm">
              <p className="font-medium">{actions[item.kind]} · {item.actor}</p>
              <p className="text-xs text-muted">{time.format(new Date(item.occurred_at))}</p>
              <p className="mt-1 whitespace-pre-wrap wrap-anywhere">{item.note}</p>
            </li>)}
          </ol> : <p>Todavía no hay intervenciones.</p>}
          {alert.review_state !== 'closed' ? (
            <form className="grid gap-3" onSubmit={record}>
              <Field label="Tipo de intervención" htmlFor="risk-kind">
                <select id="risk-kind" className={inputCls} value={kind} disabled={busy}
                  onChange={event => setKind(event.target.value as Intervention)}>
                  {Object.entries(actions).map(([id, label]) => <option key={id} value={id}>{label}</option>)}
                </select>
              </Field>
              <Field label="Nota de apoyo" htmlFor="risk-note" hint="Evita incluir información personal sensible.">
                <textarea id="risk-note" className={inputCls} readOnly={busy} required maxLength={500}
                  value={note} onChange={event => setNote(event.target.value)} />
              </Field>
              <Button type="submit" className="justify-self-start" disabled={busy || !note.trim()}>
                {kind === 'closure' ? 'Cerrar alerta' : 'Registrar intervención'}
              </Button>
            </form>
          ) : note && <Notice tone="warning">Otra sesión cerró la alerta. Puedes copiar tu nota pendiente.</Notice>}
        </>}
        {note && (!alert || alert.review_state === 'closed') && (
          <>
            <textarea aria-label="Nota pendiente" className={inputCls} readOnly value={note} />
            <Button variant="ghost" onClick={() => setNote('')}>Descartar nota</Button>
          </>
        )}
      </div>
    </Modal>
  )
}

function CohortAlerts({ cohortId }: { cohortId: string }) {
  const [filter, setFilter] = useState<ReviewState | ''>('')
  const [offset, setOffset] = useState(0)
  const [attempt, setAttempt] = useState(0)
  const [data, setData] = useState<Schemas['RiskAlertList']>()
  const [error, setError] = useState('')
  const [selected, setSelected] = useState('')
  useEffect(() => {
    setData(undefined)
    setError('')
    const controller = new AbortController()
    void api.GET('/api/v1/cohorts/{cohort_id}/risk-alerts', {
      params: { path: { cohort_id: cohortId }, query: { state: filter || undefined, limit: pageSize, offset } },
      signal: controller.signal,
    }).then(result => {
      if (controller.signal.aborted) return
      if (result.data) setData(result.data)
      else setError(errorMessage(result.error, 'No se pudieron cargar las alertas.'))
    }).catch(() => {
      if (!controller.signal.aborted) setError('No se pudo conectar con el servidor.')
    })
    return () => controller.abort()
  }, [cohortId, filter, offset, attempt])

  return (
    <Card title="Revisión de alertas" action={<Button variant="ghost" onClick={() => setAttempt(value => value + 1)}>Actualizar lista</Button>}>
      <div className="grid gap-3">
        <Field label="Estado" htmlFor="risk-state">
          <select id="risk-state" className={inputCls} value={filter} onChange={event => {
            setOffset(0)
            setFilter(event.target.value as typeof filter)
          }}>
            <option value="">Todos</option>
            {Object.entries(labels).map(([id, label]) => <option key={id} value={id}>{label}</option>)}
          </select>
        </Field>
        {!data && !error && <p role="status">Cargando alertas…</p>}
        {error && <Notice tone="warning" live="assertive">{error}</Notice>}
        {data && <>
          {data.items.length ? <ul className="grid gap-2">
            {data.items.map(alert => <li key={alert.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line p-3">
              <div><p className="font-medium">{alert.learner_name}</p>
                <p className="text-sm text-muted">{labels[alert.review_state]} · Corte {alert.cutoff} · Evidencia sintética</p>
              </div>
              <Button variant="ghost" onClick={() => setSelected(alert.id)}>Revisar alerta</Button>
            </li>)}
          </ul> : <p>No hay alertas sintéticas con este filtro.</p>}
          {(offset > 0 || offset + pageSize < data.total) && <nav aria-label="Páginas de alertas" className="flex gap-2">
            <Button variant="ghost" disabled={offset === 0} onClick={() => setOffset(offset - pageSize)}>Anterior</Button>
            <Button variant="ghost" disabled={offset + pageSize >= data.total} onClick={() => setOffset(offset + pageSize)}>Siguiente</Button>
          </nav>}
        </>}
      </div>
      {selected && <ReviewAlert cohortId={cohortId} id={selected} onClose={() => {
        setSelected('')
        setAttempt(value => value + 1)
      }} onSaved={() => setAttempt(value => value + 1)} />}
    </Card>
  )
}

export function ApiRiskAlerts() {
  const { cohorts, loading, error, retry } = useAcademicCohorts()
  const [selected, setSelected] = useState('')
  const cohort = cohorts.find(item => item.id === selected) ?? cohorts[0]
  return (
    <div className="grid gap-4">
      <PageTitle title="Alertas de apoyo" sub="Revisa evidencia sintética y registra acciones de apoyo de tu cohorte." />
      {loading && <p role="status">Cargando cohortes…</p>}
      {error && <><Notice tone="warning" live="assertive">{error}</Notice><Button onClick={retry}>Volver a cargar</Button></>}
      {!loading && !error && !cohort && <p>No hay cohortes disponibles en tu ámbito.</p>}
      {cohort && <>
        <Card>
          <Field label="Cohorte" htmlFor="risk-cohort">
            <select id="risk-cohort" className={inputCls} value={cohort.id} onChange={event => setSelected(event.target.value)}>
              {cohorts.map(item => <option key={item.id} value={item.id}>{item.nombre}</option>)}
            </select>
          </Field>
        </Card>
        <CohortAlerts key={cohort.id} cohortId={cohort.id} />
      </>}
    </div>
  )
}
