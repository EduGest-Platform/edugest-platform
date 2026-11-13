import { useState } from 'react'
import { ArrowLeft, TrendingDown, TrendingUp, Minus } from 'lucide-react'
import { pct } from '../analytics'
import { fmtDay } from '../dates'
import {
  CODER_ID,
  attendanceSummary,
  cohortOf,
  effectiveCompetencies,
  nominalCohorts,
  programOf,
  published,
  revisionsOf,
  todayOf,
  userName,
} from '../domain'
import { useGistar } from '../store'
import type { Evaluacion } from '../types'
import { DotTimeline, LEVEL_STYLE, LevelLegend } from '../components/charts'
import { Button, Card, Empty, Field, Metric, Notice, PageTitle, SyntheticBadge, Table, inputCls } from '../ui'

const ORIGIN = { heredado_v1: 'Heredado v1 (fecha sintética)', sintetico_seed: 'Sintético (seed)', demo: 'Demo' } as const

/** Individual competency evolution. Used by the coder (own data) and by the authorised teacher. */
export function CoderProfile() {
  const { data, role, focusStudent, setFocusStudent, focusComp, navigate } = useGistar()
  const own = role === 'coder'
  const allowed = own ? data.coders.filter((c) => c.id === CODER_ID) : data.coders.filter((c) => nominalCohorts(data, role).some((h) => h.id === c.cohorte_id))
  const coder = allowed.find((c) => c.id === (own ? CODER_ID : focusStudent)) ?? allowed[0]
  const coh = coder && cohortOf(data, coder.cohorte_id)!
  const today = todayOf(data)
  const [comp, setComp] = useState<string>(focusComp ?? 'todas')
  const [from, setFrom] = useState(coh?.inicio ?? today)
  const [to, setTo] = useState(today)
  const [legacy, setLegacy] = useState(true)
  if (!coder || !coh) return <Empty>No tienes acceso a fichas individuales.</Empty>

  const comps = effectiveCompetencies(data, coh.id)
  const shown = comps.filter((c) => comp === 'todas' || c.id === comp)
  const evals = data.evaluaciones
    .filter((e) => e.coder_id === coder.id && published(e) && (legacy || e.origen !== 'heredado_v1'))
    .sort((a, b) => a.fecha.localeCompare(b.fecha) || a.seq - b.seq)
  const inRange = evals.filter((e) => e.fecha >= from && e.fecha <= to)
  const current = (id: string) => [...evals].filter((e) => e.competencia_id === id && e.fecha <= to).pop()
  const withData = comps.filter((c) => current(c.id)).length
  const mastered = comps.filter((c) => (current(c.id)?.nivel ?? 0) >= 2).length
  const att = attendanceSummary(data, coh.id, { coderId: coder.id })
  const markers = data.tareas.filter((t) => t.cohorte_id === coh.id && t.estado === 'activa').map((t) => ({ date: t.fecha_entrega.slice(0, 10), label: `Entrega · ${t.nombre}` }))
  const feedbacks = data.entregas
    .filter((e) => e.coder_id === coder.id)
    .flatMap((e) => revisionsOf(data, e.id).filter((r) => r.estado === 'publicada' && r.feedback).map((r) => ({ r, t: data.tareas.find((t) => t.id === e.tarea_id) })))
    .sort((a, b) => (b.r.publicada_en ?? '').localeCompare(a.r.publicada_en ?? ''))

  return (
    <>
      {!own && (
        <Button variant="subtle" size="sm" className="-ml-2 mb-3" onClick={() => navigate('alumnado')}>
          <ArrowLeft className="size-4" aria-hidden /> Volver a Alumnado
        </Button>
      )}
      <PageTitle eyebrow={`${programOf(data, coh.programa_id)?.nombre} · ${coh.nombre}`} title={own ? 'Mi progreso' : `Ficha · ${coder.nombre_ficticio}`} sub="Evolución por competencia a partir de evaluaciones publicadas y fechadas. Una competencia sin evaluación figura como «sin datos», nunca como nivel 0." />
      <div className="mb-5 flex flex-wrap items-end gap-3">
        {!own && (
          <Field label="Coder" htmlFor="pf-coder">
            <select id="pf-coder" className={`${inputCls} w-auto`} value={coder.id} onChange={(e) => setFocusStudent(e.target.value)}>
              {allowed.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.id} · {c.nombre_ficticio}
                </option>
              ))}
            </select>
          </Field>
        )}
        <Field label="Competencia" htmlFor="pf-comp">
          <select id="pf-comp" className={`${inputCls} w-auto`} value={comp} onChange={(e) => setComp(e.target.value)}>
            <option value="todas">Todas ({comps.length})</option>
            {comps.map((c) => (
              <option key={c.id} value={c.id}>
                {c.codigo} · {c.nombre}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Desde" htmlFor="pf-from">
          <input id="pf-from" type="date" className={`${inputCls} w-auto`} value={from} max={to} onChange={(e) => setFrom(e.target.value)} />
        </Field>
        <Field label="Hasta" htmlFor="pf-to">
          <input id="pf-to" type="date" className={`${inputCls} w-auto`} value={to} min={from} max={today} onChange={(e) => setTo(e.target.value)} />
        </Field>
        <label className="flex items-center gap-2 pb-2.5 text-sm">
          <input type="checkbox" className="size-4 accent-teal" checked={legacy} onChange={(e) => setLegacy(e.target.checked)} /> Incluir punto heredado
        </label>
        <span className="ml-auto pb-2.5">
          <SyntheticBadge />
        </span>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Metric label="Competencias con datos" value={`${withData}/${comps.length}`} formula="Competencias con al menos una evaluación publicada hasta la fecha final" />
        <Metric label="En nivel 2 o 3" value={`${mastered}/${withData || 0}`} formula="Sobre competencias con datos; no se promedian niveles" />
        <Metric label="Asistencia propia" value={pct(att.tasa)} sub={`${att.presente + att.retraso}/${att.registrados} registros confirmados`} formula="Presente o retraso / registros confirmados de sesiones celebradas" />
        <Metric label="Evaluaciones en el periodo" value={inRange.length} formula="Evaluaciones publicadas entre las fechas elegidas" />
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <Card title="Evolución por competencia" action={<LevelLegend />}>
          <p className="-mt-2 mb-4 text-xs text-muted">Cada punto es una evaluación publicada. Los puntos con borde discontinuo son el corte heredado de v1. Las líneas verticales marcan fechas de entrega.</p>
          <ul className="divide-y divide-line">
            {shown.map((c) => {
              const pts = evals.filter((e) => e.competencia_id === c.id && e.fecha >= from && e.fecha <= to)
              const cur = current(c.id)
              const prev = cur && [...evals].filter((e) => e.competencia_id === c.id && e.fecha <= to && e !== cur).pop()
              const delta = cur && prev ? cur.nivel - prev.nivel : null
              return (
                <li key={c.id} className="grid gap-3 py-3 md:grid-cols-[220px_minmax(0,1fr)] md:items-center">
                  <div>
                    <p className="text-sm font-medium">
                      <span className="font-mono text-xs text-muted">{c.codigo}</span> {c.nombre}
                    </p>
                    <p className="mt-1 flex items-center gap-2 text-xs text-muted">
                      {cur ? (
                        <>
                          <span className="rounded px-1.5 py-0.5 font-bold" style={{ background: LEVEL_STYLE[cur.nivel].bg, color: LEVEL_STYLE[cur.nivel].fg }}>
                            N{cur.nivel}
                          </span>
                          {fmtDay(cur.fecha)}
                          {delta !== null && (
                            <span className="inline-flex items-center gap-0.5">
                              {delta > 0 ? <TrendingUp className="size-3.5 text-teal-700" aria-hidden /> : delta < 0 ? <TrendingDown className="size-3.5 text-amber-700" aria-hidden /> : <Minus className="size-3.5" aria-hidden />}
                              {prev && `desde N${prev.nivel}`}
                            </span>
                          )}
                        </>
                      ) : (
                        <span className="italic">Sin datos</span>
                      )}
                    </p>
                  </div>
                  {pts.length ? (
                    <DotTimeline
                      from={from}
                      to={to}
                      markers={markers}
                      ariaLabel={`${c.nombre}: ${pts.map((p) => `N${p.nivel} el ${fmtDay(p.fecha)}`).join(', ')}`}
                      points={pts.map((p) => ({ date: p.fecha, level: p.nivel, legacy: p.origen === 'heredado_v1', label: `N${p.nivel} · ${fmtDay(p.fecha)} · ${ORIGIN[p.origen]}` }))}
                    />
                  ) : (
                    <p className="text-xs text-muted">Sin evaluaciones publicadas en el periodo.</p>
                  )}
                </li>
              )
            })}
          </ul>
        </Card>
        <div className="grid content-start gap-5">
          <Card title="Último feedback publicado">
            {!feedbacks.length ? (
              <p className="text-sm text-muted">Aún no hay feedback publicado.</p>
            ) : (
              <ul className="grid gap-3">
                {feedbacks.slice(0, 4).map(({ r, t }) => (
                  <li key={r.id} className="rounded-xl bg-mist/60 p-3 text-sm">
                    <p className="mb-1 text-xs text-muted">
                      {fmtDay(r.publicada_en!)} · {t?.nombre}
                    </p>
                    {r.feedback}
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <Card title="Hitos">
            <ul className="grid gap-2 text-sm">
              {markers.map((m) => (
                <li key={m.label} className="flex justify-between gap-3">
                  <span>{m.label}</span>
                  <span className={`whitespace-nowrap tabular-nums ${m.date > today ? 'text-blue' : 'text-muted'}`}>{fmtDay(m.date)}</span>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>

      <Card title="Historial de evaluaciones" className="mt-5" action={<span className="text-xs text-muted">{inRange.length} registros en el periodo</span>}>
        <History evals={[...inRange].reverse().filter((e) => comp === 'todas' || e.competencia_id === comp)} />
        {own && <Notice>Solo ves evaluaciones publicadas tras la revisión humana de tu docente.</Notice>}
      </Card>
    </>
  )
}

function History({ evals }: { evals: Evaluacion[] }) {
  const { data } = useGistar()
  if (!evals.length) return <Empty>Sin evaluaciones publicadas con estos filtros.</Empty>
  return (
    <Table head={['Fecha', 'Competencia', 'Nivel', 'Proyecto / rúbrica', 'Evaluador', 'Evidencia y comentario', 'Origen']}>
      {evals.map((e) => {
        const c = data.competencias.find((x) => x.id === e.competencia_id)
        const t = e.tarea_id ? data.tareas.find((x) => x.id === e.tarea_id) : null
        return (
          <tr key={e.id}>
            <td className="whitespace-nowrap tabular-nums text-muted">{fmtDay(e.fecha)}</td>
            <td>
              <span className="font-mono text-xs text-muted">{c?.codigo}</span> {c?.nombre}
              {c && !c.activo && <span className="ml-1 text-[11px] text-muted">(archivada)</span>}
            </td>
            <td className="font-semibold">N{e.nivel}</td>
            <td className="text-xs text-muted">{t ? `${t.nombre} · v${e.rubrica_version}` : '—'}</td>
            <td className="text-xs">{userName(data, e.evaluador)}</td>
            <td className="max-w-72 text-xs text-muted">
              {e.evidencia}
              {e.comentario && ` · ${e.comentario}`}
            </td>
            <td className="text-xs text-muted">{ORIGIN[e.origen]}</td>
          </tr>
        )
      })}
    </Table>
  )
}
