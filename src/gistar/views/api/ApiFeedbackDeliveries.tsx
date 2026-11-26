import { useEffect, useState } from 'react'
import { api, errorMessage, type Schemas } from '../../../shared/api/client'
import { useGistar } from '../../store'
import { Button, Card, Field, Notice, PageTitle, inputCls } from '../../ui'
import { useAcademicCohorts } from './ApiCohorts'
import { ApiLearnerDeliveries } from './ApiLearnerDeliveries'
import { FeedbackReviewModal } from './FeedbackReviewModal'

const PAGE_SIZE = 25

function FeedbackQueue({ cohortId }: { cohortId: string }) {
  const [data, setData] = useState<Schemas['FeedbackQueue']>()
  const [offset, setOffset] = useState(0)
  const [attempt, setAttempt] = useState(0)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState<Schemas['FeedbackQueueItem'] | null>(null)

  useEffect(() => {
    setData(undefined)
    setError('')
    const controller = new AbortController()
    void api.GET('/api/v1/cohorts/{cohort_id}/feedback-queue', {
      params: { path: { cohort_id: cohortId }, query: { offset, limit: PAGE_SIZE } }, signal: controller.signal,
    }).then(result => {
      if (controller.signal.aborted) return
      if (result.data) setData(result.data)
      else setError(errorMessage(result.error, 'No se pudieron consultar las entregas.'))
    }).catch(() => {
      if (!controller.signal.aborted) setError('No se pudo conectar con el servidor.')
    })
    return () => controller.abort()
  }, [cohortId, offset, attempt])

  return (
    <Card title="Entregas para revisar" action={<Button variant="ghost" onClick={() => setAttempt(value => value + 1)}>Actualizar entregas</Button>}>
      {error && <Notice tone="warning" live="assertive">{error}</Notice>}
      {!data && !error && <p role="status">Cargando entregas…</p>}
      {data && <>
        {!data.items.length && <p>No hay entregas en esta página.</p>}
        <ul className="grid gap-2">
          {data.items.map(item => <li key={item.submission_id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-line p-3">
            <div>
              <p className="font-medium">{item.assignment_title} · {item.learner_name}</p>
              <p className="text-sm text-muted">Revisión {item.revision}{!item.has_check_results && ' · Sin resultados de tests'}</p>
            </div>
            <Button variant="ghost" onClick={() => setSelected(item)}>Revisar feedback</Button>
          </li>)}
        </ul>
        {(offset > 0 || offset + PAGE_SIZE < data.total) && <nav aria-label="Páginas de entregas" className="mt-3 flex gap-2">
          <Button variant="ghost" disabled={offset === 0} onClick={() => setOffset(offset - PAGE_SIZE)}>Anterior</Button>
          <Button variant="ghost" disabled={offset + PAGE_SIZE >= data.total} onClick={() => setOffset(offset + PAGE_SIZE)}>Siguiente</Button>
        </nav>}
      </>}
      {selected && <FeedbackReviewModal item={selected} onClose={() => setSelected(null)} />}
    </Card>
  )
}

function TeacherDeliveryFeedback() {
  const { cohorts, loading, error, retry } = useAcademicCohorts()
  const [selected, setSelected] = useState('')
  const cohort = cohorts.find(item => item.id === selected) ?? cohorts[0]
  return (
    <div className="grid gap-4">
      <PageTitle title="Entregas y feedback" sub="Genera, revisa y publica feedback de las entregas de tu cohorte." />
      {loading && <p role="status">Cargando cohortes…</p>}
      {error && <><Notice tone="warning" live="assertive">{error}</Notice><Button onClick={retry}>Volver a cargar</Button></>}
      {!loading && !error && !cohort && <p>No hay cohortes disponibles en tu ámbito.</p>}
      {cohort && <>
        <Card>
          <Field label="Cohorte" htmlFor="feedback-cohort">
            <select id="feedback-cohort" className={inputCls} value={cohort.id} onChange={event => setSelected(event.target.value)}>
              {cohorts.map(item => <option key={item.id} value={item.id}>{item.nombre}</option>)}
            </select>
          </Field>
        </Card>
        <FeedbackQueue key={cohort.id} cohortId={cohort.id} />
      </>}
    </div>
  )
}

export function ApiFeedbackDeliveries() {
  const { role } = useGistar()
  return role === 'docente' ? <TeacherDeliveryFeedback /> : <ApiLearnerDeliveries />
}
