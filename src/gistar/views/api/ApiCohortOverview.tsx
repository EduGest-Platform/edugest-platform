import { useEffect, useState, type FormEvent } from 'react'
import { api, errorMessage, type Schemas } from '../../../shared/api/client'
import { Button, Card, Empty, Field, Notice, PageTitle, inputCls } from '../../ui'
import { useAcademicCohorts } from './ApiCohorts'
import { OverviewAttendanceCard } from './OverviewAttendanceCard'

type Overview = Schemas['CohortProgressOverview']
type OverviewState = { data: Overview } | { error: string } | null
type AttendancePeriod = { attendance_from?: string; attendance_to?: string }

function OverviewForCohort({ cohortId }: { cohortId: string }) {
  const [state, setState] = useState<OverviewState>(null)
  const [period, setPeriod] = useState<AttendancePeriod>({})
  const [invalidPeriod, setInvalidPeriod] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    void api.GET('/api/v1/cohorts/{cohort_id}/progress-overview', {
      params: { path: { cohort_id: cohortId }, query: period },
      signal: controller.signal,
    }).then(({ data, error }) => {
      if (controller.signal.aborted) return
      if (data?.cohort_id === cohortId) setState({ data })
      else setState({ error: errorMessage(error, 'No se pudo cargar el progreso de esta cohorte.') })
    }).catch(() => {
      if (!controller.signal.aborted) setState({ error: 'No se pudo conectar con la API.' })
    })
    return () => controller.abort()
  }, [cohortId, period])

  function loadPeriod(next: AttendancePeriod) {
    setState(null)
    setPeriod(next)
  }

  function applyPeriod(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const fields = new FormData(event.currentTarget)
    const from = String(fields.get('attendance_from') ?? '')
    const to = String(fields.get('attendance_to') ?? '')
    if (from && to && from > to) {
      setInvalidPeriod(true)
      return
    }
    setInvalidPeriod(false)
    loadPeriod({ attendance_from: from || undefined, attendance_to: to || undefined })
  }

  const data = state && 'data' in state ? state.data : null
  const updated = data ? new Intl.DateTimeFormat(
    'es-ES', { dateStyle: 'medium', timeStyle: 'short', timeZone: data.timezone },
  ).format(new Date(data.generated_at)) : null

  return (
    <>
      <Card title="Resumen académico">
        <form className="flex flex-wrap items-end gap-3" onSubmit={applyPeriod} onChange={() => setInvalidPeriod(false)}>
          <Field label="Asistencia desde" htmlFor="overview-attendance-from">
            <input id="overview-attendance-from" name="attendance_from" className={inputCls} type="date"
              aria-invalid={invalidPeriod || undefined} aria-describedby={invalidPeriod ? 'overview-period-error' : undefined} />
          </Field>
          <Field label="Asistencia hasta" htmlFor="overview-attendance-to">
            <input id="overview-attendance-to" name="attendance_to" className={inputCls} type="date"
              aria-invalid={invalidPeriod || undefined} aria-describedby={invalidPeriod ? 'overview-period-error' : undefined} />
          </Field>
          <Button type="submit">Aplicar periodo</Button>
        </form>
        {invalidPeriod && <p id="overview-period-error" role="alert" className="mt-3 text-sm text-amber-800">
          La fecha de inicio debe ser anterior o igual a la fecha final.
        </p>}
        {!state && <p role="status" className="mt-4 text-sm text-muted">Cargando resumen académico…</p>}
        {state && 'error' in state && (
          <div className="mt-4 space-y-3">
            <Notice tone="warning" live="polite">{state.error}</Notice>
            <Button variant="ghost" onClick={() => loadPeriod({ ...period })}>Reintentar</Button>
          </div>
        )}
        {updated && <p className="mt-4 text-sm text-muted">Consulta generada el {updated} ({data?.timezone}).</p>}
      </Card>
      {data && <OverviewAttendanceCard attendance={data.attendance} />}
    </>
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
