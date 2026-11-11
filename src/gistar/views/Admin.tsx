import { MIN_CELL, cohortAggregate, pct } from '../analytics'
import { fmtDay } from '../dates'
import { MIN_GROUP, cohortCoders, effectiveCompetencies, programCompetencies } from '../domain'
import { metrics } from '../metrics'
import { useGistar } from '../store'
import { LevelLegend } from '../components/charts'
import { Card, Kpi, Notice, PageTitle, SyntheticBadge, Table } from '../ui'
import { humanize } from '../config'

function ProgramGrid() {
  const { data } = useGistar()
  return (
    <div className="grid gap-5 lg:grid-cols-2">
      {data.programas.map((p) => {
        const cohorts = data.cohortes.filter((h) => h.programa_id === p.id)
        const participants = cohorts.reduce((a, h) => a + cohortCoders(data, h.id).length, 0)
        const comps = programCompetencies(data, p.id).filter((x) => x.activo && x.cohorte_id === null).length
        return (
          <Card key={p.id} title={p.nombre} action={<span className="font-mono text-xs text-muted">{p.id}</span>}>
            <p className="-mt-2 mb-5 text-sm text-muted">{p.descripcion}</p>
            <div className="grid grid-cols-2 gap-3">
              <Stat n={participants} l="participantes" />
              <Stat n={comps} l="competencias en catálogo" />
            </div>
            {cohorts.map((h) => (
              <p key={h.id} className="mt-4 border-t border-line pt-3 text-xs text-muted">
                {h.nombre} · {h.inicio} → {h.fin} · {effectiveCompetencies(data, h.id).length} competencias efectivas
              </p>
            ))}
          </Card>
        )
      })}
    </div>
  )
}

function Stat({ n, l }: { n: number | string; l: string }) {
  return (
    <div className="rounded-xl bg-mist/70 px-4 py-3">
      <div className="text-2xl font-bold tabular-nums text-navy">{n}</div>
      <div className="text-xs text-muted">{l}</div>
    </div>
  )
}

export function Programs() {
  return (
    <>
      <PageTitle title="Programas y cohortes" sub="Vista administrativa del catálogo educativo." />
      <ProgramGrid />
    </>
  )
}

export function AuditTrail() {
  const { data } = useGistar()
  return (
    <>
      <PageTitle title="Bitácora de actividades" sub="Registro sintético local de las acciones realizadas en la demo." />
      <Card title="Actividad reciente" action={<span className="text-xs text-muted">Últimos 50 eventos</span>}>
        <Table head={['Fecha', 'Rol', 'Entidad', 'Acción', 'Detalle']}>
          {data.bitacora_demo.slice(0, 50).map((a) => (
            <tr key={a.id}>
              <td className="tabular-nums text-muted">{a.fecha_simulada}</td>
              <td className="capitalize">{a.actor_rol}</td>
              <td className="font-mono text-xs">{a.entidad}</td>
              <td className="font-medium capitalize">{humanize(a.accion)}</td>
              <td className="text-muted">{a.detalle}</td>
            </tr>
          ))}
        </Table>
      </Card>
    </>
  )
}

/** Coordination / funding: aggregates only. No names, no individual records, small groups suppressed. */
export function Coordination() {
  const { data } = useGistar()
  const m = metrics(data)
  const cell = (n: number, N: number) => (n > 0 && n < MIN_CELL ? `<${MIN_CELL}` : pct(N ? n / N : null))
  return (
    <>
      <PageTitle title="Coordinación" sub="Indicadores agregados por cohorte. No se exponen nombres, fichas ni evaluaciones individuales." />
      <div className="mb-4 flex justify-end">
        <SyntheticBadge />
      </div>
      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Kpi label="Personas en formación" value={m.coders} />
        <Kpi label="Candidaturas" value={m.candidaturas} />
        <Kpi label="Asistencia registrada" value={m.asistencia == null ? '—' : `${m.asistencia}%`} />
        <Kpi label="Alertas pendientes" value={m.alertas} />
      </div>
      <Notice>
        Agregados con supresión: si una cohorte tiene menos de {MIN_GROUP} personas no se muestran sus valores, y los recuentos por nivel inferiores a {MIN_CELL} se muestran como «&lt;{MIN_CELL}».
      </Notice>
      <div className="grid gap-5 lg:grid-cols-2">
        {data.cohortes.map((c) => {
          const a = cohortAggregate(data, c.id, MIN_GROUP)
          return (
            <Card key={c.id} title={c.nombre} action={<span className="text-xs text-muted">Actualizado {fmtDay(data.meta.fecha_simulada)}</span>}>
              {a.suppressed ? (
                <p className="text-sm text-muted">Grupo demasiado pequeño (N &lt; {MIN_GROUP}): valores ocultos para evitar identificaciones.</p>
              ) : (
                <>
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                    <Stat n={a.N} l="coders activos" />
                    <Stat n={pct(a.g.current.coverage)} l="cobertura de evaluación" />
                    <Stat n={pct(a.g.current.mastery)} l="pares evaluados en N2–3" />
                    <Stat n={pct(a.g.att.tasa)} l="asistencia confirmada" />
                  </div>
                  <p className="mt-3 text-xs text-muted">
                    Entregas a tiempo: {pct(a.g.onTime)} sobre {a.g.dueTotal} con plazo vencido.
                  </p>
                  <h3 className="mb-2 mt-5 text-xs font-semibold uppercase tracking-wide text-muted">Distribución agregada por competencia</h3>
                  <LevelLegend />
                  <Table head={['Competencia', 'N1', 'N2', 'N3', 'Sin evaluar']}>
                    {a.g.dist.map((d) => (
                      <tr key={d.comp.id}>
                        <td>
                          <span className="font-mono text-xs text-muted">{d.comp.codigo}</span> {d.comp.nombre}
                        </td>
                        <td className="tabular-nums">{cell(d.n1, d.N)}</td>
                        <td className="tabular-nums">{cell(d.n2, d.N)}</td>
                        <td className="tabular-nums">{cell(d.n3, d.N)}</td>
                        <td className="tabular-nums text-muted">{cell(d.none, d.N)}</td>
                      </tr>
                    ))}
                  </Table>
                </>
              )}
            </Card>
          )
        })}
      </div>
      <div className="mt-6">
        <ProgramGrid />
      </div>
    </>
  )
}
