import { useCallback, useState } from 'react'
import { api } from '../../../shared/api/client'
import { Card, Empty, Field, PageTitle, Status, inputCls } from '../../ui'
import { deliveryStateLabel, matchesDeliveryFilter, type DeliveryFilter } from './learnerDeliveryStates'
import { validPortfolioLink } from './portfolioLink'
import { LearnerReadProblem, OwnEnrollmentPicker, requireLearnerResponse, useLearnerRead } from './OwnEnrollmentPicker'

const deadline = new Intl.DateTimeFormat('es-ES', { dateStyle: 'medium', timeStyle: 'short' })

function PortfolioReference({ value, title }: { value: string; title: string }) {
  const href = validPortfolioLink(value)
  return href ? (
    <a href={href} target="_blank" rel="noopener noreferrer"
      aria-label={`Abrir portfolio de ${title} en otra pestaña`}
      className="mt-2 inline-block text-sm font-medium text-blue underline">
      Abrir portfolio
    </a>
  ) : <p className="mt-2 text-sm text-muted">El enlace guardado requiere un formato HTTPS válido.</p>
}

function OwnDeliveries({ enrollmentId }: { enrollmentId: string }) {
  const [filter, setFilter] = useState<DeliveryFilter>('all')
  const load = useCallback(async (signal: AbortSignal) => requireLearnerResponse(
    await api.GET('/api/v1/enrollments/{enrollment_id}/submissions', {
      params: { path: { enrollment_id: enrollmentId } }, signal,
    }),
  ), [enrollmentId])
  const { state, retry } = useLearnerRead(load)

  if (!state) return <p role="status" className="text-muted">Cargando entregas…</p>
  if ('error' in state) return <LearnerReadProblem message={state.error} retry={retry} />
  if (!state.data.items.length) return <Empty>Aún no hay actividades publicadas para esta matrícula.</Empty>

  const visible = state.data.items.filter(item => matchesDeliveryFilter(item, filter))
  return (
    <div className="grid gap-4">
      <Field label="Estado de entrega" htmlFor="delivery-filter">
        <select id="delivery-filter" className={`${inputCls} max-w-md`} value={filter}
          onChange={event => setFilter(event.target.value as DeliveryFilter)}>
          <option value="all">Todas las actividades</option>
          <option value="outstanding">Pendientes y vencidas</option>
          <option value="delivered">Entregadas por revisar</option>
          <option value="reviewed">Revisadas</option>
        </select>
      </Field>
      <p role="status" className="text-sm text-muted">{visible.length} de {state.data.items.length} actividades</p>
      {!visible.length && <Empty>No hay actividades con este estado.</Empty>}
      {visible.map(item => (
        <Card key={item.assignment_id} title={item.title} action={
          <div className="flex flex-wrap gap-2">
            <Status s={item.state === 'overdue' || item.state === 'late' ? 'fuera_de_plazo' : item.state === 'on_time' ? 'enviada' : 'en_seguimiento'}
              label={deliveryStateLabel[item.state]} />
            {item.reviewed && <Status s="completada" label="Revisada" />}
          </div>
        }>
          <p className="text-sm text-muted">
            Plazo en tu zona horaria · <time dateTime={item.due_at}>{deadline.format(new Date(item.due_at))}</time>
          </p>
          <p className="mt-2 text-sm">
            {item.submission ? (
              <>Primer envío · <time dateTime={item.submission.first_submitted_at}>{deadline.format(new Date(item.submission.first_submitted_at))}</time></>
            ) : 'Aún no hay un envío registrado.'}
          </p>
          {item.submission?.portfolio_url && <PortfolioReference value={item.submission.portfolio_url} title={item.title} />}
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
