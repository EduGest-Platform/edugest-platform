import { useMemo, useState } from 'react'
import { CheckCheck, History } from 'lucide-react'
import { fmtLong, dayOf, timeOf } from '../dates'
import { cohortCoders, cohortOf, nominalCohorts, nowOf } from '../domain'
import { applyAttendance } from '../actions'
import { useGistar } from '../store'
import type { AsistEstado } from '../types'
import { Modal } from './Modal'
import { Button, Notice, inputCls } from '../ui'

const STATES: { id: AsistEstado; label: string; cls: string }[] = [
  { id: 'presente', label: 'Presente', cls: 'bg-teal text-white' },
  { id: 'retraso', label: 'Retraso', cls: 'bg-amber-500 text-white' },
  { id: 'ausente', label: 'Ausente', cls: 'bg-rose-600 text-white' },
  { id: 'pendiente', label: 'Pendiente', cls: 'bg-slate-500 text-white' },
]

export function AttendanceModal({ sessionId, onClose }: { sessionId: string; onClose: () => void }) {
  const { data, role, update } = useGistar()
  const ses = data.eventos.find((e) => e.id === sessionId)!
  const coders = cohortCoders(data, ses.cohorte_id!)
  const held = ses.inicio <= nowOf(data)
  const canEdit = held && ses.estado !== 'cancelado' && role === 'docente' && nominalCohorts(data, role).some((c) => c.id === ses.cohorte_id)
  const initial = useMemo(() => {
    const m: Record<string, { estado: AsistEstado; comentario: string }> = {}
    for (const c of coders) {
      const r = data.asistencia.find((x) => x.evento_id === sessionId && x.coder_id === c.id)
      m[c.id] = { estado: r?.estado ?? 'pendiente', comentario: r?.comentario ?? '' }
    }
    return m
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId])
  const [rows, setRows] = useState(initial)
  const [showHist, setShowHist] = useState<string | null>(null)
  const changed = coders.filter((c) => rows[c.id].estado !== initial[c.id].estado || rows[c.id].comentario !== initial[c.id].comentario)
  const counts = STATES.map((s) => ({ ...s, n: coders.filter((c) => rows[c.id].estado === s.id).length }))

  const save = () => {
    update(
      (d) => applyAttendance(d, sessionId, Object.fromEntries(changed.map((c) => [c.id, rows[c.id]]))),
      'registro_asistencia',
      sessionId,
      `${changed.length} registros actualizados`,
      'Asistencia guardada',
    )
    onClose()
  }

  return (
    <Modal
      open
      onClose={onClose}
      size="lg"
      dirty={changed.length > 0}
      title={`Asistencia · ${ses.titulo}`}
      subtitle={`${fmtLong(dayOf(ses.inicio))} · ${timeOf(ses.inicio)}–${timeOf(ses.fin)} (Europe/Madrid) · ${cohortOf(data, ses.cohorte_id!)?.nombre}`}
      footer={
        <>
          <span className="mr-auto text-xs text-muted">{changed.length ? `${changed.length} cambios sin guardar` : 'Sin cambios'}</span>
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          {canEdit && (
            <Button variant="success" disabled={!changed.length} onClick={save}>
              Guardar asistencia
            </Button>
          )}
        </>
      }
    >
      {!held && <Notice tone="warning">Esta sesión aún no se ha celebrado. Las sesiones futuras no se registran ni cuentan como ausencias.</Notice>}
      {held && !canEdit && <Notice>Solo el docente responsable de la cohorte puede registrar esta asistencia. Vista de consulta.</Notice>}
      <div className="mb-4 flex flex-wrap items-center gap-3 text-sm">
        {counts.map((c) => (
          <span key={c.id} className="inline-flex items-center gap-1.5">
            <span className={`size-2.5 rounded-full ${c.cls.split(' ')[0]}`} />
            {c.label} <b className="tabular-nums">{c.n}</b>
          </span>
        ))}
        {canEdit && (
          <Button
            size="sm"
            variant="ghost"
            className="ml-auto"
            onClick={() => setRows(Object.fromEntries(coders.map((c) => [c.id, { ...rows[c.id], estado: rows[c.id].estado === 'pendiente' ? 'presente' : rows[c.id].estado }])))}
          >
            <CheckCheck className="size-4" aria-hidden /> Pendientes → presente
          </Button>
        )}
      </div>
      <ul className="divide-y divide-line rounded-xl border border-line">
        {coders.map((c) => {
          const rec = data.asistencia.find((x) => x.evento_id === sessionId && x.coder_id === c.id)
          return (
            <li key={c.id} className="grid gap-2 px-4 py-3 md:grid-cols-[minmax(0,1fr)_auto] md:items-center">
              <div className="min-w-0">
                <span className="mr-2 font-mono text-xs text-muted">{c.id}</span>
                <span className="font-medium">{c.nombre_ficticio}</span>
                {rec && rec.historial.length > 1 && (
                  <button type="button" onClick={() => setShowHist(showHist === c.id ? null : c.id)} className="ml-2 inline-flex cursor-pointer items-center gap-1 text-xs text-blue hover:underline">
                    <History className="size-3" aria-hidden /> {rec.historial.length} cambios
                  </button>
                )}
                {showHist === c.id && rec && (
                  <ol className="mt-1.5 grid gap-0.5 text-xs text-muted">
                    {rec.historial.map((h, i) => (
                      <li key={i}>
                        {h.en} · {h.estado} · {h.actor}
                        {h.comentario && ` · «${h.comentario}»`}
                      </li>
                    ))}
                  </ol>
                )}
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <div role="radiogroup" aria-label={`Asistencia de ${c.nombre_ficticio}`} className="inline-flex rounded-lg bg-mist p-0.5">
                  {STATES.map((s) => (
                    <button
                      key={s.id}
                      type="button"
                      role="radio"
                      aria-checked={rows[c.id].estado === s.id}
                      disabled={!canEdit}
                      onClick={() => setRows((p) => ({ ...p, [c.id]: { ...p[c.id], estado: s.id } }))}
                      className={`cursor-pointer rounded-md px-2.5 py-1 text-xs font-semibold disabled:cursor-default ${rows[c.id].estado === s.id ? s.cls : 'text-muted hover:text-ink'}`}
                    >
                      {s.label}
                    </button>
                  ))}
                </div>
                <input
                  aria-label={`Comentario para ${c.nombre_ficticio}`}
                  placeholder="Comentario (opcional, no sensible)"
                  disabled={!canEdit}
                  className={`${inputCls} w-52 py-1.5 text-xs`}
                  value={rows[c.id].comentario}
                  onChange={(e) => {
                    const v = e.target.value
                    setRows((p) => ({ ...p, [c.id]: { ...p[c.id], comentario: v } }))
                  }}
                />
              </div>
            </li>
          )
        })}
      </ul>
      <p className="mt-3 text-xs text-muted">
        Un único registro por coder y sesión; las ediciones se guardan en su historial. No anotes motivos de salud, situación personal ni otros datos sensibles.
      </p>
    </Modal>
  )
}
