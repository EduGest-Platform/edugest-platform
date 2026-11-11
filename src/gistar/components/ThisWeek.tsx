import { CalendarDays } from 'lucide-react'
import { addDays, dayOf, fmtShort, timeOf } from '../dates'
import { EVENT_TYPES, todayOf, weekRange } from '../domain'
import { useGistar } from '../store'
import { useVisibleItems } from '../views/Calendar'
import { Button, Card } from '../ui'

/** «Esta semana»: role-filtered calendar items (events + task deadlines) for the current demo week. */
export function ThisWeek({ limit = 8 }: { limit?: number }) {
  const { data, navigate } = useGistar()
  const today = todayOf(data)
  const { from, to } = weekRange(today)
  const items = useVisibleItems().filter((i) => i.estado !== 'cancelado' && dayOf(i.inicio) >= from && dayOf(i.inicio) <= to)
  return (
    <Card
      title="Esta semana"
      action={
        <Button size="sm" variant="ghost" onClick={() => navigate('calendario')}>
          <CalendarDays className="size-4" aria-hidden /> Calendario
        </Button>
      }
    >
      <p className="-mt-2 mb-3 text-xs text-muted">
        {fmtShort(from)} – {fmtShort(addDays(from, 6))} · fuente: calendario
      </p>
      {!items.length ? (
        <p className="text-sm text-muted">No tienes eventos esta semana.</p>
      ) : (
        <ul className="grid gap-1.5">
          {items.slice(0, limit).map((i) => (
            <li key={i.id} className={`flex min-w-0 items-center gap-3 rounded-lg px-2 py-1.5 text-sm ${dayOf(i.inicio) < today ? 'opacity-60' : ''}`}>
              <span className={`size-2 shrink-0 rounded-full ${EVENT_TYPES[i.tipo].dot}`} />
              <span className="w-28 shrink-0 text-xs tabular-nums text-muted">
                {fmtShort(i.inicio)} {timeOf(i.inicio)}
              </span>
              <span className="min-w-0 truncate" title={i.titulo}>
                {i.titulo}
              </span>
            </li>
          ))}
          {items.length > limit && <li className="px-2 text-xs text-muted">+{items.length - limit} más</li>}
        </ul>
      )}
    </Card>
  )
}

export function Upcoming({ limit = 5, title = 'Próximos eventos' }: { limit?: number; title?: string }) {
  const { data } = useGistar()
  const now = `${todayOf(data)}T00:00`
  const items = useVisibleItems().filter((i) => i.estado !== 'cancelado' && i.inicio >= now).slice(0, limit)
  return (
    <Card title={title}>
      {!items.length ? (
        <p className="text-sm text-muted">Sin eventos próximos.</p>
      ) : (
        <ul className="grid gap-2">
          {items.map((i) => (
            <li key={i.id} className="flex items-start gap-3 text-sm">
              <span className={`mt-1.5 size-2 shrink-0 rounded-full ${EVENT_TYPES[i.tipo].dot}`} />
              <div className="min-w-0">
                <p className="truncate font-medium">{i.titulo}</p>
                <p className="text-xs text-muted">
                  {fmtShort(i.inicio)} · {timeOf(i.inicio)} · {EVENT_TYPES[i.tipo].label}
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}
