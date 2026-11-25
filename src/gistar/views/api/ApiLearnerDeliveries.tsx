import { useCallback } from 'react'
import { api } from '../../../shared/api/client'
import { Card, Empty, PageTitle } from '../../ui'
import { LearnerReadProblem, OwnEnrollmentPicker, requireLearnerResponse, useLearnerRead } from './OwnEnrollmentPicker'

const deadline = new Intl.DateTimeFormat('es-ES', { dateStyle: 'medium', timeStyle: 'short' })

function OwnDeliveries({ enrollmentId }: { enrollmentId: string }) {
  const load = useCallback(async (signal: AbortSignal) => requireLearnerResponse(
    await api.GET('/api/v1/enrollments/{enrollment_id}/submissions', {
      params: { path: { enrollment_id: enrollmentId } }, signal,
    }),
  ), [enrollmentId])
  const { state, retry } = useLearnerRead(load)

  if (!state) return <p role="status" className="text-muted">Cargando entregas…</p>
  if ('error' in state) return <LearnerReadProblem message={state.error} retry={retry} />
  if (!state.data.items.length) return <Empty>Aún no hay actividades publicadas para esta matrícula.</Empty>

  return (
    <div className="grid gap-4">
      {state.data.items.map(item => (
        <Card key={item.assignment_id} title={item.title}>
          <p className="text-sm text-muted">
            Plazo en tu zona horaria · <time dateTime={item.due_at}>{deadline.format(new Date(item.due_at))}</time>
          </p>
        </Card>
      ))}
    </div>
  )
}

export function ApiLearnerDeliveries() {
  return (
    <div className="space-y-5">
      <PageTitle title="Mis entregas" sub="Consulta las actividades publicadas para tu matrícula." />
      <OwnEnrollmentPicker fieldId="delivery-enrollment">
        {enrollment => <OwnDeliveries key={enrollment.enrollment_id} enrollmentId={enrollment.enrollment_id} />}
      </OwnEnrollmentPicker>
    </div>
  )
}
