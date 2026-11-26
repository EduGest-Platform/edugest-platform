import { useState } from 'react'
import { EVENT_TYPES, nowOf } from '../domain'
import { fmtShort, timeOf } from '../dates'
import { useGistar } from '../store'
import type { EventType } from '../types'
import { Button, Card, Field, PageTitle, inputCls } from '../ui'
import { useVisibleItems } from './Calendar'
import { eventPhase, filterEvents } from '../events'

export function Events() {
  const { data, navigate } = useGistar()
  const [query, setQuery] = useState('')
  const [type, setType] = useState<EventType | ''>('')
  const [upcoming, setUpcoming] = useState(true)
  const now = nowOf(data)
  const items = filterEvents(useVisibleItems(), now, query, type, upcoming)

  return (
    <>
      <PageTitle title="Eventos" sub="Actividades de tu ámbito. Horario Europe/Madrid · datos de demostración." />
      <Card title="Buscar eventos">
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Buscar por título" htmlFor="events-query">
            <input id="events-query" className={inputCls} value={query} onChange={event => setQuery(event.target.value)} />
          </Field>
          <Field label="Tipo de evento" htmlFor="events-type">
            <select id="events-type" className={inputCls} value={type} onChange={event => setType(event.target.value as EventType | '')}>
              <option value="">Todos los tipos</option>
              {(Object.keys(EVENT_TYPES) as EventType[]).filter(key => key !== 'entrega').map(key => <option key={key} value={key}>{EVENT_TYPES[key].label}</option>)}
            </select>
          </Field>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={upcoming} onChange={event => setUpcoming(event.target.checked)} /> Solo próximos eventos y en curso
          </label>
          <Button variant="ghost" disabled={!query && !type && upcoming} onClick={() => { setQuery(""); setType(""); setUpcoming(true) }}>Restablecer filtros</Button>
        </div>
      </Card>
      <div className="mt-5 grid gap-4">
        <p role="status" className="text-sm text-muted">{items.length} {items.length === 1 ? "evento" : "eventos"}</p>
        {!items.length && <Card title="Sin eventos"><p className="text-sm text-muted">No hay eventos con los filtros seleccionados.</p></Card>}
        {items.map(item => (
          <Card key={item.id} title={item.titulo}>
            <span className="mb-2 inline-block rounded-full border border-line px-2 py-1 text-xs font-semibold text-ink">{{ upcoming: 'Próximo', ongoing: 'En curso', ended: 'Finalizado' }[eventPhase(item, now)]}</span>
            <p className="text-sm text-muted">{EVENT_TYPES[item.tipo].label} · {fmtShort(item.inicio)} {timeOf(item.inicio)} – {fmtShort(item.fin)} {timeOf(item.fin)}</p>
            <details className="mt-3 text-sm">
              <summary className="cursor-pointer font-semibold">Ver detalle</summary>
              <p className="mt-2 whitespace-pre-wrap break-words">{item.descripcion || 'Sin descripción.'}</p>
            </details>
          </Card>
        ))}
        <Button variant="ghost" onClick={() => navigate('calendario')}>Abrir calendario</Button>
      </div>
    </>
  )
}
