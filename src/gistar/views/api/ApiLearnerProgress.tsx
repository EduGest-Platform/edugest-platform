import { useEffect, useState } from 'react'
import { api, type Schemas } from '../../../shared/api/client'
import { describeApiError, problemText } from '../../../shared/api/errors'
import { Button, Card, Empty, Field, Notice, PageTitle, inputCls } from '../../ui'

type Enrollment = Schemas['LearnerEnrollment']
type DataState<T> = { data: T } | { error: string } | null

const enrollmentStatus: Record<Enrollment['status'], string> = {
  activa: 'Activa',
  finalizada: 'Finalizada',
  baja_voluntaria: 'Baja voluntaria',
}

const deliveryStatus: Record<Schemas['EnrollmentDelivery']['state'], string> = {
  on_time: 'A tiempo',
  late: 'Con retraso',
  pending: 'Pendiente',
  overdue: 'Vencida',
}

function requireResponse<T>({ data, response }: { data?: T; response: Response }): T {
  if (data === undefined) throw new Error(problemText(describeApiError(response.status)))
  return data
}

async function loadProgress(enrollmentId: string, signal: AbortSignal) {
  const params = { path: { enrollment_id: enrollmentId } }
  const [attendance, competencies, deliveries] = await Promise.all([
    api.GET('/api/v1/me/enrollments/{enrollment_id}/attendance', { params, signal }),
    api.GET('/api/v1/me/enrollments/{enrollment_id}/competencies', { params, signal }),
    api.GET('/api/v1/enrollments/{enrollment_id}/submissions', { params, signal }),
  ])
  return {
    attendance: requireResponse(attendance),
    competencies: requireResponse(competencies),
    deliveries: requireResponse(deliveries),
  }
}

function LoadProblem({ message, retry }: { message: string; retry: () => void }) {
  return (
    <div className="space-y-3">
      <Notice tone="warning" live="polite">{message}</Notice>
      <Button variant="ghost" onClick={retry}>Reintentar</Button>
    </div>
  )
}

function loadError(error: unknown) {
  return error instanceof TypeError
    ? problemText(describeApiError(undefined))
    : error instanceof Error ? error.message : 'No se ha podido cargar el progreso.'
}

function LatestProgress({ enrollmentId }: { enrollmentId: string }) {
  const [state, setState] = useState<DataState<Awaited<ReturnType<typeof loadProgress>>>>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    loadProgress(enrollmentId, controller.signal)
      .then(data => {
        if (!controller.signal.aborted) setState({ data })
      })
      .catch(error => {
        if (!controller.signal.aborted) setState({ error: loadError(error) })
      })
    return () => controller.abort()
  }, [enrollmentId, attempt])

  if (!state) return <p role="status" className="text-muted">Cargando progreso…</p>
  if ('error' in state) {
    return <LoadProblem message={state.error} retry={() => { setState(null); setAttempt(attempt + 1) }} />
  }

  const { attendance, competencies, deliveries } = state.data
  const { totals, timezone } = attendance
  const number = new Intl.NumberFormat('es-ES')
  const date = new Intl.DateTimeFormat('es-ES', { dateStyle: 'medium', timeZone: timezone })
  const deadline = new Intl.DateTimeFormat('es-ES', { dateStyle: 'medium', timeStyle: 'short', timeZone: timezone })
  const attendanceRows = [
    ['Presencial', totals.attended_in_person_days],
    ['Online', totals.attended_online_days],
    ['Ausencia justificada', totals.justified_absence_days],
    ['Ausencia sin justificar', totals.unjustified_absence_days],
    ['Sin registrar', totals.unrecorded_days],
  ] as const

  return (
    <div className="grid items-start gap-5 lg:grid-cols-2">
      <Card title="Asistencia">
        {totals.held_days === 0 ? <Empty>Aún no hay sesiones celebradas.</Empty> : (
          <dl className="divide-y divide-line text-sm">
            {attendanceRows.map(([label, days]) => (
              <div key={label} className="flex justify-between gap-4 py-2">
                <dt>{label}</dt><dd>{number.format(days)} días</dd>
              </div>
            ))}
          </dl>
        )}
      </Card>
      <Card title="Competencias">
        {competencies.current.length === 0 ? <Empty>Aún no hay un árbol de competencias asignado.</Empty> : (
          <ul className="divide-y divide-line text-sm">
            {competencies.current.map(competency => (
              <li key={competency.competency_id} className="flex flex-wrap justify-between gap-2 py-2">
                <span>{competency.nombre}</span>
                <span className="text-muted">
                  {competency.level === null ? 'Sin evaluar' : `Nivel ${competency.level}`}
                  {competency.assessed_at && <> · {date.format(new Date(competency.assessed_at))}</>}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>
      <Card title="Entregas" className="lg:col-span-2">
        {deliveries.items.length === 0 ? <Empty>Aún no hay actividades publicadas.</Empty> : (
          <ul className="divide-y divide-line text-sm">
            {deliveries.items.map(delivery => (
              <li key={delivery.assignment_id} className="flex flex-wrap justify-between gap-2 py-2">
                <span>{delivery.title}</span>
                <span className="text-muted">
                  {deliveryStatus[delivery.state]}{delivery.reviewed && ' · Revisada'}
                  {' · '}{deadline.format(new Date(delivery.due_at))}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}

export function ApiLearnerProgress() {
  const [state, setState] = useState<DataState<Enrollment[]>>(null)
  const [attempt, setAttempt] = useState(0)
  const [selectedId, setSelectedId] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    api.GET('/api/v1/me/enrollments', { signal: controller.signal })
      .then(result => {
        if (controller.signal.aborted) return
        const { items } = requireResponse(result)
        setState({ data: items })
        setSelectedId(previous => items.find(item => item.enrollment_id === previous)?.enrollment_id
          ?? items.find(item => item.status === 'activa')?.enrollment_id ?? items[0]?.enrollment_id ?? '')
      })
      .catch(error => {
        if (!controller.signal.aborted) setState({ error: loadError(error) })
      })
    return () => controller.abort()
  }, [attempt])

  const enrolled = state && 'data' in state ? state.data : []
  const selected = enrolled.find(item => item.enrollment_id === selectedId)
  return (
    <div className="space-y-5">
      <PageTitle title="Mi progreso" sub="Consulta la asistencia, las competencias y las entregas de tu matrícula." />
      {!state && <p role="status" className="text-muted">Cargando matrículas…</p>}
      {state && 'error' in state && (
        <LoadProblem message={state.error} retry={() => { setState(null); setAttempt(attempt + 1) }} />
      )}
      {state && 'data' in state && enrolled.length === 0 && <Empty>No tienes matrículas asociadas.</Empty>}
      {selected && (
        <>
          <Field label="Matrícula" htmlFor="learner-enrollment">
            <select
              id="learner-enrollment"
              className={`${inputCls} max-w-md`}
              value={selectedId}
              onChange={event => setSelectedId(event.target.value)}
            >
              {enrolled.map(item => (
                <option key={item.enrollment_id} value={item.enrollment_id}>
                  {item.cohort_name} · {enrollmentStatus[item.status]}
                </option>
              ))}
            </select>
          </Field>
          {selected.status === 'activa'
            ? <LatestProgress key={selectedId} enrollmentId={selectedId} />
            : <Empty>El progreso está disponible para matrículas activas.</Empty>}
        </>
      )}
    </div>
  )
}
