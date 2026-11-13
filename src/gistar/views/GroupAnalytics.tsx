import { useMemo, useState } from 'react'
import { ShieldAlert } from 'lucide-react'
import { evolution, groupAnalytics, pct, ratio, weeklyCuts } from '../analytics'
import { fmtDay, fmtShort, timeOf } from '../dates'
import { MIN_GROUP, activeTasks, cohortOf, effectiveCompetencies, nominalCohorts, programOf, todayOf } from '../domain'
import { useGistar } from '../store'
import { AttendanceModal } from '../components/AttendanceModal'
import { ColumnChart, LEVEL_STYLE, LevelCell, LevelLegend, LineChart, SegmentLegend, StackedBar, type Segment } from '../components/charts'
import { Button, Card, Chips, Empty, Field, Formula, Metric, Notice, PageTitle, SyntheticBadge, inputCls } from '../ui'

const distSegments = (d: { n1: number; n2: number; n3: number; none: number }): Segment[] => [
  { key: 'n1', value: d.n1, color: LEVEL_STYLE[1].bg, label: 'Nivel 1' },
  { key: 'n2', value: d.n2, color: LEVEL_STYLE[2].bg, label: 'Nivel 2' },
  { key: 'n3', value: d.n3, color: LEVEL_STYLE[3].bg, label: 'Nivel 3' },
  { key: 'none', value: d.none, color: '', label: 'Sin evaluar', pattern: true },
]

export function GroupAnalytics() {
  const { data, role, teacherCohort, setTeacherCohort, setFocusStudent, setFocusComp, navigate } = useGistar()
  const cohorts = nominalCohorts(data, role)
  const today = todayOf(data)
  const cohortId = cohorts.some((c) => c.id === teacherCohort) ? teacherCohort : cohorts[0]?.id
  const coh = cohortOf(data, cohortId)!
  const programs = [...new Set(cohorts.map((c) => c.programa_id))]
  const [from, setFrom] = useState(coh.inicio)
  const [to, setTo] = useState(today)
  const [compIds, setCompIds] = useState<string[]>([])
  const [tareaId, setTareaId] = useState('')
  const [explore, setExplore] = useState<string | null>(null)
  const [week, setWeek] = useState<string | null>(null)
  const [session, setSession] = useState<string | null>(null)

  const changeCohort = (id: string) => {
    setTeacherCohort(id)
    setFrom(cohortOf(data, id)!.inicio)
    setCompIds([])
    setTareaId('')
    setExplore(null)
    setWeek(null)
  }
  const g = useMemo(
    () => groupAnalytics(data, { cohortId, from, to, compIds: compIds.length ? compIds : null, tareaId: tareaId || null }),
    [data, cohortId, from, to, compIds, tareaId],
  )
  const exploreComp = g.comps.find((c) => c.id === explore) ?? null
  const exploreEvo = useMemo(
    () => (exploreComp ? evolution(data, g.coders, [exploreComp], weeklyCuts(g.from, g.to), tareaId || null) : []),
    [data, exploreComp, g.coders, g.from, g.to, tareaId],
  )
  const lastUpdate = [...data.evaluaciones.filter((e) => e.estado === 'publicada').map((e) => e.fecha), ...data.asistencia.map((a) => a.actualizado_en)].sort().pop()
  const small = g.coders.length < MIN_GROUP
  const openCoder = (id: string, comp?: string) => {
    setFocusStudent(id)
    setFocusComp(comp ?? null)
    navigate('ficha')
  }
  const weekSel = g.weeks.find((w) => w.week === week)

  if (!cohorts.length) return <Empty>No tienes cohortes asignadas.</Empty>

  return (
    <>
      <PageTitle
        eyebrow="Docente · cohortes asignadas"
        title="Analítica del grupo"
        sub="Indicadores calculados en vivo desde evaluaciones publicadas, registros de asistencia y entregas. Los borradores no cuentan. Niveles 1–3 son categorías, no notas."
      />
      <Notice>
        <ShieldAlert className="mr-1 inline size-4 align-[-3px]" aria-hidden />
        Solo se muestran las cohortes asignadas a este docente ({cohorts.map((c) => c.id).join(', ')}). En la demo el alcance se aplica en la interfaz; la seguridad real exigirá backend y autenticación.
      </Notice>

      <section aria-label="Filtros" className="sticky top-[61px] z-10 mb-6 rounded-2xl border border-line bg-white/95 p-4 backdrop-blur">
        <div className="flex flex-wrap items-end gap-3">
          <Field label="Programa" htmlFor="ga-prog">
            <select id="ga-prog" className={`${inputCls} w-auto`} value={coh.programa_id} onChange={(e) => changeCohort(cohorts.find((c) => c.programa_id === e.target.value)!.id)}>
              {programs.map((p) => (
                <option key={p} value={p}>
                  {programOf(data, p)?.nombre}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Cohorte" htmlFor="ga-coh">
            <select id="ga-coh" className={`${inputCls} w-auto`} value={cohortId} onChange={(e) => changeCohort(e.target.value)}>
              {cohorts
                .filter((c) => c.programa_id === coh.programa_id)
                .map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.nombre}
                  </option>
                ))}
            </select>
          </Field>
          <Field label="Desde" htmlFor="ga-from">
            <input id="ga-from" type="date" className={`${inputCls} w-auto`} value={from} min={coh.inicio} max={to} onChange={(e) => e.target.value && setFrom(e.target.value)} />
          </Field>
          <Field label="Hasta" htmlFor="ga-to">
            <input id="ga-to" type="date" className={`${inputCls} w-auto`} value={to} min={from} max={today} onChange={(e) => e.target.value && setTo(e.target.value)} />
          </Field>
          <Field label="Proyecto" htmlFor="ga-task">
            <select id="ga-task" className={`${inputCls} w-auto`} value={tareaId} onChange={(e) => setTareaId(e.target.value)}>
              <option value="">Todos</option>
              {activeTasks(data, cohortId).map((t) => (
                <option key={t.id} value={t.id}>
                  {t.nombre}
                </option>
              ))}
            </select>
          </Field>
          <div className="ml-auto flex flex-col items-end gap-1 pb-1 text-right text-[11.5px] text-muted">
            <SyntheticBadge />
            <span>Última actualización: {lastUpdate ? fmtDay(lastUpdate) : '—'}</span>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold text-muted">Competencias:</span>
          <Button size="sm" variant={compIds.length ? 'subtle' : 'primary'} onClick={() => setCompIds([])}>
            Todas ({effectiveCompetencies(data, cohortId).length})
          </Button>
          <Chips label="Filtrar competencias" value={compIds} onChange={setCompIds} options={g.allComps.map((c) => ({ id: c.id, label: c.codigo }))} />
        </div>
        <p className="mt-2 text-[11.5px] text-muted">
          Periodo {fmtDay(g.from)} – {fmtDay(g.to)}. El estado competencial usa, por coder y competencia, la última evaluación publicada hasta la fecha final{tareaId && ' del proyecto seleccionado'}.
        </p>
      </section>

      {small && <Notice tone="warning">Muestra pequeña (N = {g.coders.length}): interpreta los porcentajes con cautela.</Notice>}

      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Metric label="Coders activos" value={g.coders.length} formula="Matrícula activa de la cohorte" />
        <Metric label="Competencias" value={g.comps.length} sub={compIds.length ? `de ${g.allComps.length}` : undefined} formula="Catálogo efectivo activo (filtro aplicado)" />
        <Metric label="Cobertura" value={pct(g.current.coverage)} sub={`${g.current.evaluated}/${g.current.pairs} pares`} formula="Pares coder-competencia con alguna evaluación publicada / N × competencias" />
        <Metric label="Nivel 2 o 3" value={pct(g.current.mastery)} sub={`${g.current.mastered}/${g.current.evaluated} evaluados`} formula="Sobre pares evaluados; los no evaluados no son nivel 0" warn={g.current.evaluated && g.current.evaluated < 10 ? 'Pocos datos' : undefined} />
        <Metric label="Asistencia" value={pct(g.att.tasa)} sub={`${g.att.presente + g.att.retraso}/${g.att.registrados} registros`} formula={`Presente o retraso / registros confirmados en ${g.att.celebradas} sesiones celebradas. ${g.att.pendiente} pendientes excluidos.`} />
        <Metric label="Entregas recibidas" value={g.del.a_tiempo + g.del.tarde} sub={`${g.del.revision} pendientes de corrección`} formula="Enviadas en tareas del periodo; corrección = sin evaluación publicada" />
        <Metric label="A tiempo" value={pct(g.onTime)} sub={`${g.del.a_tiempo}/${g.dueTotal} con plazo vencido`} formula="A tiempo / entregas cuyo plazo ya venció (incluye no entregadas)" />
        <Metric label="Alertas revisables" value={g.alerts.length} formula="Señales orientativas por revisar; no son predicciones" />
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <Card title="Evolución grupal del dominio" action={<span className="text-xs text-muted">Cortes semanales</span>}>
          {g.evo.every((p) => !p.evaluated) ? (
            <Empty>Datos insuficientes: no hay evaluaciones publicadas en el periodo.</Empty>
          ) : (
            <>
              <LineChart
                ariaLabel="Porcentaje de pares evaluados en nivel 2 o 3 y cobertura por semana"
                labels={g.evo.map((p) => p.cut)}
                notes={g.evo.map((p) => `${p.mastered}/${p.evaluated} evaluados · cobertura ${p.evaluated}/${p.pairs}`)}
                series={[
                  { key: 'm', label: '% evaluados en nivel 2–3', color: '#0f6e67', values: g.evo.map((p) => p.mastery) },
                  { key: 'c', label: 'Cobertura de evaluación', color: '#246a92', dashed: true, values: g.evo.map((p) => p.coverage) },
                ]}
              />
              <Formula>En cada corte se usa la última evaluación publicada hasta esa fecha; nunca resultados posteriores.</Formula>
              <details className="mt-3 text-sm">
                <summary className="cursor-pointer text-xs font-semibold text-blue">Ver tabla de datos</summary>
                <table className="mt-2 w-full text-xs">
                  <thead>
                    <tr className="text-left text-muted">
                      <th className="py-1">Corte</th>
                      <th>Nivel 2–3 (n/evaluados)</th>
                      <th>Cobertura (evaluados/N×C)</th>
                    </tr>
                  </thead>
                  <tbody className="tabular-nums">
                    {g.evo.map((p) => (
                      <tr key={p.cut} className="border-t border-line">
                        <td className="py-1">{fmtDay(p.cut)}</td>
                        <td>
                          {pct(p.mastery)} ({p.mastered}/{p.evaluated})
                        </td>
                        <td>
                          {pct(p.coverage)} ({p.evaluated}/{p.pairs})
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </details>
            </>
          )}
        </Card>

        <Card title="Distribución por competencia" action={<span className="text-xs text-muted">N = {g.coders.length} coders</span>}>
          <SegmentLegend segments={distSegments({ n1: 0, n2: 0, n3: 0, none: 0 })} />
          <ul className="mt-4 grid gap-3">
            {g.dist.map((d) => (
              <li key={d.comp.id}>
                <button type="button" onClick={() => setExplore(d.comp.id)} className={`w-full cursor-pointer rounded-lg p-1.5 text-left hover:bg-mist/60 ${explore === d.comp.id ? 'bg-mist ring-1 ring-blue/30' : ''}`}>
                  <div className="mb-1 flex items-center justify-between gap-2 text-xs">
                    <span className="truncate font-medium text-ink">
                      <span className="font-mono text-muted">{d.comp.codigo}</span> {d.comp.nombre}
                    </span>
                    <span className="shrink-0 tabular-nums text-muted">
                      N1 {d.n1} · N2 {d.n2} · N3 {d.n3} · sin evaluar {d.none} / {d.N}
                    </span>
                  </div>
                  <StackedBar total={d.N} segments={distSegments(d)} />
                </button>
              </li>
            ))}
          </ul>
          {!g.dist.length && <Empty>No hay competencias activas en el filtro.</Empty>}
          <Formula>Pulsa una competencia para explorarla. Las brechas se leen por competencia, no por persona.</Formula>
        </Card>
      </div>

      <Card title="Matriz de niveles (heatmap)" className="mt-5" action={<LevelLegend />}>
        {!g.coders.length || !g.comps.length ? (
          <Empty>Sin coders o competencias en el filtro.</Empty>
        ) : (
          <div className="-mx-6 overflow-x-auto px-6">
            <table className="w-full min-w-[640px] border-separate border-spacing-1 text-xs">
              <caption className="mb-2 text-left text-xs text-muted">
                Último nivel publicado hasta {fmtDay(g.to)} por coder (filas, orden alfabético) y competencia (columnas). «—» = sin evaluar. Pulsa una celda para abrir el historial individual.
              </caption>
              <thead>
                <tr>
                  <th scope="col" className="text-left font-semibold text-muted">
                    Coder
                  </th>
                  {g.comps.map((c) => (
                    <th key={c.id} scope="col" title={c.nombre} className="font-mono font-semibold text-muted">
                      {c.codigo}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {g.coders.map((c) => (
                  <tr key={c.id}>
                    <th scope="row" className="whitespace-nowrap pr-2 text-left font-medium">
                      {c.nombre_ficticio}
                    </th>
                    {g.comps.map((k) => {
                      const l = g.matrix.get(c.id)!.get(k.id) ?? null
                      return (
                        <td key={k.id}>
                          <LevelCell level={l} title={`${c.nombre_ficticio} · ${k.nombre}: ${l ? `nivel ${l}` : 'sin evaluar'}`} onClick={() => openCoder(c.id, k.id)} />
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <div className="mt-5 grid gap-5 xl:grid-cols-2">
        <Card title="Asistencia del grupo" action={<span className="text-xs text-muted">{g.att.celebradas} sesiones celebradas</span>}>
          {!g.weeks.length ? (
            <Empty>No hay sesiones celebradas en el periodo.</Empty>
          ) : (
            <>
              <ColumnChart
                ariaLabel="Registros de asistencia por semana"
                selected={week}
                onSelect={(k) => setWeek(k === week ? null : k)}
                columns={g.weeks.map((w) => ({
                  key: w.week,
                  label: fmtDay(w.week),
                  segments: [
                    { key: 'p', value: w.presente, color: '#138c83', label: 'Presentes' },
                    { key: 'r', value: w.retraso, color: '#e6b348', label: 'Retrasos' },
                    { key: 'a', value: w.ausente, color: '#c2556a', label: 'Ausentes' },
                    { key: 'n', value: w.pendiente, color: '', label: 'Pendientes', pattern: true },
                  ],
                }))}
              />
              <SegmentLegend
                segments={[
                  { key: 'p', value: g.att.presente, color: '#138c83', label: 'Presentes' },
                  { key: 'r', value: g.att.retraso, color: '#e6b348', label: 'Retrasos' },
                  { key: 'a', value: g.att.ausente, color: '#c2556a', label: 'Ausentes' },
                  { key: 'n', value: g.att.pendiente, color: '', label: 'Pendientes', pattern: true },
                ]}
                total={g.att.celebradas}
              />
              <Formula>Semana = lunes indicado. Solo sesiones ya celebradas; las futuras no se cuentan y los pendientes no son ausencias. Pulsa una semana para ver sus sesiones.</Formula>
              {weekSel && (
                <ul className="mt-3 grid gap-1.5">
                  {weekSel.sessions.map((s) => (
                    <li key={s.id} className="flex items-center justify-between gap-3 rounded-lg bg-mist/60 px-3 py-2 text-sm">
                      <span>
                        <span className="">{fmtShort(s.inicio)}</span> · {timeOf(s.inicio)} · {s.titulo}
                      </span>
                      <Button size="sm" variant="ghost" onClick={() => setSession(s.id)}>
                        Abrir sesión
                      </Button>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </Card>

        <Card title="Entregas del grupo" action={<span className="text-xs text-muted">{g.del.total} entregas esperadas</span>}>
          {!g.del.total ? (
            <Empty>No hay tareas en el periodo seleccionado.</Empty>
          ) : (
            <>
              <StackedBar
                height="h-5"
                total={g.del.total}
                segments={[
                  { key: 'at', value: g.del.a_tiempo, color: '#138c83', label: 'A tiempo' },
                  { key: 'ta', value: g.del.tarde, color: '#e6b348', label: 'Tarde' },
                  { key: 'pp', value: g.del.pendiente_en_plazo, color: '#9cc3dc', label: 'Pendiente en plazo' },
                  { key: 'pv', value: g.del.pendiente_vencida, color: '#c2556a', label: 'Pendiente vencida' },
                ]}
              />
              <div className="mt-3">
                <SegmentLegend
                  total={g.del.total}
                  segments={[
                    { key: 'at', value: g.del.a_tiempo, color: '#138c83', label: 'A tiempo' },
                    { key: 'ta', value: g.del.tarde, color: '#e6b348', label: 'Tarde' },
                    { key: 'pp', value: g.del.pendiente_en_plazo, color: '#9cc3dc', label: 'Pendiente en plazo' },
                    { key: 'pv', value: g.del.pendiente_vencida, color: '#c2556a', label: 'Pendiente vencida' },
                  ]}
                />
              </div>
              <p className="mt-3 text-sm">
                <b className="tabular-nums">{g.del.revision}</b> entregas recibidas pendientes de revisión docente.
              </p>
              <h3 className="mb-2 mt-5 text-xs font-semibold uppercase tracking-wide text-muted">Participación por tarea</h3>
              <ul className="grid gap-2.5">
                {g.perTask.map((p) => (
                  <li key={p.tarea.id}>
                    <div className="mb-1 flex justify-between gap-2 text-xs">
                      <span className="truncate">
                        {p.tarea.nombre} <span className="text-muted">· {p.vencida ? 'plazo vencido' : `vence ${fmtDay(p.tarea.fecha_entrega)}`}</span>
                      </span>
                      <span className="tabular-nums text-muted">
                        {p.sent}/{p.total} · {pct(ratio(p.sent, p.total))}
                      </span>
                    </div>
                    <StackedBar total={p.total} segments={[{ key: 's', value: p.sent, color: '#246a92', label: 'Enviadas' }]} />
                  </li>
                ))}
              </ul>
              {g.perTask.length < 2 && <Formula>Datos insuficientes para mostrar evolución de la participación (se necesitan al menos dos tareas).</Formula>}
            </>
          )}
        </Card>
      </div>

      <Card title="Explorar una competencia" className="mt-5">
        <div className="mb-4 flex flex-wrap items-end gap-3">
          <Field label="Competencia" htmlFor="ga-exp">
            <select id="ga-exp" className={`${inputCls} w-auto`} value={explore ?? ''} onChange={(e) => setExplore(e.target.value || null)}>
              <option value="">Selecciona…</option>
              {g.comps.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.codigo} · {c.nombre}
                </option>
              ))}
            </select>
          </Field>
        </div>
        {!exploreComp ? (
          <Empty>Elige una competencia (o pulsa una barra de la distribución) para ver su evolución grupal, su distribución y acceder a las fichas individuales.</Empty>
        ) : (
          <div className="grid gap-6 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
            <div>
              <p className="mb-2 text-sm text-muted">{exploreComp.descripcion}</p>
              {exploreEvo.every((p) => !p.evaluated) ? (
                <Empty>Datos insuficientes para esta competencia en el periodo.</Empty>
              ) : (
                <LineChart
                  ariaLabel={`Evolución de ${exploreComp.nombre}`}
                  labels={exploreEvo.map((p) => p.cut)}
                  notes={exploreEvo.map((p) => `${p.mastered}/${p.evaluated} evaluados de ${p.pairs}`)}
                  series={[
                    { key: 'm', label: '% evaluados en nivel 2–3', color: '#0f6e67', values: exploreEvo.map((p) => p.mastery) },
                    { key: 'c', label: 'Cobertura', color: '#246a92', dashed: true, values: exploreEvo.map((p) => p.coverage) },
                  ]}
                />
              )}
              {(() => {
                const d = g.dist.find((x) => x.comp.id === exploreComp.id)!
                return (
                  <div className="mt-4">
                    <StackedBar total={d.N} height="h-4" segments={distSegments(d)} />
                    <div className="mt-2">
                      <SegmentLegend segments={distSegments(d)} total={d.N} />
                    </div>
                  </div>
                )
              })()}
            </div>
            <div>
              <h3 className="mb-2 text-sm font-semibold">Fichas individuales (orden alfabético)</h3>
              <p className="mb-3 text-xs text-muted">Sin ranking. Las métricas aisladas no explican causas: consulta la ficha y conversa con la persona.</p>
              <ul className="grid max-h-80 gap-1 overflow-y-auto pr-1">
                {g.coders.map((c) => {
                  const l = g.matrix.get(c.id)!.get(exploreComp.id) ?? null
                  return (
                    <li key={c.id}>
                      <button type="button" onClick={() => openCoder(c.id, exploreComp.id)} className="flex w-full cursor-pointer items-center justify-between gap-3 rounded-lg px-2 py-1.5 text-left text-sm hover:bg-mist">
                        <span>{c.nombre_ficticio}</span>
                        <span className="w-12">
                          <LevelCell level={l} />
                        </span>
                      </button>
                    </li>
                  )
                })}
              </ul>
            </div>
          </div>
        )}
      </Card>

      <Card title="Contexto y calidad de los datos" className="mt-5">
        <ul className="grid gap-1.5 text-sm text-ink/85 md:grid-cols-2">
          <li>• «Sin evaluar» no equivale a nivel 1 ni a nivel 0; se excluye del porcentaje de nivel 2–3 y se refleja en la cobertura.</li>
          <li>• El corte del {fmtDay('2026-10-30')} procede de valores v1 sin fecha original (fecha de corte sintética).</li>
          <li>• Muestra: N = {g.coders.length} coders; {g.current.evaluated} pares evaluados de {g.current.pairs}.</li>
          <li>• Las alertas son reglas ilustrativas revisadas por personas, no modelos predictivos.</li>
        </ul>
      </Card>
      {session && <AttendanceModal sessionId={session} onClose={() => setSession(null)} />}
    </>
  )
}
