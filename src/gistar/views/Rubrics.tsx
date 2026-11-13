import { useState } from 'react'
import { Archive, ArrowDown, ArrowUp, Copy, Pencil, Plus, Send, Trash2 } from 'lucide-react'
import { archiveRubric, publishRubric, saveRubricDraft, validateRubric } from '../actions'
import { fmtDateTime, fmtDay } from '../dates'
import { activeTasks, effectiveCompetencies, nominalCohorts, uid } from '../domain'
import { useGistar } from '../store'
import type { Criterio, Rubrica, Tarea } from '../types'
import { Modal } from '../components/Modal'
import { Button, Card, Empty, Field, Notice, PageTitle, Status, Table, inputCls } from '../ui'

export function Rubrics() {
  const { data, role, update, toast } = useGistar()
  const cohorts = nominalCohorts(data, role)
  const [cohortId, setCohortId] = useState(cohorts[0]?.id ?? '')
  const [editor, setEditor] = useState<{ rubric?: Rubrica; tareaId: string; duplicateOf?: Rubrica } | null>(null)
  const tasks = activeTasks(data, cohortId)
  const usage = (r: Rubrica) => data.revisiones.filter((x) => x.rubrica_id === r.id && x.estado === 'publicada').length

  const act = (fn: () => void) => {
    try {
      fn()
    } catch (e) {
      toast((e as Error).message)
    }
  }

  return (
    <>
      <PageTitle
        eyebrow="Modelo académico"
        title="Rúbricas por tarea"
        sub="Cada tarea tiene rúbricas versionadas con criterios libres vinculados a competencias. Las versiones usadas en evaluaciones publicadas se conservan y no se pueden editar."
      />
      <div className="mb-5 flex flex-wrap items-end gap-3">
        <Field label="Cohorte" htmlFor="rb-coh">
          <select id="rb-coh" className={`${inputCls} w-auto`} value={cohortId} onChange={(e) => setCohortId(e.target.value)}>
            {cohorts.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
            ))}
          </select>
        </Field>
        <p className="pb-2.5 text-xs text-muted">Para crear una tarea nueva, añade una «Entrega de proyecto» en el Calendario.</p>
      </div>
      {!tasks.length && <Empty>Esta cohorte no tiene tareas activas.</Empty>}
      <div className="grid gap-5">
        {tasks.map((t) => {
          const versions = data.rubricas.filter((r) => r.tarea_id === t.id).sort((a, b) => b.version - a.version)
          return (
            <Card
              key={t.id}
              title={t.nombre}
              action={
                <Button size="sm" onClick={() => setEditor({ tareaId: t.id })}>
                  <Plus className="size-4" aria-hidden /> Nueva versión
                </Button>
              }
            >
              <p className="-mt-2 mb-4 text-sm text-muted">
                {t.id} · plazo {fmtDateTime(t.fecha_entrega)} · {t.rubrica_id ? `vigente: v${data.rubricas.find((r) => r.id === t.rubrica_id)?.version}` : 'sin rúbrica publicada'}
              </p>
              {!versions.length ? (
                <Empty>Sin rúbricas. Crea la primera versión para poder revisar entregas.</Empty>
              ) : (
                <Table head={['Versión', 'Nombre', 'Criterios', 'Estado', 'Uso', 'Acciones']}>
                  {versions.map((r) => (
                    <tr key={r.id}>
                      <td className="font-mono text-xs font-semibold">v{r.version}</td>
                      <td>
                        <p className="font-medium">{r.nombre}</p>
                        <p className="text-xs text-muted">{r.publicada_en ? `Publicada ${fmtDay(r.publicada_en)}` : `Creada ${fmtDay(r.creada_en)}`}</p>
                      </td>
                      <td className="text-xs text-muted">
                        {r.criterios.length} · {r.criterios.map((k) => k.nombre).join(', ')}
                      </td>
                      <td>
                        <Status s={r.estado === 'publicada' ? 'en_seguimiento' : r.estado === 'borrador' ? 'borrador' : 'lista_espera'} label={r.id === t.rubrica_id ? 'Publicada · vigente' : r.estado} />
                      </td>
                      <td className="text-xs tabular-nums">{usage(r)} revisiones</td>
                      <td>
                        <div className="flex flex-wrap gap-1">
                          {r.estado === 'borrador' && (
                            <>
                              <Button size="sm" variant="ghost" onClick={() => setEditor({ rubric: r, tareaId: t.id })}>
                                <Pencil className="size-3.5" aria-hidden /> Editar
                              </Button>
                              <Button
                                size="sm"
                                variant="success"
                                onClick={() =>
                                  act(() => {
                                    const err = validateRubric(r.criterios)
                                    if (err) throw new Error(err)
                                    update((d) => publishRubric(d, r.id), 'publicar_rubrica', r.id, `v${r.version}`)
                                  })
                                }
                              >
                                <Send className="size-3.5" aria-hidden /> Publicar
                              </Button>
                            </>
                          )}
                          <Button size="sm" variant="ghost" onClick={() => setEditor({ tareaId: t.id, duplicateOf: r })}>
                            <Copy className="size-3.5" aria-hidden /> Duplicar
                          </Button>
                          {r.estado !== 'archivada' && (
                            <Button
                              size="sm"
                              variant="subtle"
                              onClick={() => {
                                if (r.id === t.rubrica_id && !confirm('Es la rúbrica vigente: la tarea quedará sin rúbrica para nuevas revisiones. ¿Archivar?')) return
                                update((d) => archiveRubric(d, r.id), 'archivar_rubrica', r.id)
                              }}
                            >
                              <Archive className="size-3.5" aria-hidden /> Archivar
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </Table>
              )}
            </Card>
          )
        })}
      </div>
      {editor && <RubricEditor key={editor.rubric?.id ?? editor.duplicateOf?.id ?? 'new'} {...editor} tasks={tasks} onClose={() => setEditor(null)} />}
    </>
  )
}

const emptyCrit = (): Criterio => ({ id: uid('K'), nombre: '', definicion: '', evidencia: '', peso: null, competencias: [] })

function RubricEditor({ rubric, tareaId, duplicateOf, tasks, onClose }: { rubric?: Rubrica; tareaId: string; duplicateOf?: Rubrica; tasks: Tarea[]; onClose: () => void }) {
  const { data, update, toast } = useGistar()
  const src = rubric ?? duplicateOf
  const init = {
    tarea: rubric?.tarea_id ?? tareaId,
    nombre: src ? (duplicateOf ? `${src.nombre} (copia)` : src.nombre) : `Rúbrica ${tasks.find((t) => t.id === tareaId)?.nombre ?? ''}`,
    criterios: src ? src.criterios.map((k) => ({ ...k, id: duplicateOf ? uid('K') : k.id, competencias: [...k.competencias] })) : [emptyCrit()],
  }
  const [f, setF] = useState(init)
  const dirty = JSON.stringify(f) !== JSON.stringify(init)
  const tarea = data.tareas.find((t) => t.id === f.tarea)!
  const comps = effectiveCompetencies(data, tarea.cohorte_id)
  const weighted = f.criterios.some((k) => k.peso != null)
  const sum = f.criterios.reduce((a, k) => a + (k.peso ?? 0), 0)
  const error = validateRubric(f.criterios)
  const setK = (i: number, patch: Partial<Criterio>) => setF({ ...f, criterios: f.criterios.map((k, j) => (j === i ? { ...k, ...patch } : k)) })
  const move = (i: number, dir: number) => {
    const c = [...f.criterios]
    ;[c[i], c[i + dir]] = [c[i + dir], c[i]]
    setF({ ...f, criterios: c })
  }

  const save = (publish: boolean) => {
    if (publish && error) return toast(error)
    if (f.criterios.some((k) => !k.nombre.trim())) return toast('Todos los criterios necesitan nombre')
    update(
      (d) => {
        const r = saveRubricDraft(d, { id: rubric?.id, familia_id: duplicateOf?.familia_id ?? rubric?.familia_id, tarea_id: f.tarea, nombre: f.nombre, criterios: f.criterios, basada_en: duplicateOf?.id ?? rubric?.basada_en ?? null })
        if (publish) publishRubric(d, r.id)
      },
      publish ? 'publicar_rubrica' : 'guardar_rubrica',
      f.tarea,
      `${f.criterios.length} criterios`,
      publish ? 'Rúbrica publicada y vigente para la tarea' : 'Borrador de rúbrica guardado',
    )
    onClose()
  }

  return (
    <Modal
      open
      dirty={dirty}
      onClose={onClose}
      title={rubric ? `Editar borrador v${rubric.version}` : duplicateOf ? `Duplicar v${duplicateOf.version}` : 'Nueva versión de rúbrica'}
      subtitle="Los criterios valoran la entrega; las competencias vinculadas reciben el nivel en el historial del coder."
      footer={
        <>
          <span className={`mr-auto text-xs ${error ? 'text-amber-700' : 'text-teal-700'}`}>{error ?? 'Lista para publicar'}</span>
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button variant="ghost" onClick={() => save(false)}>
            Guardar borrador
          </Button>
          <Button variant="success" disabled={!!error} onClick={() => save(true)}>
            Publicar
          </Button>
        </>
      }
    >
      <div className="mb-5 grid gap-4 sm:grid-cols-2">
        <Field label="Nombre" htmlFor="rb-name">
          <input id="rb-name" data-autofocus className={inputCls} value={f.nombre} onChange={(e) => setF({ ...f, nombre: e.target.value })} />
        </Field>
        <Field label="Tarea" htmlFor="rb-task">
          <select id="rb-task" className={inputCls} value={f.tarea} disabled={!!rubric} onChange={(e) => setF({ ...f, tarea: e.target.value })}>
            {tasks.map((t) => (
              <option key={t.id} value={t.id}>
                {t.nombre}
              </option>
            ))}
          </select>
        </Field>
      </div>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">Criterios ({f.criterios.length})</h3>
        <div className="flex flex-wrap items-center gap-3 text-xs">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              className="size-4 accent-teal"
              checked={weighted}
              onChange={(e) => {
                const n = f.criterios.length
                setF({ ...f, criterios: f.criterios.map((k, i) => ({ ...k, peso: e.target.checked ? Math.floor(100 / n) + (i < 100 % n ? 1 : 0) : null })) })
              }}
            />
            Usar pesos
          </label>
          {weighted && <span className={`font-semibold tabular-nums ${Math.abs(sum - 100) < 0.001 ? 'text-teal-700' : 'text-amber-700'}`}>Suma: {sum}% / 100%</span>}
        </div>
      </div>
      <ol className="grid gap-3">
        {f.criterios.map((k, i) => (
          <li key={k.id} className="rounded-xl border border-line p-4">
            <div className="mb-3 flex items-center gap-2">
              <span className="text-xs font-bold text-muted">Criterio {i + 1}</span>
              <div className="ml-auto flex gap-0.5">
                <Button size="sm" variant="subtle" aria-label="Subir criterio" disabled={i === 0} onClick={() => move(i, -1)}>
                  <ArrowUp className="size-3.5" aria-hidden />
                </Button>
                <Button size="sm" variant="subtle" aria-label="Bajar criterio" disabled={i === f.criterios.length - 1} onClick={() => move(i, 1)}>
                  <ArrowDown className="size-3.5" aria-hidden />
                </Button>
                <Button size="sm" variant="subtle" aria-label="Eliminar criterio" disabled={f.criterios.length === 1} onClick={() => setF({ ...f, criterios: f.criterios.filter((_, j) => j !== i) })}>
                  <Trash2 className="size-3.5" aria-hidden />
                </Button>
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_96px]">
              <input aria-label={`Nombre del criterio ${i + 1}`} placeholder="Nombre" className={inputCls} value={k.nombre} onChange={(e) => setK(i, { nombre: e.target.value })} />
              <input aria-label={`Evidencia del criterio ${i + 1}`} placeholder="Evidencia esperada" className={inputCls} value={k.evidencia} onChange={(e) => setK(i, { evidencia: e.target.value })} />
              <input
                aria-label={`Peso del criterio ${i + 1}`}
                type="number"
                min={0}
                max={100}
                placeholder="Peso %"
                disabled={!weighted}
                className={inputCls}
                value={k.peso ?? ''}
                onChange={(e) => setK(i, { peso: e.target.value === '' ? 0 : Number(e.target.value) })}
              />
              <textarea aria-label={`Definición del criterio ${i + 1}`} placeholder="Definición: qué se observa" className={`${inputCls} min-h-16 sm:col-span-3`} value={k.definicion} onChange={(e) => setK(i, { definicion: e.target.value })} />
            </div>
            <p className="mb-1.5 mt-3 text-xs font-semibold text-muted">Competencias relacionadas</p>
            <div className="flex flex-wrap gap-1.5">
              {comps.map((c) => {
                const on = k.competencias.includes(c.id)
                return (
                  <button
                    key={c.id}
                    type="button"
                    aria-pressed={on}
                    onClick={() => setK(i, { competencias: on ? k.competencias.filter((x) => x !== c.id) : [...k.competencias, c.id] })}
                    className={`cursor-pointer rounded-full border px-2.5 py-1 text-xs ${on ? 'border-teal bg-teal-50 font-semibold text-teal-900' : 'border-line text-ink/70 hover:border-teal/50'}`}
                  >
                    {c.codigo} · {c.nombre}
                  </button>
                )
              })}
            </div>
          </li>
        ))}
      </ol>
      <Button variant="ghost" className="mt-3" onClick={() => setF({ ...f, criterios: [...f.criterios, { ...emptyCrit(), peso: weighted ? 0 : null }] })}>
        <Plus className="size-4" aria-hidden /> Añadir criterio
      </Button>
      {duplicateOf && <Notice>Se creará una nueva versión en borrador; la versión original y sus evaluaciones no cambian.</Notice>}
    </Modal>
  )
}
