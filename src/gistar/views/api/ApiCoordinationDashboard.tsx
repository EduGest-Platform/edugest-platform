import { useEffect, useState } from 'react'
import { api, errorMessage, type Schemas } from '../../../shared/api/client'
import { Card, Empty, Kpi, Notice, PageTitle } from '../../ui'

type Call = Schemas['CallOut']
type CallSummary = Schemas['CallSummaryOut']
type LoadState<T> = { status: 'loading' } | { status: 'ready'; data: T } | { status: 'error'; message: string }

function CoordinationSummary({ call }: { call: Call }) {
  const [summary, setSummary] = useState<LoadState<CallSummary>>({ status: 'loading' })

  useEffect(() => {
    const controller = new AbortController()
    void api.GET('/api/v1/calls/{call_id}/summary', {
      params: { path: { call_id: call.id } },
      signal: controller.signal,
    }).then(({ data, error }) => {
      if (controller.signal.aborted) return
      if (data?.call_id === call.id) setSummary({ status: 'ready', data })
      else setSummary({ status: 'error', message: errorMessage(error, 'No se pudo consultar el resumen.') })
    }).catch(() => {
      if (!controller.signal.aborted) setSummary({ status: 'error', message: 'No se pudo conectar con la API.' })
    })
    return () => controller.abort()
  }, [call.id])

  return (
    <Card title={call.nombre}>
      {summary.status === 'loading' && <p role="status">Cargando indicadores…</p>}
      {summary.status === 'error' && <Notice tone="warning" live="assertive">{summary.message}</Notice>}
      {summary.status === 'ready' && (
        <div className="grid gap-3 sm:grid-cols-2">
          <Kpi label="Plazas ofertadas" value={call.plazas} />
          <Kpi label="Candidaturas totales" value={summary.data.total ?? 'Ocultas'} />
        </div>
      )}
    </Card>
  )
}

export function ApiCoordinationDashboard() {
  const [calls, setCalls] = useState<LoadState<Call[]>>({ status: 'loading' })

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
  }, [])

  const firstCall = calls.status === 'ready' ? calls.data[0] : undefined
  return (
    <div className="space-y-5">
      <PageTitle title="Seguimiento de convocatorias" sub="Plazas e indicadores agregados de admisión del servidor." />
      {calls.status === 'loading' && <p role="status">Cargando convocatorias…</p>}
      {calls.status === 'error' && <Notice tone="warning" live="assertive">{calls.message}</Notice>}
      {calls.status === 'ready' && !firstCall && <Empty>No hay convocatorias publicadas.</Empty>}
      {firstCall && <CoordinationSummary key={firstCall.id} call={firstCall} />}
    </div>
  )
}
