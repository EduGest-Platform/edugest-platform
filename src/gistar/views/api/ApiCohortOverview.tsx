import { useEffect, useState } from 'react'
import { api, errorMessage, type Schemas } from '../../../shared/api/client'
import { Button, Card, Empty, Field, Notice, PageTitle, inputCls } from '../../ui'
import { useAcademicCohorts } from './ApiCohorts'

type Overview = Schemas['CohortProgressOverview']
type OverviewState = { data: Overview } | { error: string } | null

function OverviewForCohort({ cohortId }: { cohortId: string }) {
  const [state, setState] = useState<OverviewState>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    void api.GET('/api/v1/cohorts/{cohort_id}/progress-overview', {
      params: { path: { cohort_id: cohortId } },
      signal: controller.signal,
    }).then(({ data, error }) => {
      if (controller.signal.aborted) return
      if (data?.cohort_id === cohortId) setState({ data })
      else setState({ error: errorMessage(error, 'No se pudo cargar el progreso de esta cohorte.') })
    }).catch(() => {
      if (!controller.signal.aborted) setState({ error: 'No se pudo conectar con la API.' })
    })
    return () => controller.abort()
  }, [cohortId, attempt])

  function retry() {
    setState(null)
    setAttempt(previous => previous + 1)
  }

  if (state && 'error' in state) {
    return (
      <Card title="Resumen académico" action={<Button variant="ghost" onClick={retry}>Reintentar</Button>}>
        <Notice tone="warning" live="polite">{state.error}</Notice>
      </Card>
    )
  }

  const updated = state ? new Intl.DateTimeFormat(
    'es-ES', { dateStyle: 'medium', timeStyle: 'short', timeZone: state.data.timezone },
  ).format(new Date(state.data.generated_at)) : null

  return (
    <Card title="Resumen académico" action={<Button variant="ghost" onClick={retry} disabled={!state}>Actualizar datos</Button>}>
      {updated
        ? <p className="text-sm text-muted">Consulta generada el {updated} ({state?.data.timezone}).</p>
        : <p role="status" className="text-sm text-muted">Cargando resumen académico…</p>}
    </Card>
  )
}

export function ApiCohortOverview() {
  const { cohorts, loading, error, retry } = useAcademicCohorts()
  const [selected, setSelected] = useState('')
  const cohort = cohorts.find(item => item.id === selected) ?? cohorts[0]
  return (
    <div className="space-y-5">
      <PageTitle title="Analítica del grupo" sub="Consulta el progreso agregado de tus cohortes." />
      <Card title="Cohorte">
        {loading && <p role="status" className="text-sm text-muted">Cargando cohortes…</p>}
        {error && (
          <div className="space-y-3">
            <Notice tone="warning" live="polite">{error}</Notice>
            <Button variant="ghost" onClick={retry}>Reintentar</Button>
          </div>
        )}
        {!loading && !error && !cohort && <Empty>No hay cohortes con acceso académico en tu cuenta.</Empty>}
        {cohort && !loading && !error && (
          <Field label="Seleccionar cohorte" htmlFor="overview-cohort">
            <select id="overview-cohort" className={`${inputCls} max-w-md`} value={cohort.id} onChange={event => setSelected(event.target.value)}>
              {cohorts.map(item => <option key={item.id} value={item.id}>{item.nombre}</option>)}
            </select>
          </Field>
        )}
      </Card>
      {cohort && !loading && !error && <OverviewForCohort key={cohort.id} cohortId={cohort.id} />}
    </div>
  )
}
