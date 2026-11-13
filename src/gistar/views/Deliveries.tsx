import { useState } from 'react'
import { GitBranch, Send } from 'lucide-react'
import { fmtDateTime, fmtDay } from '../dates'
import { CODER_ID, DELIVERY_LABEL, activeTasks, coderName, deliveryStatus, nominalCohorts, nowOf, reviewStatus, revisionsOf } from '../domain'
import { useGistar } from '../store'
import type { DeliveryStatus } from '../domain'
import { ReviewModal } from '../components/ReviewModal'
import { Button, Card, Empty, Field, Notice, PageTitle, Status, Table, inputCls } from '../ui'

const DS_TONE: Record<DeliveryStatus, string> = { a_tiempo: 'entregada', tarde: 'fuera_de_plazo', pendiente_en_plazo: 'enviada', pendiente_vencida: 'por_revisar' }
const RS_LABEL = { sin_entregar: 'Sin entrega', sin_revisar: 'Pendiente de revisión', borrador: 'Borrador docente', publicada: 'Publicada' } as const
const RS_TONE = { sin_entregar: 'borrador', sin_revisar: 'por_revisar', borrador: 'lista_espera', publicada: 'admitida' } as const

export function Deliveries() {
  const { role } = useGistar()
  return role === 'coder' ? <CoderDeliveries /> : <TeacherDeliveries />
}

function TeacherDeliveries() {
  const { data, role, teacherCohort, setTeacherCohort } = useGistar()
  const cohorts = nominalCohorts(data, role)
  const cohortId = cohorts.some((c) => c.id === teacherCohort) ? teacherCohort : cohorts[0]?.id
  const tasks = activeTasks(data, cohortId)
  const [taskId, setTaskId] = useState('todas')
  const [rs, setRs] = useState('todas')
  const [open, setOpen] = useState<string | null>(null)
  const now = nowOf(data)
  const rows = data.entregas
    .filter((e) => tasks.some((t) => t.id === e.tarea_id) && (taskId === 'todas' || e.tarea_id === taskId))
    .map((e) => ({ e, t: data.tareas.find((t) => t.id === e.tarea_id)!, rs: reviewStatus(data, e) }))
    .filter((r) => rs === 'todas' || r.rs === rs)
    .sort((a, b) => (a.rs === 'sin_revisar' ? -1 : 0) - (b.rs === 'sin_revisar' ? -1 : 0) || a.t.fecha_entrega.localeCompare(b.t.fecha_entrega) || coderName(data, a.e.coder_id).localeCompare(coderName(data, b.e.coder_id)))
  const pending = rows.filter((r) => r.rs === 'sin_revisar' || r.rs === 'borrador').length

  return (
    <>
      <PageTitle title="Entregas y revisión" sub="Revisión docente con rúbrica versionada. Los borradores no son visibles para el coder ni cuentan en las métricas." />
      <Card
        title="Entregas recibidas"
        action={<span className="text-xs text-muted">{rows.length} entregas · {pending} por revisar o en borrador</span>}
      >
        <div className="mb-4 flex flex-wrap gap-3">
          <Field label="Cohorte" htmlFor="de-coh">
            <select id="de-coh" className={`${inputCls} w-auto`} value={cohortId} onChange={(e) => (setTeacherCohort(e.target.value), setTaskId('todas'))}>
              {cohorts.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nombre}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Tarea" htmlFor="de-task">
            <select id="de-task" className={`${inputCls} w-auto`} value={taskId} onChange={(e) => setTaskId(e.target.value)}>
              <option value="todas">Todas</option>
              {tasks.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.nombre}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Revisión" htmlFor="de-rs">
            <select id="de-rs" className={`${inputCls} w-auto`} value={rs} onChange={(e) => setRs(e.target.value)}>
              <option value="todas">Todas</option>
              {Object.entries(RS_LABEL).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </Field>
        </div>
        {!rows.length ? (
          <Empty>No hay entregas con estos filtros.</Empty>
        ) : (
          <Table head={['Coder', 'Tarea', 'Plazo', 'Entrega', 'Revisión', '']}>
            {rows.map(({ e, t, rs: st }) => {
              const ds = deliveryStatus(e, t, now)
              return (
                <tr key={e.id}>
                  <td>
                    <span className="mr-2 font-mono text-xs text-muted">{e.coder_id}</span>
                    <span className="font-medium">{coderName(data, e.coder_id)}</span>
                  </td>
                  <td className="max-w-52 truncate text-muted">{t.nombre}</td>
                  <td className="whitespace-nowrap text-xs tabular-nums text-muted">{fmtDay(t.fecha_entrega)}</td>
                  <td>
                    <Status s={DS_TONE[ds]} label={DELIVERY_LABEL[ds]} />
                  </td>
                  <td>
                    <Status s={RS_TONE[st]} label={RS_LABEL[st]} />
                  </td>
                  <td className="text-right">
                    <Button size="sm" variant={st === 'sin_revisar' || st === 'borrador' ? 'primary' : 'ghost'} disabled={!e.enviada_en} onClick={() => setOpen(e.id)}>
                      {st === 'publicada' ? 'Revisar de nuevo' : st === 'borrador' ? 'Continuar' : 'Revisar'}
                    </Button>
                  </td>
                </tr>
              )
            })}
          </Table>
        )}
      </Card>
      {open && <ReviewModal entregaId={open} onClose={() => setOpen(null)} />}
    </>
  )
}

function CoderDeliveries() {
  const { data, update, toast } = useGistar()
  const coder = data.coders.find((c) => c.id === CODER_ID)!
  const now = nowOf(data)
  const own = data.entregas
    .filter((e) => e.coder_id === CODER_ID)
    .map((e) => ({ e, t: data.tareas.find((t) => t.id === e.tarea_id)! }))
    .filter((x) => x.t && x.t.estado === 'activa' && x.t.cohorte_id === coder.cohorte_id)
    .sort((a, b) => b.t.fecha_entrega.localeCompare(a.t.fecha_entrega))
  const [repos, setRepos] = useState<Record<string, string>>({})

  return (
    <>
      <PageTitle title="Mis entregas" sub="Tus entregas, plazos y solo las evaluaciones que tu docente ha publicado." />
      <div className="grid gap-5">
        {own.map(({ e, t }) => {
          const ds = deliveryStatus(e, t, now)
          const pub = [...revisionsOf(data, e.id)].reverse().find((r) => r.estado === 'publicada')
          const rubric = pub && data.rubricas.find((r) => r.id === pub.rubrica_id)
          const repo = repos[e.id] ?? e.repositorio_ficticio
          return (
            <Card key={e.id} title={t.nombre} action={<Status s={DS_TONE[ds]} label={DELIVERY_LABEL[ds]} />}>
              <p className="-mt-2 mb-4 text-sm text-muted">
                Plazo: {fmtDateTime(t.fecha_entrega)}
                {e.enviada_en && ` · Enviada: ${fmtDateTime(e.enviada_en)}`}
              </p>
              <div className="grid gap-5 lg:grid-cols-2">
                <div>
                  <Field label="Repositorio ficticio" htmlFor={`repo-${e.id}`}>
                    <input id={`repo-${e.id}`} className={inputCls} value={repo} onChange={(ev) => setRepos({ ...repos, [e.id]: ev.target.value })} />
                  </Field>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button
                      onClick={() =>
                        update(
                          (d) => {
                            const x = d.entregas.find((y) => y.id === e.id)!
                            x.repositorio_ficticio = repo
                            x.enviada_en = nowOf(d)
                            x.estado = 'entregada'
                          },
                          'registrar_entrega',
                          e.id,
                          undefined,
                          e.enviada_en ? 'Entrega actualizada' : 'Entrega registrada',
                        )
                      }
                    >
                      <Send className="size-4" aria-hidden /> {e.enviada_en ? 'Reenviar' : 'Registrar entrega'}
                    </Button>
                    <Button variant="ghost" onClick={() => toast('GitHub simulado: no se ha conectado ningún servicio')}>
                      <GitBranch className="size-4" aria-hidden /> Simular sincronización
                    </Button>
                  </div>
                  {e.nota_migracion && <p className="mt-3 text-xs text-muted">{e.nota_migracion}</p>}
                </div>
                <div>
                  <h3 className="mb-2 text-sm font-semibold">Evaluación publicada</h3>
                  {!pub ? (
                    <p className="text-sm text-muted">Todavía no hay una evaluación publicada para esta entrega.</p>
                  ) : (
                    <div className="grid gap-2 text-sm">
                      <p className="text-xs text-muted">
                        Publicada el {fmtDay(pub.publicada_en!)}
                        {rubric && ` · ${rubric.nombre} v${rubric.version}`}
                        {pub.origen === 'heredado_v1' && ' · feedback heredado (v1)'}
                      </p>
                      {pub.criterios.map((c) => {
                        const k = rubric?.criterios.find((x) => x.id === c.criterio_id)
                        return (
                          <div key={c.criterio_id} className="flex items-start justify-between gap-3 rounded-lg bg-mist/60 px-3 py-2">
                            <div>
                              <p className="font-medium">{k?.nombre}</p>
                              {c.comentario && <p className="text-xs text-muted">{c.comentario}</p>}
                            </div>
                            <span className="text-xs font-bold">{c.nivel ? `N${c.nivel}` : '—'}</span>
                          </div>
                        )
                      })}
                      {pub.feedback && <Notice>{pub.feedback}</Notice>}
                    </div>
                  )}
                </div>
              </div>
            </Card>
          )
        })}
        {!own.length && <Empty>No tienes entregas asignadas.</Empty>}
      </div>
    </>
  )
}
