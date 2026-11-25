import { useCallback } from 'react'
import { api, type Schemas } from '../../../shared/api/client'
import { Card, Empty, PageTitle } from '../../ui'
import { LearnerReadProblem, OwnEnrollmentPicker, requireLearnerResponse, useLearnerRead } from './OwnEnrollmentPicker'

const deliveryStatus: Record<Schemas['EnrollmentDelivery']['state'], string> = {
  on_time: 'A tiempo',
  late: 'Con retraso',
  pending: 'Pendiente',
  overdue: 'Vencida',
}

async function loadProgress(enrollmentId: string, signal: AbortSignal) {
  const params = { path: { enrollment_id: enrollmentId } }
  const [attendance, competencies, deliveries] = await Promise.all([
    api.GET('/api/v1/me/enrollments/{enrollment_id}/attendance', { params, signal }),
    api.GET('/api/v1/me/enrollments/{enrollment_id}/competencies', { params, signal }),
    api.GET('/api/v1/enrollments/{enrollment_id}/submissions', { params, signal }),
  ])
  return {
    attendance: requireLearnerResponse(attendance),
    competencies: requireLearnerResponse(competencies),
    deliveries: requireLearnerResponse(deliveries),
  }
}

function LatestProgress({ enrollmentId }: { enrollmentId: string }) {
  const load = useCallback((signal: AbortSignal) => loadProgress(enrollmentId, signal), [enrollmentId])
  const { state, retry } = useLearnerRead(load)
  if (!state) return <p role="status" className="text-muted">Cargando progreso…</p>
  if ('error' in state) return <LearnerReadProblem message={state.error} retry={retry} />

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
  return (
    <div className="space-y-5">
      <PageTitle title="Mi progreso" sub="Consulta la asistencia, las competencias y las entregas de tu matrícula." />
      <OwnEnrollmentPicker fieldId="learner-enrollment">
        {enrollment => <LatestProgress key={enrollment.enrollment_id} enrollmentId={enrollment.enrollment_id} />}
      </OwnEnrollmentPicker>
    </div>
  )
}
