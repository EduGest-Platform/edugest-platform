import { useEffect, useState } from 'react'
import { api, errorMessage, type Schemas } from '../../../shared/api/client'
import { Button, Card, Field, Notice, inputCls } from '../../ui'

const PAGE_SIZE = 25

export function RecruitmentInbox({ onOpen, revision }: { onOpen: (id: string) => void; revision: number }) {
  const [mine, setMine] = useState(false)
  const [dueThrough, setDueThrough] = useState('')
  const [offset, setOffset] = useState(0)
  const [attempt, setAttempt] = useState(0)
  const [data, setData] = useState<Schemas['RecruitmentInbox'] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    setData(null)
    setError('')
    const controller = new AbortController()
    void api.GET('/api/v1/recruitment/inbox', {
      params: { query: { mine, due_through: dueThrough || undefined, offset, limit: PAGE_SIZE } },
      signal: controller.signal,
    }).then(({ data, error }) => {
      if (controller.signal.aborted) return
      if (data) setData(data)
      else setError(errorMessage(error, 'No se pudieron cargar las próximas acciones.'))
    }).catch(() => {
      if (!controller.signal.aborted) setError('No se pudo conectar con el servidor.')
    })
    return () => controller.abort()
  }, [mine, dueThrough, offset, attempt, revision])

  return (
    <Card title="Bandeja de captación" action={<Button variant="ghost" onClick={() => setAttempt(value => value + 1)}>Actualizar bandeja</Button>}>
      <div className="grid gap-4">
        <p className="text-sm text-muted">Última próxima acción registrada en cada candidatura que sigue en preselección.</p>
        <div className="flex flex-wrap items-end gap-4">
          <Field label="Próximas acciones hasta" htmlFor="recruitment-inbox-due">
            <input id="recruitment-inbox-due" type="date" className={inputCls} value={dueThrough} onChange={event => {
              setOffset(0); setDueThrough(event.target.value)
            }} />
          </Field>
          <label className="mb-2 flex items-center gap-2 text-sm">
            <input type="checkbox" checked={mine} onChange={event => {
              setOffset(0); setMine(event.target.checked)
            }} />
            Solo las asignadas a mí
          </label>
        </div>
        {error && <Notice live="assertive" tone="warning">{error}</Notice>}
        {!data && !error && <p role="status">Cargando próximas acciones…</p>}
        {data && <>
          <p role="status" className="text-sm text-muted">{data.total} próximas acciones con estos filtros.</p>
          {!data.items.length && <p>No hay próximas acciones en esta página.</p>}
          <ul className="grid gap-2">
            {data.items.map(item => (
              <li key={item.application_id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line p-3">
                <div className="min-w-0">
                  <p className="font-medium wrap-anywhere">{item.action.description}</p>
                  <p className="text-sm text-muted">{item.code} · {item.call_id} · {item.action.owner} · Hasta <time dateTime={item.action.due_on}>{item.action.due_on}</time></p>
                </div>
                <Button variant="ghost" size="sm" aria-label={`Abrir expediente ${item.code} desde la bandeja`} onClick={() => onOpen(item.application_id)}>Abrir expediente</Button>
              </li>
            ))}
          </ul>
          {(offset > 0 || offset + PAGE_SIZE < data.total) && <nav aria-label="Páginas de próximas acciones" className="flex flex-wrap gap-3">
            <Button variant="ghost" disabled={offset === 0} onClick={() => setOffset(offset - PAGE_SIZE)}>Anterior</Button>
            <Button variant="ghost" disabled={offset + PAGE_SIZE >= data.total} onClick={() => setOffset(offset + PAGE_SIZE)}>Siguiente</Button>
          </nav>}
        </>}
      </div>
    </Card>
  )
}
