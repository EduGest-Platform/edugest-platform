import { useEffect, useRef, useState, type FormEvent } from 'react'
import { api, type Schemas } from '../../../shared/api/client'
import { describeApiError, problemText } from '../../../shared/api/errors'
import { Button, Field, Notice, inputCls } from '../../ui'

const timestamp = new Intl.DateTimeFormat('es-ES', { dateStyle: 'short', timeStyle: 'short', timeZone: 'Europe/Madrid' })
const kinds = { documentation: 'Documentación', exercises: 'Ejercicios' }

export function RecruitmentReminders({ applicationId, canSimulate }: { applicationId: string; canSimulate: boolean }) {
  const [history, setHistory] = useState<Schemas['SimulatedReminderList'] | null>(null)
  const [historyError, setHistoryError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [taskRef, setTaskRef] = useState('')
  const [kind, setKind] = useState<keyof typeof kinds>('documentation')
  const [due, setDue] = useState('')
  const [busy, setBusy] = useState(false)
  const [feedback, setFeedback] = useState('')
  const [error, setError] = useState('')
  const pending = useRef<AbortController | null>(null)
  useEffect(() => () => pending.current?.abort(), [])

  useEffect(() => {
    const controller = new AbortController()
    void api.GET('/api/v1/applications/{application_id}/simulated-reminders', {
      params: { path: { application_id: applicationId } }, signal: controller.signal,
    }).then(({ data, error, response }) => {
      if (controller.signal.aborted) return
      if (data) setHistory(data)
      else setHistoryError(problemText(describeApiError(response.status, error)))
    }).catch(() => {
      if (!controller.signal.aborted) setHistoryError('No se pudo conectar con el servidor.')
    })
    return () => controller.abort()
  }, [applicationId, attempt])

  function reload() {
    setHistory(null)
    setHistoryError('')
    setAttempt(value => value + 1)
  }

  async function simulate(event: FormEvent) {
    event.preventDefault()
    if (!canSimulate || pending.current) return
    const date = new Date(due)
    if (!Number.isFinite(date.valueOf())) {
      setError('Selecciona una fecha y hora válidas.')
      return
    }
    const controller = new AbortController()
    pending.current = controller
    setBusy(true)
    setError('')
    setFeedback('')
    try {
      const { data, error, response } = await api.POST('/api/v1/applications/{application_id}/simulated-reminders', {
        params: { path: { application_id: applicationId } }, signal: controller.signal,
        body: { task_ref: taskRef.trim(), kind, due_at: date.toISOString(), synthetic_only: true },
      })
      if (controller.signal.aborted) return
      if (!data) setError(problemText(describeApiError(response.status, error)))
      else if (data.outcome === 'not_due') setFeedback('El plazo aún no ha vencido.')
      else {
        setFeedback(response.status === 201 ? 'Simulación registrada.' : 'Esta simulación ya estaba registrada.')
        reload()
      }
    } catch {
      if (!controller.signal.aborted) setError('No se pudo confirmar la simulación. Actualiza el historial antes de reintentar.')
    } finally {
      pending.current = null
      if (!controller.signal.aborted) setBusy(false)
    }
  }

  return (
    <section aria-label="Recordatorios simulados" className="grid gap-3 rounded-xl border border-line p-3">
      <h3 className="font-semibold">Recordatorios simulados</h3>
      <p className="text-sm text-muted">La simulación deja constancia en el historial. El canal de envío permanece desactivado.</p>
      {canSimulate && (
        <form className="grid gap-3" onSubmit={simulate}>
          <Field label="Referencia sintética" htmlFor="reminder-reference" hint="Ejemplo: synthetic-docs-v1">
            <input id="reminder-reference" className={inputCls} required minLength={11} maxLength={80}
              pattern="synthetic-[a-z][a-z0-9]*(?:-[a-z0-9]+)*" value={taskRef} readOnly={busy} onChange={event => setTaskRef(event.target.value)} />
          </Field>
          <Field label="Tipo de tarea" htmlFor="reminder-kind">
            <select id="reminder-kind" className={inputCls} value={kind} disabled={busy}
              onChange={event => setKind(event.target.value === 'exercises' ? 'exercises' : 'documentation')}>
              <option value="documentation">Documentación</option>
              <option value="exercises">Ejercicios</option>
            </select>
          </Field>
          <Field label="Vencimiento (hora local del dispositivo)" htmlFor="reminder-due">
            <input id="reminder-due" className={inputCls} required type="datetime-local" value={due}
              readOnly={busy} onChange={event => setDue(event.target.value)} />
          </Field>
          <Button type="submit" className="justify-self-start" disabled={busy}>{busy ? 'Simulando…' : 'Simular recordatorio'}</Button>
        </form>
      )}
      {!canSimulate && <p className="text-sm">Las nuevas simulaciones están disponibles durante la preselección.</p>}
      {feedback && <p role="status">{feedback}</p>}
      {error && <Notice tone="warning" live="assertive">{error}</Notice>}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 className="font-medium">Historial de simulaciones</h4>
        <Button size="sm" variant="ghost" onClick={reload} disabled={busy}>Actualizar historial</Button>
      </div>
      {historyError && <Notice tone="warning" live="assertive">{historyError}</Notice>}
      {!history && !historyError && <p role="status">Cargando historial…</p>}
      {history && (history.total ? <>
        <p className="text-sm text-muted">{history.items.length} de {history.total} simulaciones. Horas en Europe/Madrid.</p>
        <ul className="grid gap-2">
          {history.items.map(item => (
            <li key={item.id} className="border-b border-line pb-2 text-sm">
              <p>{kinds[item.kind]} · {item.task_ref}</p>
              <p className="text-xs text-muted">Venció el {timestamp.format(new Date(item.due_at))} · Simulado el {timestamp.format(new Date(item.simulated_at))}</p>
            </li>
          ))}
        </ul>
      </> : <p className="text-sm">Todavía no hay simulaciones.</p>)}
    </section>
  )
}
