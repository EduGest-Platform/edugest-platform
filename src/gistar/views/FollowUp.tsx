import { useState } from 'react'
import { CircleCheck, HeartHandshake } from 'lucide-react'
import { pct } from '../analytics'
import { fmtDay, fmtShort, timeOf } from '../dates'
import { ABSENCE_RULE, attendanceSummary, cohortCoders, coderName, nominalCohorts, nowOf, sessionsOf } from '../domain'
import { useGistar } from '../store'
import { AttendanceModal } from '../components/AttendanceModal'
import { Button, Card, Empty, Field, Notice, PageTitle, Status, Table, inputCls } from '../ui'

export function Attendance() {
  const { data, role, teacherCohort, setTeacherCohort } = useGistar()
  const cohorts = nominalCohorts(data, role)
  const cohortId = cohorts.some((c) => c.id === teacherCohort) ? teacherCohort : cohorts[0]?.id
  const [open, setOpen] = useState<string | null>(null)
  const now = nowOf(data)
  const sessions = sessionsOf(data, cohortId)
  const held = sessions.filter((s) => s.inicio <= now).reverse()
  const upcoming = sessions.filter((s) => s.inicio > now).slice(0, 4)
  const coders = cohortCoders(data, cohortId)
  const total = attendanceSummary(data, cohortId)

  return (
    <>
      <PageTitle title="Asistencia por sesión" sub="Un registro por coder y sesión fechada. Los resúmenes se recalculan desde los registros; las sesiones futuras y los registros pendientes no cuentan como ausencias." />
      <div className="mb-5 flex flex-wrap items-end gap-3">
        <Field label="Cohorte" htmlFor="as-coh">
          <select id="as-coh" className={`${inputCls} w-auto`} value={cohortId} onChange={(e) => setTeacherCohort(e.target.value)}>
            {cohorts.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
            ))}
          </select>
        </Field>
        <p className="pb-2.5 text-sm text-muted">
          Asistencia de la cohorte: <b className="text-ink">{pct(total.tasa)}</b> ({total.presente + total.retraso}/{total.registrados} registros confirmados · {total.pendiente} pendientes)
        </p>
      </div>
      <Notice>
        Regla orientativa: {ABSENCE_RULE.threshold} o más ausencias confirmadas en las últimas {ABSENCE_RULE.window} sesiones registradas generan una señal para revisión humana. Las faltas no prueban abandono. Puedes crear sesiones nuevas desde el Calendario.
      </Notice>
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        <Card title="Sesiones celebradas" action={<span className="text-xs text-muted">{held.length} sesiones</span>}>
          {!held.length ? (
            <Empty>No hay sesiones celebradas.</Empty>
          ) : (
            <Table head={['Fecha', 'Sesión', 'Registro', '']}>
              {held.map((s) => {
                const recs = data.asistencia.filter((r) => r.evento_id === s.id && r.estado !== 'pendiente').length
                const done = recs === coders.length
                return (
                  <tr key={s.id}>
                    <td className="whitespace-nowrap">
                      {fmtShort(s.inicio)} <span className="text-muted">{timeOf(s.inicio)}</span>
                    </td>
                    <td className="max-w-56 truncate">{s.titulo}</td>
                    <td>
                      {done ? (
                        <span className="inline-flex items-center gap-1 text-xs font-semibold text-teal-700">
                          <CircleCheck className="size-3.5" aria-hidden /> Completo
                        </span>
                      ) : (
                        <span className="text-xs font-semibold text-amber-700">
                          {recs}/{coders.length} registrados
                        </span>
                      )}
                    </td>
                    <td className="text-right">
                      <Button size="sm" variant={done ? 'ghost' : 'primary'} onClick={() => setOpen(s.id)}>
                        {done ? 'Editar' : 'Registrar'}
                      </Button>
                    </td>
                  </tr>
                )
              })}
            </Table>
          )}
          {upcoming.length > 0 && (
            <p className="mt-4 text-xs text-muted">
              Próximas (no registrables aún): {upcoming.map((s) => fmtShort(s.inicio)).join(' · ')}
            </p>
          )}
        </Card>
        <Card title="Resumen por coder">
          <Table head={['Coder', 'Presente', 'Retraso', 'Ausente', 'Pendiente', 'Tasa']}>
            {coders.map((c) => {
              const s = attendanceSummary(data, cohortId, { coderId: c.id })
              return (
                <tr key={c.id}>
                  <td className="font-medium">{c.nombre_ficticio}</td>
                  <td className="tabular-nums">{s.presente}</td>
                  <td className="tabular-nums">{s.retraso}</td>
                  <td className="tabular-nums">{s.ausente}</td>
                  <td className="tabular-nums text-muted">{s.pendiente}</td>
                  <td className="tabular-nums">{pct(s.tasa)}</td>
                </tr>
              )
            })}
          </Table>
        </Card>
      </div>
      {open && <AttendanceModal sessionId={open} onClose={() => setOpen(null)} />}
    </>
  )
}

export function Alerts() {
  const { data, role } = useGistar()
  const scope = role === 'docente' ? new Set(nominalCohorts(data, role).map((c) => c.id)) : null
  const alerts = data.alertas_simuladas.filter((a) => !scope || scope.has(data.coders.find((c) => c.id === a.coder_id)?.cohorte_id ?? ''))
  return (
    <>
      <PageTitle title="Tutoría y alertas" sub="Señales de seguimiento explicables, no predicciones ni decisiones automáticas." />
      <Notice tone="warning">Las señales se calculan con reglas ilustrativas, no con un modelo predictivo entrenado. Las necesidades personales o vulnerabilidades nunca se usan para puntuar ni clasificar.</Notice>
      {alerts.length === 0 && <Empty>No hay alertas registradas.</Empty>}
      <div className="grid gap-5 lg:grid-cols-2">
        {alerts.map((x) => (
          <AlertCard key={x.id} id={x.id} />
        ))}
      </div>
    </>
  )
}

function AlertCard({ id }: { id: string }) {
  const { data, role, update } = useGistar()
  const x = data.alertas_simuladas.find((a) => a.id === id)!
  const [plan, setPlan] = useState('Contactar y explorar barreras de participación, acordar seguimiento.')
  const canAct = role === 'docente' || role === 'fundacion'
  return (
    <Card
      title={
        <span>
          {coderName(data, x.coder_id)} <span className="font-mono text-sm font-normal text-muted">· {x.coder_id}</span>
        </span>
      }
      action={<Status s={x.estado} />}
    >
      <p className="-mt-2 mb-3 text-xs text-muted">
        Alerta {x.id}
        {x.creada_en && ` · ${fmtDay(x.creada_en)}`} · simulación, no clasificación real
      </p>
      <div className="flex flex-wrap gap-2">
        {x.senales.map((s) => (
          <span key={s} className="rounded-lg bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-900">
            {s}
          </span>
        ))}
      </div>
      {x.explicacion && <p className="mt-3 text-xs leading-relaxed text-muted">{x.explicacion}</p>}
      {x.estado === 'por_revisar' && canAct && (
        <div className="mt-5 grid gap-3">
          <Field label="Plan de tutoría / apoyo" htmlFor={`plan-${x.id}`}>
            <textarea id={`plan-${x.id}`} className={`${inputCls} min-h-24`} value={plan} onChange={(e) => setPlan(e.target.value)} />
          </Field>
          <div>
            <Button
              variant="success"
              disabled={!plan.trim()}
              onClick={() =>
                update(
                  (d) => {
                    const a = d.alertas_simuladas.find((y) => y.id === id)!
                    a.estado = 'en_seguimiento'
                    a.plan_apoyo = plan
                    d.planes_apoyo.push({ alerta_id: id, coder_id: a.coder_id, nota: plan, responsable: role === 'docente' ? 'USR-DOC' : 'USR-FUND', fecha_revision: '2026-11-20' })
                  },
                  'plan_tutoria',
                  id,
                )
              }
            >
              <HeartHandshake className="size-4" aria-hidden /> Guardar plan de apoyo
            </Button>
          </div>
        </div>
      )}
      {x.estado === 'en_seguimiento' && (
        <>
          <Notice>
            <b>Plan registrado</b> · revisión el 20 nov 2026
            <br />
            {x.plan_apoyo}
          </Notice>
          {canAct && (
            <Button variant="ghost" size="sm" onClick={() => update((d) => (d.alertas_simuladas.find((y) => y.id === id)!.estado = 'cerrada'), 'cerrar_alerta', id)}>
              Cerrar seguimiento
            </Button>
          )}
        </>
      )}
      {x.estado === 'cerrada' && <p className="mt-3 text-sm text-muted">Seguimiento cerrado tras revisión humana.</p>}
    </Card>
  )
}
