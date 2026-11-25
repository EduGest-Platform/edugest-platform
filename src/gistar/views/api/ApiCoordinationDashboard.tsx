import { useEffect, useState } from 'react'
import { api, errorMessage, type Schemas } from '../../../shared/api/client'
import { humanize } from '../../config'
import { Button, Card, Empty, Field, Kpi, Notice, PageTitle, inputCls } from '../../ui'

type Call = Schemas['CallOut']
type CallSummary = Schemas['CallSummaryOut']
type LoadState<T> = { status: 'loading' } | { status: 'ready'; data: T } | { status: 'error'; message: string }

function CoordinationSummary({ call }: { call: Call }) {
  const [summary, setSummary] = useState<LoadState<CallSummary> | { status: 'denied' }>({ status: 'loading' })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    void api.GET('/api/v1/calls/{call_id}/summary', {
      params: { path: { call_id: call.id } },
      signal: controller.signal,
    }).then(({ data, error, response }) => {
      if (controller.signal.aborted) return
      if (response.status === 403) setSummary({ status: 'denied' })
      else if (data?.call_id === call.id) setSummary({ status: 'ready', data })
      else setSummary({ status: 'error', message: errorMessage(error, 'No se pudo consultar el resumen.') })
    }).catch(() => {
      if (!controller.signal.aborted) setSummary({ status: 'error', message: 'No se pudo conectar con la API.' })
    })
    return () => controller.abort()
  }, [call.id, attempt])

  return (
    <Card title={call.nombre} action={
      <Button variant="ghost" onClick={() => {
        setSummary({ status: 'loading' })
        setAttempt(value => value + 1)
      }}>Actualizar indicadores</Button>
    }>
      {summary.status === 'loading' && <p role="status">Cargando indicadores…</p>}
      {summary.status === 'denied' && (
        <Notice tone="warning" live="assertive">Tu cuenta no tiene permiso para consultar los indicadores de esta convocatoria.</Notice>
      )}
      {summary.status === 'error' && <Notice tone="warning" live="assertive">{summary.message}</Notice>}
      {summary.status === 'ready' && (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <Kpi label="Plazas ofertadas" value={call.plazas} />
            <Kpi label="Candidaturas totales" value={summary.data.total ?? 'Ocultas'} />
          </div>
          {summary.data.suppressed ? (
            <Notice live="polite">El total y el desglose se ocultan si hay menos de {summary.data.min_group_size} candidaturas.</Notice>
          ) : (
            <>
              <h3 className="font-semibold text-ink">Candidaturas por etapa</h3>
              <p className="text-sm text-muted">Cada etapa forma parte del total de la convocatoria. Las cifras positivas inferiores a {summary.data.min_cell_size} se ocultan.</p>
              <dl className="grid gap-x-6 gap-y-2 sm:grid-cols-2">
                {summary.data.by_stage.map(({ stage, count }) => (
                  <div key={stage} className="flex items-baseline justify-between gap-3 border-b border-line py-2">
                    <dt className="text-sm">{humanize(stage)}</dt>
                    <dd className="text-sm font-semibold tabular-nums">{count ?? 'Oculta'}</dd>
                  </div>
                ))}
              </dl>
            </>
          )}
        </div>
      )}
    </Card>
  )
}

export function ApiCoordinationDashboard() {
  const [calls, setCalls] = useState<LoadState<Call[]>>({ status: 'loading' })
  const [programId, setProgramId] = useState('')
  const [callId, setCallId] = useState('')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    void api.GET('/api/v1/calls', { signal: controller.signal }).then(({ data, error }) => {
      if (controller.signal.aborted) return
      if (data) setCalls({ status: 'ready', data })
      else setCalls({ status: 'error', message: errorMessage(error, 'No se pudieron cargar las convocatorias.') })
    }).catch(() => {
      if (!controller.signal.aborted) setCalls({ status: 'error', message: 'No se pudo conectar con la API.' })
    })
    return () => controller.abort()
  }, [attempt])

  const available = calls.status === 'ready' ? calls.data : []
  const programs = new Map(available.map(call => [call.program_id, call.program_nombre]))
  const visible = programId ? available.filter(call => call.program_id === programId) : available
  const call = visible.find(item => item.id === callId) ?? visible[0]

  return (
    <div className="space-y-5">
      <PageTitle title="Seguimiento de convocatorias" sub="Plazas e indicadores agregados de admisión del servidor." />
      {calls.status === 'loading' && <p role="status">Cargando convocatorias…</p>}
      {calls.status === 'error' && (
        <div>
          <Notice tone="warning" live="assertive">{calls.message}</Notice>
          <Button variant="ghost" onClick={() => {
            setCalls({ status: 'loading' })
            setAttempt(value => value + 1)
          }}>Reintentar convocatorias</Button>
        </div>
      )}
      {calls.status === 'ready' && !available.length && <Empty>No hay convocatorias publicadas.</Empty>}
      {Boolean(available.length) && (
        <Card title="Filtros del seguimiento">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Programa" htmlFor="coordination-program">
              <select id="coordination-program" className={inputCls} value={programId} onChange={event => {
                setProgramId(event.target.value)
                setCallId('')
              }}>
                <option value="">Todos los programas</option>
                {[...programs].map(([id, name]) => <option key={id} value={id}>{name}</option>)}
              </select>
            </Field>
            <Field label="Convocatoria" htmlFor="coordination-call">
              <select id="coordination-call" className={inputCls} value={call?.id ?? ''} onChange={event => setCallId(event.target.value)}>
                {visible.map(item => <option key={item.id} value={item.id}>{item.nombre}</option>)}
              </select>
            </Field>
          </div>
        </Card>
      )}
      {call && <CoordinationSummary key={call.id} call={call} />}
    </div>
  )
}
