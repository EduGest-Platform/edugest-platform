import { useMemo, useState } from 'react'
import { CalendarPlus, ChevronLeft, ChevronRight, ClipboardCheck, Ban, RotateCcw } from 'lucide-react'
import { ROLES } from '../config'
import { addDays, addMonths, dayOf, fmtLong, fmtMonth, fmtShort, monthStart, timeOf, weekStart } from '../dates'
import {
  EVENT_TYPES,
  calendarItems,
  canEditItem,
  canSeeItem,
  cohortCoders,
  cohortOf,
  coderName,
  nominalCohorts,
  nowOf,
  todayOf,
  uid,
  userName,
} from '../domain'
import { useGistar } from '../store'
import type { CalItem, EventType, GistarData, Role } from '../types'
import { Modal } from '../components/Modal'
import { AttendanceModal } from '../components/AttendanceModal'
import { Button, Chips, Field, Notice, PageTitle, Segmented, inputCls } from '../ui'

type Mode = 'mes' | 'semana' | 'agenda'
const TYPE_IDS = Object.keys(EVENT_TYPES) as EventType[]
const WEEKDAYS = ['lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom']

export function useVisibleItems() {
  const { data, role } = useGistar()
  return useMemo(() => calendarItems(data).filter((i) => canSeeItem(data, role, i)), [data, role])
}

export function Calendar() {
  const { data, role } = useGistar()
  const today = todayOf(data)
  const [mode, setMode] = useState<Mode>('mes')
  const [cursor, setCursor] = useState(today)
  const [types, setTypes] = useState<EventType[]>(TYPE_IDS)
  const [cohort, setCohort] = useState('todas')
  const [open, setOpen] = useState<{ item?: CalItem; createOn?: string } | null>(null)
  const [attendance, setAttendance] = useState<string | null>(null)
  const all = useVisibleItems()
  const items = all.filter((i) => types.includes(i.tipo) && (cohort === 'todas' || i.cohorte_id === cohort || (cohort === 'general' && !i.cohorte_id)))
  const canCreate = role === 'admin' || role === 'docente'
  const cohortOptions = role === 'admin' || role === 'docente' ? nominalCohorts(data, role) : role === 'coder' ? [] : role === 'coordinacion' ? data.cohortes : []

  const step = (n: number) => setCursor(mode === 'mes' ? addMonths(cursor, n) : addDays(cursor, n * (mode === 'semana' ? 7 : 14)))
  const title = mode === 'mes' ? fmtMonth(cursor) : mode === 'semana' ? `Semana del ${fmtShort(weekStart(cursor))}` : `Desde ${fmtShort(cursor)}`

  return (
    <>
      <PageTitle
        title="Calendario"
        sub={`Sesiones, entregas, talleres, tutorías y convocatorias visibles para ${ROLES[role]}. Horario Europe/Madrid. Hoy (demo): ${fmtLong(today)}.`}
      />
      <section className="rounded-2xl border border-line bg-white">
        <div className="flex flex-wrap items-center gap-3 border-b border-line p-4">
          <div className="flex items-center gap-1">
            <Button size="sm" variant="ghost" aria-label="Anterior" onClick={() => step(-1)}>
              <ChevronLeft className="size-4" aria-hidden />
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setCursor(today)}>
              Hoy
            </Button>
            <Button size="sm" variant="ghost" aria-label="Siguiente" onClick={() => step(1)}>
              <ChevronRight className="size-4" aria-hidden />
            </Button>
          </div>
          <h2 className="min-w-40 text-base font-semibold first-letter:uppercase">{title}</h2>
          <div className="ml-auto flex flex-wrap items-center gap-2">
            {cohortOptions.length > 0 && (
              <select aria-label="Filtrar por cohorte" className={`${inputCls} w-auto py-1.5`} value={cohort} onChange={(e) => setCohort(e.target.value)}>
                <option value="todas">Todas las cohortes</option>
                <option value="general">Eventos generales</option>
                {cohortOptions.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.nombre}
                  </option>
                ))}
              </select>
            )}
            <Segmented label="Vista" value={mode} onChange={setMode} options={[{ id: 'mes', label: 'Mes' }, { id: 'semana', label: 'Semana' }, { id: 'agenda', label: 'Agenda' }]} />
            {canCreate && (
              <Button size="sm" onClick={() => setOpen({ createOn: cursor })}>
                <CalendarPlus className="size-4" aria-hidden /> Nuevo evento
              </Button>
            )}
          </div>
          <div className="w-full">
            <Chips label="Tipos de evento" value={types} onChange={setTypes} options={TYPE_IDS.map((t) => ({ id: t, label: EVENT_TYPES[t].label }))} />
          </div>
        </div>
        {mode === 'mes' && <MonthGrid cursor={cursor} today={today} items={items} onOpen={(item) => setOpen({ item })} onCreate={canCreate ? (d) => setOpen({ createOn: d }) : undefined} />}
        {mode === 'semana' && <WeekView cursor={cursor} today={today} items={items} onOpen={(item) => setOpen({ item })} />}
        {mode === 'agenda' && <Agenda from={cursor} items={items} onOpen={(item) => setOpen({ item })} />}
      </section>
      {open && (
        <EventModal
          key={open.item?.id ?? 'new'}
          item={open.item}
          createOn={open.createOn}
          onClose={() => setOpen(null)}
          onAttendance={(id) => {
            setOpen(null)
            setAttendance(id)
          }}
        />
      )}
      {attendance && <AttendanceModal sessionId={attendance} onClose={() => setAttendance(null)} />}
    </>
  )
}

function Chip({ it, onOpen, compact }: { it: CalItem; onOpen: (i: CalItem) => void; compact?: boolean }) {
  const t = EVENT_TYPES[it.tipo]
  return (
    <button
      type="button"
      onClick={() => onOpen(it)}
      className={`flex w-full cursor-pointer items-center gap-1.5 truncate rounded-md border px-1.5 py-0.5 text-left text-[11.5px] font-medium ${t.chip} ${it.estado === 'cancelado' ? 'line-through opacity-60' : ''}`}
      title={`${t.label} · ${it.titulo}`}
    >
      <span className={`size-1.5 shrink-0 rounded-full ${t.dot}`} />
      {!compact && <span className="tabular-nums opacity-70">{timeOf(it.inicio)}</span>}
      <span className="truncate">{it.titulo}</span>
    </button>
  )
}

function MonthGrid({ cursor, today, items, onOpen, onCreate }: { cursor: string; today: string; items: CalItem[]; onOpen: (i: CalItem) => void; onCreate?: (d: string) => void }) {
  const start = weekStart(monthStart(cursor))
  const month = cursor.slice(0, 7)
  const days = Array.from({ length: 42 }, (_, i) => addDays(start, i))
  const weeks = days[35].slice(0, 7) === month ? 6 : 5
  return (
    <div className="overflow-x-auto">
      <div className="grid min-w-[720px] grid-cols-7 text-xs">
        {WEEKDAYS.map((w) => (
          <div key={w} className="border-b border-line px-2 py-2 font-semibold uppercase tracking-wide text-muted">
            {w}
          </div>
        ))}
        {days.slice(0, weeks * 7).map((d) => {
          const list = items.filter((i) => dayOf(i.inicio) === d)
          const inMonth = d.slice(0, 7) === month
          return (
            <div key={d} className={`group min-h-28 border-b border-r border-line p-1.5 ${inMonth ? '' : 'bg-[#fafcfd] text-slate-400'}`}>
              <div className="mb-1 flex items-center justify-between">
                <span className={`inline-flex size-6 items-center justify-center rounded-full text-xs font-semibold ${d === today ? 'bg-navy text-white' : ''}`}>{Number(d.slice(8))}</span>
                {onCreate && (
                  <button type="button" aria-label={`Crear evento el ${fmtShort(d)}`} onClick={() => onCreate(d)} className="cursor-pointer rounded px-1 text-muted opacity-0 hover:bg-mist group-hover:opacity-100 focus:opacity-100">
                    +
                  </button>
                )}
              </div>
              <div className="grid gap-0.5">
                {list.slice(0, 3).map((it) => (
                  <Chip key={it.id} it={it} onOpen={onOpen} compact />
                ))}
                {list.length > 3 && <span className="px-1 text-[11px] text-muted">+{list.length - 3} más</span>}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function WeekView({ cursor, today, items, onOpen }: { cursor: string; today: string; items: CalItem[]; onOpen: (i: CalItem) => void }) {
  const start = weekStart(cursor)
  return (
    <div className="grid gap-px bg-line md:grid-cols-7">
      {Array.from({ length: 7 }, (_, i) => addDays(start, i)).map((d) => {
        const list = items.filter((x) => dayOf(x.inicio) === d)
        return (
          <div key={d} className="min-h-40 bg-white p-2">
            <p className={`mb-2 text-xs font-semibold ${d === today ? 'text-blue' : 'text-muted'}`}>{fmtShort(d)}</p>
            <div className="grid gap-1">
              {list.map((it) => (
                <Chip key={it.id} it={it} onOpen={onOpen} />
              ))}
              {!list.length && <span className="text-[11px] text-slate-300">—</span>}
            </div>
          </div>
        )
      })}
    </div>
  )
}

function Agenda({ from, items, onOpen }: { from: string; items: CalItem[]; onOpen: (i: CalItem) => void }) {
  const to = addDays(from, 30)
  const list = items.filter((i) => dayOf(i.inicio) >= from && dayOf(i.inicio) <= to)
  const days = [...new Set(list.map((i) => dayOf(i.inicio)))]
  if (!days.length) return <p className="p-6 text-sm text-muted">No hay eventos en los próximos 30 días con los filtros actuales.</p>
  return (
    <ol className="divide-y divide-line">
      {days.map((d) => (
        <li key={d} className="grid gap-2 px-4 py-3 sm:grid-cols-[160px_minmax(0,1fr)]">
          <p className="text-sm font-semibold">{fmtShort(d)}</p>
          <div className="grid gap-1.5">
            {list
              .filter((i) => dayOf(i.inicio) === d)
              .map((it) => (
                <button key={it.id} type="button" onClick={() => onOpen(it)} className={`flex cursor-pointer items-center gap-3 rounded-lg px-2 py-1.5 text-left text-sm hover:bg-mist ${it.estado === 'cancelado' ? 'line-through opacity-60' : ''}`}>
                  <span className={`size-2 shrink-0 rounded-full ${EVENT_TYPES[it.tipo].dot}`} />
                  <span className="w-24 shrink-0 tabular-nums text-muted">
                    {timeOf(it.inicio)}
                    {it.fin !== it.inicio && `–${timeOf(it.fin)}`}
                  </span>
                  <span className="font-medium">{it.titulo}</span>
                  <span className="ml-auto hidden text-xs text-muted sm:inline">{EVENT_TYPES[it.tipo].label}</span>
                </button>
              ))}
          </div>
        </li>
      ))}
    </ol>
  )
}

const ROLE_IDS = Object.keys(ROLES) as Role[]
const defaultVis = (tipo: EventType): Role[] =>
  tipo === 'jornada' ? ['admin', 'docente', 'aspirante', 'fundacion', 'seleccion', 'coordinacion'] : tipo === 'tutoria' ? ['admin', 'docente', 'coder'] : tipo === 'hito' ? [...ROLE_IDS] : ['admin', 'docente', 'coder', 'coordinacion']

function EventModal({ item, createOn, onClose, onAttendance }: { item?: CalItem; createOn?: string; onClose: () => void; onAttendance: (id: string) => void }) {
  const { data, role, update, toast } = useGistar()
  const editable = item ? canEditItem(data, role, item) : true
  const [editing, setEditing] = useState(!item)
  const cohorts = nominalCohorts(data, role)
  const init = {
    titulo: item ? (item.tarea_id ? data.tareas.find((t) => t.id === item.tarea_id)!.nombre : item.titulo) : '',
    tipo: (item?.tipo ?? 'sesion') as EventType,
    fecha: item ? dayOf(item.inicio) : createOn ?? todayOf(data),
    hi: item ? timeOf(item.inicio) : '09:30',
    hf: item ? timeOf(item.fin) : '13:30',
    cohorte: item ? item.cohorte_id ?? '' : cohorts[0]?.id ?? '',
    responsable: item?.responsable ?? 'USR-DOC',
    visibilidad: item?.visibilidad ?? defaultVis('sesion'),
    descripcion: item?.descripcion ?? '',
    participante: item?.evento?.participante_id ?? '',
  }
  const [f, setF] = useState(init)
  const dirty = editing && JSON.stringify(f) !== JSON.stringify(init)
  const isTask = f.tipo === 'entrega'
  const t = EVENT_TYPES[item?.tipo ?? f.tipo]
  const held = item?.tipo === 'sesion' && item.inicio <= nowOf(data)
  const canRegister = item?.tipo === 'sesion' && role === 'docente' && cohorts.some((c) => c.id === item.cohorte_id)

  const save = () => {
    if (!f.titulo.trim()) return toast('El título es obligatorio')
    if (f.hf < f.hi && !isTask) return toast('La hora de fin debe ser posterior al inicio')
    if ((isTask || f.tipo === 'sesion') && !f.cohorte) return toast('Selecciona una cohorte')
    const inicio = `${f.fecha}T${f.hi}`
    const fin = isTask ? inicio : `${f.fecha}T${f.hf}`
    update(
      (d: GistarData) => {
        if (isTask) {
          if (item?.tarea_id) {
            const task = d.tareas.find((x) => x.id === item.tarea_id)!
            task.nombre = f.titulo
            task.fecha_entrega = inicio
            task.descripcion = f.descripcion
          } else {
            const coh = cohortOf(d, f.cohorte)!
            const id = uid('T')
            d.tareas.push({ id, programa_id: coh.programa_id, cohorte_id: coh.id, nombre: f.titulo, descripcion: f.descripcion, fecha_entrega: inicio, rubrica_id: null, estado: 'activa' })
            for (const c of cohortCoders(d, coh.id))
              d.entregas.push({ id: uid('ENT'), coder_id: c.id, tarea_id: id, estado: 'pendiente', enviada_en: null, repositorio_ficticio: `https://example.test/repos/${c.id.toLowerCase()}-${id.toLowerCase()}`, feedback_borrador: null, feedback_publicado: null })
          }
          return
        }
        const payload = {
          titulo: f.titulo,
          tipo: f.tipo as Exclude<EventType, 'entrega'>,
          inicio,
          fin,
          cohorte_id: f.cohorte || null,
          responsable: f.responsable,
          visibilidad: f.visibilidad,
          descripcion: f.descripcion,
          participante_id: f.tipo === 'tutoria' && f.participante ? f.participante : null,
        }
        const ev = item?.evento && d.eventos.find((x) => x.id === item.evento!.id)
        if (ev) Object.assign(ev, payload)
        else d.eventos.push({ id: uid('EVT'), zona: 'Europe/Madrid', estado: 'programado', origen: 'demo', ...payload })
      },
      item ? 'editar_evento' : 'crear_evento',
      item?.id ?? f.titulo,
      `${f.tipo} · ${inicio}`,
      isTask && !item ? 'Entrega creada: asigna su rúbrica en Rúbricas' : 'Evento guardado',
    )
    onClose()
  }
  const setCancelled = (cancel: boolean) => {
    if (cancel && !confirm('¿Cancelar este evento? Se conservará como cancelado.')) return
    update(
      (d) => {
        if (item!.tarea_id) d.tareas.find((x) => x.id === item!.tarea_id)!.estado = cancel ? 'cancelada' : 'activa'
        else d.eventos.find((x) => x.id === item!.evento!.id)!.estado = cancel ? 'cancelado' : 'programado'
      },
      cancel ? 'cancelar_evento' : 'reactivar_evento',
      item!.id,
    )
    onClose()
  }

  const coders = f.cohorte ? cohortCoders(data, f.cohorte) : []
  return (
    <Modal
      open
      onClose={onClose}
      size="lg"
      dirty={dirty}
      title={item ? (editing ? 'Editar evento' : item.titulo) : 'Nuevo evento'}
      subtitle={item && !editing ? `${t.label} · ${fmtLong(dayOf(item.inicio))}` : 'Horario Europe/Madrid'}
      footer={
        editing ? (
          <>
            <Button variant="ghost" onClick={() => (item ? setEditing(false) : onClose())}>
              Cancelar
            </Button>
            <Button onClick={save}>{item ? 'Guardar cambios' : 'Crear evento'}</Button>
          </>
        ) : (
          <>
            {editable && item && (
              <Button variant="subtle" className="mr-auto" onClick={() => setCancelled(item.estado !== 'cancelado')}>
                {item.estado === 'cancelado' ? <RotateCcw className="size-4" aria-hidden /> : <Ban className="size-4" aria-hidden />}
                {item.estado === 'cancelado' ? 'Reactivar' : 'Cancelar evento'}
              </Button>
            )}
            {canRegister && held && item?.estado !== 'cancelado' && (
              <Button variant="success" onClick={() => onAttendance(item!.id)}>
                <ClipboardCheck className="size-4" aria-hidden /> Registrar asistencia
              </Button>
            )}
            {editable && <Button variant="ghost" onClick={() => setEditing(true)}>Editar</Button>}
            <Button onClick={onClose}>Cerrar</Button>
          </>
        )
      }
    >
      {!editing && item ? (
        <dl className="grid gap-3 text-sm sm:grid-cols-[160px_minmax(0,1fr)]">
          <dt className="text-muted">Estado</dt>
          <dd className="font-medium">{item.estado}</dd>
          <dt className="text-muted">Horario</dt>
          <dd>
            {timeOf(item.inicio)}
            {item.fin !== item.inicio && `–${timeOf(item.fin)}`} · Europe/Madrid
          </dd>
          <dt className="text-muted">Cohorte</dt>
          <dd>{item.cohorte_id ? cohortOf(data, item.cohorte_id)?.nombre : 'General'}</dd>
          <dt className="text-muted">Responsable</dt>
          <dd>{userName(data, item.responsable)}</dd>
          {item.evento?.participante_id && role !== 'coordinacion' && (
            <>
              <dt className="text-muted">Participante</dt>
              <dd>{coderName(data, item.evento.participante_id)}</dd>
            </>
          )}
          {(role === 'admin' || role === 'docente') && (
            <>
              <dt className="text-muted">Visible para</dt>
              <dd>{item.visibilidad.map((r) => ROLES[r]).join(', ')}</dd>
            </>
          )}
          {item.descripcion && (
            <>
              <dt className="text-muted">Descripción</dt>
              <dd>{item.descripcion}</dd>
            </>
          )}
          {item.tarea_id && (
            <>
              <dt className="text-muted">Fuente</dt>
              <dd>Fecha límite de la tarea {item.tarea_id}: es la misma que usa el módulo de entregas.</dd>
            </>
          )}
          {item.tipo === 'sesion' && !held && (
            <dd className="sm:col-span-2">
              <Notice>Sesión futura: no admite registro de asistencia y no cuenta en las métricas.</Notice>
            </dd>
          )}
        </dl>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={isTask ? 'Nombre de la tarea' : 'Título'} htmlFor="ev-title">
            <input id="ev-title" data-autofocus className={inputCls} value={f.titulo} onChange={(e) => setF({ ...f, titulo: e.target.value })} />
          </Field>
          <Field label="Tipo" htmlFor="ev-type">
            <select
              id="ev-type"
              className={inputCls}
              value={f.tipo}
              disabled={!!item}
              onChange={(e) => {
                const tipo = e.target.value as EventType
                setF({ ...f, tipo, visibilidad: defaultVis(tipo) })
              }}
            >
              {TYPE_IDS.map((x) => (
                <option key={x} value={x}>
                  {EVENT_TYPES[x].label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Fecha" htmlFor="ev-date">
            <input id="ev-date" type="date" className={inputCls} value={f.fecha} onChange={(e) => setF({ ...f, fecha: e.target.value })} />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label={isTask ? 'Hora límite' : 'Inicio'} htmlFor="ev-hi">
              <input id="ev-hi" type="time" className={inputCls} value={f.hi} onChange={(e) => setF({ ...f, hi: e.target.value })} />
            </Field>
            {!isTask && (
              <Field label="Fin" htmlFor="ev-hf">
                <input id="ev-hf" type="time" className={inputCls} value={f.hf} onChange={(e) => setF({ ...f, hf: e.target.value })} />
              </Field>
            )}
          </div>
          <Field label="Cohorte" htmlFor="ev-coh">
            <select id="ev-coh" className={inputCls} value={f.cohorte} disabled={!!item?.tarea_id} onChange={(e) => setF({ ...f, cohorte: e.target.value })}>
              {!isTask && f.tipo !== 'sesion' && <option value="">General (sin cohorte)</option>}
              {(role === 'admin' ? data.cohortes : cohorts).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nombre}
                </option>
              ))}
            </select>
          </Field>
          {!isTask && (
            <Field label="Responsable" htmlFor="ev-resp">
              <select id="ev-resp" className={inputCls} value={f.responsable} onChange={(e) => setF({ ...f, responsable: e.target.value })}>
                {data.usuarios_demo
                  .filter((u) => ['admin', 'docente', 'fundacion', 'seleccion', 'coordinacion'].includes(u.rol))
                  .map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.nombre}
                    </option>
                  ))}
              </select>
            </Field>
          )}
          {f.tipo === 'tutoria' && (
            <Field label="Participante (opcional)" htmlFor="ev-part">
              <select id="ev-part" className={inputCls} value={f.participante} onChange={(e) => setF({ ...f, participante: e.target.value })}>
                <option value="">Grupal</option>
                {coders.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.nombre_ficticio}
                  </option>
                ))}
              </select>
            </Field>
          )}
          {!isTask && (
            <div className="sm:col-span-2">
              <Field label="Visibilidad por rol">
                <Chips label="Visibilidad" value={f.visibilidad} onChange={(v) => setF({ ...f, visibilidad: v })} options={ROLE_IDS.map((r) => ({ id: r, label: ROLES[r] }))} />
              </Field>
            </div>
          )}
          <div className="sm:col-span-2">
            <Field label="Descripción" htmlFor="ev-desc">
              <textarea id="ev-desc" className={`${inputCls} min-h-20`} value={f.descripcion} onChange={(e) => setF({ ...f, descripcion: e.target.value })} />
            </Field>
          </div>
          {isTask && (
            <div className="sm:col-span-2">
              <Notice>La fecha límite se guarda en la tarea: el calendario y el módulo de entregas usan la misma fuente. {!item && 'Se crearán entregas pendientes para cada coder activo de la cohorte.'}</Notice>
            </div>
          )}
          {f.tipo === 'sesion' && `${f.fecha}T${f.hi}` <= nowOf(data) && (
            <div className="sm:col-span-2">
              <Notice>Esta sesión ya se ha celebrado según la fecha de la demo: podrás registrar su asistencia desde el calendario o Asistencia.</Notice>
            </div>
          )}
        </div>
      )}
    </Modal>
  )
}
