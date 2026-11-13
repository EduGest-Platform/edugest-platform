import { useMemo, useState } from 'react'
import { ArrowRight, BarChart3, BellRing, CalendarDays, CircleUser, ClipboardCheck, GraduationCap, RotateCcw, Users } from 'lucide-react'
import { MENUS, ROLES, VIEWS } from '../config'
import { groupAnalytics, pct } from '../analytics'
import { fmtDay } from '../dates'
import {
  CODER_ID,
  DELIVERY_LABEL,
  attendanceSummary,
  cohortOf,
  coderName,
  deliveryStatus,
  effectiveCompetencies,
  latestEval,
  nominalCohorts,
  nowOf,
  reviewStatus,
  revisionsOf,
  todayOf,
} from '../domain'
import { metrics } from '../metrics'
import { useGistar } from '../store'
import { LevelCell, LevelLegend, LineChart } from '../components/charts'
import { ReviewModal } from '../components/ReviewModal'
import { ThisWeek, Upcoming } from '../components/ThisWeek'
import { Button, Card, Field, Kpi, Metric, Notice, PageTitle, Status, SyntheticBadge, inputCls } from '../ui'

export function Dashboard() {
  const { role } = useGistar()
  if (role === 'docente') return <TeacherDashboard />
  if (role === 'coder') return <CoderDashboard />
  return <GeneralDashboard />
}

function GeneralDashboard() {
  const { data, role, navigate, reset } = useGistar()
  const m = metrics(data)
  const personal = role === 'aspirante'
  const iconCls = 'size-4 text-slate-400'
  const shortcuts = MENUS[role].filter((v) => v !== 'dashboard').slice(0, 4)
  return (
    <>
      <PageTitle eyebrow={ROLES[role]} title="Bienvenida a Gistar" sub="Información y acciones de tu entorno de demostración." />
      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        {personal ? (
          <>
            <Kpi label="Mi perfil" value="Activo" icon={<CircleUser className={iconCls} />} />
            <Kpi label="Próximos hitos" value="Nov 2026" icon={<CalendarDays className={iconCls} />} />
          </>
        ) : (
          <>
            <Kpi label="Personas en formación" value={m.coders} icon={<Users className={iconCls} />} />
            <Kpi label="Candidaturas" value={m.candidaturas} icon={<GraduationCap className={iconCls} />} />
            <Kpi label="Asistencia registrada" value={m.asistencia == null ? '—' : `${m.asistencia}%`} icon={<ClipboardCheck className={iconCls} />} />
            <Kpi label="Alertas pendientes" value={m.alertas} icon={<BellRing className={iconCls} />} />
          </>
        )}
      </div>
      <div className="grid gap-5 lg:grid-cols-3">
        <Card title="Empieza por aquí">
          <p className="mb-4 text-sm text-muted">Cambia de rol en la barra superior para descubrir otras vistas.</p>
          <div className="grid gap-2">
            {shortcuts.map((v) => {
              const { label, icon: Icon } = VIEWS[v]
              return (
                <button
                  key={v}
                  type="button"
                  onClick={() => navigate(v)}
                  className="group flex cursor-pointer items-center gap-3 rounded-xl border border-line px-4 py-3 text-left text-sm font-semibold text-navy transition-colors hover:border-blue/30 hover:bg-mist"
                >
                  <Icon className="size-4 text-blue" aria-hidden />
                  Abrir {label}
                  <ArrowRight className="ml-auto size-4 text-slate-300 transition-transform group-hover:translate-x-0.5 group-hover:text-blue" aria-hidden />
                </button>
              )
            })}
          </div>
        </Card>
        <ThisWeek />
        <Card title="Qué hace Gistar">
          <p className="text-sm leading-relaxed text-ink/85">Centraliza admisión, seguimiento competencial, entregas y tutorías, siempre con revisión humana en las decisiones.</p>
          <Notice tone="warning">
            Todas las personas, respuestas de IA e indicadores mostrados son <b>simulados</b>.
          </Notice>
          <Button variant="ghost" onClick={reset}>
            <RotateCcw className="size-4" aria-hidden /> Restablecer demo
          </Button>
        </Card>
      </div>
    </>
  )
}

function TeacherDashboard() {
  const { data, role, navigate, teacherCohort, setTeacherCohort } = useGistar()
  const cohorts = nominalCohorts(data, role)
  const cohortId = cohorts.some((c) => c.id === teacherCohort) ? teacherCohort : cohorts[0].id
  const coh = cohortOf(data, cohortId)!
  const today = todayOf(data)
  const g = useMemo(() => groupAnalytics(data, { cohortId, from: coh.inicio, to: today, compIds: null, tareaId: null }), [data, cohortId, coh.inicio, today])
  const [review, setReview] = useState<string | null>(null)
  const pending = data.entregas
    .filter((e) => g.coders.some((c) => c.id === e.coder_id) && ['sin_revisar', 'borrador'].includes(reviewStatus(data, e)))
    .filter((e) => data.tareas.find((t) => t.id === e.tarea_id)?.estado === 'activa')

  return (
    <>
      <PageTitle eyebrow="Docente" title="Panel docente" sub="Resumen conectado a calendario, entregas, asistencia y evaluaciones publicadas." />
      <div className="-mt-2 mb-6 flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-wrap items-end gap-3">
          <Field label="Cohorte" htmlFor="td-coh">
            <select id="td-coh" className={`${inputCls} w-auto`} value={cohortId} onChange={(e) => setTeacherCohort(e.target.value)}>
              {cohorts.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nombre}
                </option>
              ))}
            </select>
          </Field>
          <Button onClick={() => navigate('analitica')}>
            <BarChart3 className="size-4" aria-hidden /> Analítica del grupo
          </Button>
        </div>
        <SyntheticBadge />
      </div>
      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Metric label="Coders activos" value={g.coders.length} sub={`${g.comps.length} competencias`} />
        <Metric label="Nivel 2 o 3" value={pct(g.current.mastery)} sub={`${g.current.mastered}/${g.current.evaluated} pares evaluados`} />
        <Metric label="Cobertura" value={pct(g.current.coverage)} sub={`${g.current.evaluated}/${g.current.pairs}`} />
        <Metric label="Asistencia" value={pct(g.att.tasa)} sub={`${g.att.presente + g.att.retraso}/${g.att.registrados} registros`} />
        <Metric label="Correcciones pendientes" value={pending.length} sub={`${g.alerts.length} ${g.alerts.length === 1 ? 'alerta revisable' : 'alertas revisables'}`} />
      </div>
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <Card title="Progreso de la cohorte" action={<span className="text-xs text-muted">Cortes semanales</span>}>
          <LineChart
            height={190}
            ariaLabel="Evolución semanal del porcentaje en nivel 2–3 y cobertura"
            labels={g.evo.map((p) => p.cut)}
            notes={g.evo.map((p) => `${p.mastered}/${p.evaluated}`)}
            series={[
              { key: 'm', label: '% evaluados en nivel 2–3', color: '#0f6e67', values: g.evo.map((p) => p.mastery) },
              { key: 'c', label: 'Cobertura', color: '#246a92', dashed: true, values: g.evo.map((p) => p.coverage) },
            ]}
          />
          <Button variant="ghost" size="sm" className="mt-3" onClick={() => navigate('analitica')}>
            Ver heatmap, distribución y asistencia <ArrowRight className="size-3.5" aria-hidden />
          </Button>
        </Card>
        <ThisWeek />
        <Card title="Correcciones pendientes" action={<Button size="sm" variant="ghost" onClick={() => navigate('entregas')}>Todas</Button>}>
          {!pending.length ? (
            <p className="text-sm text-muted">No hay correcciones pendientes.</p>
          ) : (
            <ul className="grid gap-1.5">
              {pending.slice(0, 6).map((e) => {
                const t = data.tareas.find((x) => x.id === e.tarea_id)!
                return (
                  <li key={e.id} className="flex items-center justify-between gap-3 rounded-lg px-2 py-1.5 text-sm hover:bg-mist/60">
                    <span className="min-w-0 truncate">
                      <b className="font-medium">{coderName(data, e.coder_id)}</b> <span className="text-muted">· {t.nombre}</span>
                    </span>
                    <Button size="sm" variant="ghost" onClick={() => setReview(e.id)}>
                      {reviewStatus(data, e) === 'borrador' ? 'Continuar' : 'Revisar'}
                    </Button>
                  </li>
                )
              })}
              {pending.length > 6 && <li className="px-2 text-xs text-muted">+{pending.length - 6} más</li>}
            </ul>
          )}
        </Card>
        <div className="grid content-start gap-5">
          <Card title="Alertas revisables" action={<Button size="sm" variant="ghost" onClick={() => navigate('alertas')}>Abrir</Button>}>
            {!g.alerts.length ? (
              <p className="text-sm text-muted">Sin alertas por revisar en esta cohorte.</p>
            ) : (
              <ul className="grid gap-2 text-sm">
                {g.alerts.map((a) => (
                  <li key={a.id} className="flex items-start justify-between gap-2">
                    <span>
                      <b className="font-medium">{coderName(data, a.coder_id)}</b>
                      <span className="block text-xs text-muted">{a.senales.join(' · ')}</span>
                    </span>
                    <Status s={a.estado} />
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <Upcoming />
        </div>
      </div>
      {review && <ReviewModal entregaId={review} onClose={() => setReview(null)} />}
    </>
  )
}

function CoderDashboard() {
  const { data, navigate } = useGistar()
  const coder = data.coders.find((c) => c.id === CODER_ID)!
  const coh = cohortOf(data, coder.cohorte_id)!
  const today = todayOf(data)
  const now = nowOf(data)
  const comps = effectiveCompetencies(data, coh.id)
  const levels = comps.map((c) => ({ c, e: latestEval(data.evaluaciones, coder.id, c.id, today) }))
  const withData = levels.filter((x) => x.e).length
  const att = attendanceSummary(data, coh.id, { coderId: coder.id })
  const own = data.entregas.filter((e) => e.coder_id === coder.id).map((e) => ({ e, t: data.tareas.find((t) => t.id === e.tarea_id)! })).filter((x) => x.t?.estado === 'activa')
  const nextDue = own.filter((x) => x.t.fecha_entrega > now).sort((a, b) => a.t.fecha_entrega.localeCompare(b.t.fecha_entrega))
  const lastFb = own
    .flatMap(({ e, t }) => revisionsOf(data, e.id).filter((r) => r.estado === 'publicada' && r.feedback).map((r) => ({ r, t })))
    .sort((a, b) => (b.r.publicada_en ?? '').localeCompare(a.r.publicada_en ?? ''))[0]

  return (
    <>
      <PageTitle eyebrow={`Coder · ${coh.nombre}`} title={`Hola, ${coder.nombre_ficticio}`} sub="Tu progreso, tus próximas entregas y tu agenda. Solo ves datos propios y evaluaciones publicadas." />
      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Metric label="Competencias con datos" value={`${withData}/${comps.length}`} />
        <Metric label="En nivel 2 o 3" value={`${levels.filter((x) => (x.e?.nivel ?? 0) >= 2).length}/${withData}`} />
        <Metric label="Mi asistencia" value={pct(att.tasa)} sub={`${att.presente + att.retraso}/${att.registrados} registros`} />
        <Metric label="Próxima entrega" value={nextDue[0] ? fmtDay(nextDue[0].t.fecha_entrega) : '—'} sub={nextDue[0]?.t.nombre} />
      </div>
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <Card title="Mis competencias" action={<Button size="sm" variant="ghost" onClick={() => navigate('progreso')}>Ver evolución</Button>}>
          <div className="mb-3">
            <LevelLegend />
          </div>
          <ul className="grid gap-2 sm:grid-cols-2">
            {levels.map(({ c, e }) => (
              <li key={c.id} className="flex items-center justify-between gap-3 rounded-lg bg-mist/50 px-3 py-2 text-sm">
                <span className="truncate">
                  <span className="font-mono text-xs text-muted">{c.codigo}</span> {c.nombre}
                </span>
                <span className="w-12 shrink-0">
                  <LevelCell level={e?.nivel ?? null} title={e ? `Nivel ${e.nivel} · ${fmtDay(e.fecha)}` : 'Sin datos'} />
                </span>
              </li>
            ))}
          </ul>
        </Card>
        <ThisWeek />
        <Card title="Entregas" action={<Button size="sm" variant="ghost" onClick={() => navigate('entregas')}>Mis entregas</Button>}>
          <ul className="grid gap-2 text-sm">
            {own
              .sort((a, b) => b.t.fecha_entrega.localeCompare(a.t.fecha_entrega))
              .map(({ e, t }) => (
                <li key={e.id} className="flex items-center justify-between gap-3">
                  <span className="min-w-0 truncate">
                    {t.nombre} <span className="text-xs text-muted">· {fmtDay(t.fecha_entrega)}</span>
                  </span>
                  <span className="shrink-0 text-xs text-muted">{DELIVERY_LABEL[deliveryStatus(e, t, now)]}</span>
                </li>
              ))}
          </ul>
        </Card>
        <div className="grid content-start gap-5">
          <Card title="Último feedback">
            {lastFb ? (
              <>
                <p className="mb-1 text-xs text-muted">
                  {fmtDay(lastFb.r.publicada_en!)} · {lastFb.t.nombre}
                </p>
                <p className="text-sm">{lastFb.r.feedback}</p>
              </>
            ) : (
              <p className="text-sm text-muted">Aún no hay feedback publicado.</p>
            )}
          </Card>
          <Upcoming />
        </div>
      </div>
    </>
  )
}
