import { useMemo, useState } from 'react'
import { ExternalLink, Save, Send } from 'lucide-react'
import { fmtDateTime, fmtDay } from '../dates'
import { DELIVERY_LABEL, coderName, deliveryStatus, latestEval, nowOf, revisionsOf, todayOf } from '../domain'
import { applyReview } from '../actions'
import { useGistar } from '../store'
import type { Level } from '../types'
import { Modal } from './Modal'
import { Button, Field, Notice, Status, inputCls } from '../ui'

type CritState = Record<string, { nivel: Level | null; evidencia: string; comentario: string }>

export function ReviewModal({ entregaId, onClose }: { entregaId: string; onClose: () => void }) {
  const { data, update, navigate } = useGistar()
  const ent = data.entregas.find((e) => e.id === entregaId)!
  const tarea = data.tareas.find((t) => t.id === ent.tarea_id)!
  const revs = revisionsOf(data, ent.id)
  const draft = revs.find((r) => r.estado === 'borrador')
  const lastPub = [...revs].reverse().find((r) => r.estado === 'publicada')
  const rubric = data.rubricas.find((r) => r.id === (draft?.rubrica_id ?? tarea.rubrica_id))
  const comps = useMemo(() => {
    const ids = [...new Set(rubric?.criterios.flatMap((k) => k.competencias) ?? [])]
    return ids.map((id) => data.competencias.find((c) => c.id === id)).filter(Boolean) as typeof data.competencias
  }, [rubric, data])

  const initial = useMemo(() => {
    const base = draft ?? (lastPub?.rubrica_id === rubric?.id ? lastPub : undefined)
    const crit: CritState = {}
    for (const k of rubric?.criterios ?? []) {
      const r = base?.criterios.find((x) => x.criterio_id === k.id)
      crit[k.id] = { nivel: r?.nivel ?? null, evidencia: r?.evidencia ?? '', comentario: r?.comentario ?? '' }
    }
    const over: Record<string, Level | null> = {}
    for (const c of draft?.competencias ?? []) over[c.competencia_id] = c.nivel
    return { crit, over, feedback: draft?.feedback ?? ent.feedback_borrador ?? '' }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entregaId])
  const [crit, setCrit] = useState<CritState>(initial.crit)
  const [over, setOver] = useState<Record<string, Level | null>>(initial.over)
  const [feedback, setFeedback] = useState(initial.feedback)
  const [human, setHuman] = useState(false)
  const dirty = JSON.stringify({ crit, over, feedback }) !== JSON.stringify({ crit: initial.crit, over: initial.over, feedback: initial.feedback })

  /** Conservative proposal: the lowest level among criteria linked to the competency. Editable by the teacher. */
  const auto = (compId: string): Level | null => {
    const lv = (rubric?.criterios ?? []).filter((k) => k.competencias.includes(compId)).map((k) => crit[k.id]?.nivel).filter((x): x is Level => !!x)
    return lv.length ? (Math.min(...lv) as Level) : null
  }
  const compLevel = (id: string) => (id in over && over[id] !== undefined ? over[id] : auto(id))
  const missing = (rubric?.criterios ?? []).filter((k) => !crit[k.id]?.nivel)
  const status = deliveryStatus(ent, tarea, nowOf(data))

  const persist = (publish: boolean) => {
    update(
      (d) =>
        applyReview(d, {
          entregaId,
          rubricaId: rubric!.id,
          criterios: crit,
          competencias: comps.map((c) => ({ competencia_id: c.id, nivel: compLevel(c.id) })),
          feedback,
          publish,
        }),
      publish ? 'publicar_evaluacion' : 'guardar_borrador_evaluacion',
      ent.id,
      `${tarea.nombre} · rúbrica v${rubric!.version}`,
      publish ? 'Evaluación publicada: métricas actualizadas' : 'Borrador guardado (no visible ni contabilizado)',
    )
    onClose()
  }

  return (
    <Modal
      open
      onClose={onClose}
      dirty={dirty}
      title={`Revisión · ${coderName(data, ent.coder_id)}`}
      subtitle={
        <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <span>{tarea.nombre}</span>
          <span>Plazo: {fmtDateTime(tarea.fecha_entrega)}</span>
          <span>{ent.enviada_en ? `Enviada: ${fmtDateTime(ent.enviada_en)}` : 'Sin enviar'}</span>
          <Status s={status === 'a_tiempo' ? 'entregada' : status === 'tarde' ? 'fuera_de_plazo' : 'borrador'} label={DELIVERY_LABEL[status]} />
        </span>
      }
      footer={
        rubric && (
          <>
            <label className="mr-auto flex items-center gap-2 text-sm">
              <input type="checkbox" className="size-4 accent-teal" checked={human} onChange={(e) => setHuman(e.target.checked)} />
              He revisado personalmente esta evaluación
            </label>
            <Button variant="ghost" onClick={onClose}>
              Cancelar
            </Button>
            <Button variant="ghost" onClick={() => persist(false)}>
              <Save className="size-4" aria-hidden /> Guardar borrador
            </Button>
            <Button variant="success" disabled={!human || missing.length > 0} title={missing.length ? 'Valora todos los criterios' : !human ? 'Confirma la revisión humana' : undefined} onClick={() => persist(true)}>
              <Send className="size-4" aria-hidden /> Publicar evaluación
            </Button>
          </>
        )
      }
    >
      <div className="mb-5 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
        <a href={ent.repositorio_ficticio} onClick={(e) => e.preventDefault()} className="inline-flex items-center gap-1.5 text-blue hover:underline" title="Enlace ficticio: no se abre ningún servicio">
          <ExternalLink className="size-3.5" aria-hidden /> {ent.repositorio_ficticio}
        </a>
        {draft && <Status s="borrador" label="Borrador en curso" />}
        {lastPub && <span className="text-muted">Última publicación: {fmtDay(lastPub.publicada_en!)}</span>}
      </div>
      {!rubric ? (
        <Notice tone="warning">
          Esta tarea no tiene una rúbrica publicada.{' '}
          <button type="button" className="cursor-pointer font-semibold underline" onClick={() => (onClose(), navigate('rubricas'))}>
            Ir a Rúbricas
          </button>
        </Notice>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
          <div className="min-w-0">
            <h3 className="mb-1 text-sm font-semibold">
              {rubric.nombre} · v{rubric.version}
            </h3>
            <p className="mb-3 text-xs text-muted">
              {rubric.criterios.length} criterios{rubric.criterios.some((k) => k.peso != null) && ' · ponderados'}. Los niveles 1–3 son descriptores, no notas.
            </p>
            <ol className="grid gap-3">
              {rubric.criterios.map((k, i) => (
                <li key={k.id} className="rounded-xl border border-line p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="font-semibold">
                        {i + 1}. {k.nombre}
                        {k.peso != null && <span className="ml-2 text-xs font-medium text-muted">{k.peso}%</span>}
                      </p>
                      <p className="mt-0.5 text-sm text-muted">{k.definicion}</p>
                      <p className="mt-1 text-xs text-muted">
                        Evidencia esperada: <span className="text-ink/80">{k.evidencia || '—'}</span>
                      </p>
                      <div className="mt-2 flex flex-wrap gap-1">
                        {k.competencias.map((cid) => {
                          const c = data.competencias.find((x) => x.id === cid)
                          return (
                            <span key={cid} className="rounded-md bg-mist px-1.5 py-0.5 text-[11px] font-medium text-[#255c81]">
                              {c?.codigo} · {c?.nombre}
                            </span>
                          )
                        })}
                        {!k.competencias.length && <span className="text-[11px] text-slate-400">Sin competencia vinculada</span>}
                      </div>
                    </div>
                    <div role="radiogroup" aria-label={`Nivel en ${k.nombre}`} className="inline-flex shrink-0 rounded-lg bg-mist p-0.5">
                      {([1, 2, 3] as Level[]).map((l) => (
                        <button
                          key={l}
                          type="button"
                          role="radio"
                          aria-checked={crit[k.id].nivel === l}
                          onClick={() => setCrit((p) => ({ ...p, [k.id]: { ...p[k.id], nivel: l } }))}
                          className={`cursor-pointer rounded-md px-3 py-1.5 text-xs font-bold ${crit[k.id].nivel === l ? 'bg-navy text-white' : 'text-muted hover:text-ink'}`}
                        >
                          N{l}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    <input aria-label={`Evidencia observada en ${k.nombre}`} placeholder="Evidencia observada" className={`${inputCls} py-2 text-[13px]`} value={crit[k.id].evidencia} onChange={(e) => setCrit((p) => ({ ...p, [k.id]: { ...p[k.id], evidencia: e.target.value } }))} />
                    <input aria-label={`Comentario sobre ${k.nombre}`} placeholder="Comentario" className={`${inputCls} py-2 text-[13px]`} value={crit[k.id].comentario} onChange={(e) => setCrit((p) => ({ ...p, [k.id]: { ...p[k.id], comentario: e.target.value } }))} />
                  </div>
                </li>
              ))}
            </ol>
          </div>
          <div className="grid content-start gap-5">
            <section>
              <h3 className="mb-1 text-sm font-semibold">Nivel por competencia</h3>
              <p className="mb-3 text-xs text-muted">Propuesta: el nivel más bajo de los criterios vinculados. Ajústalo si procede.</p>
              <ul className="grid gap-2">
                {comps.map((c) => {
                  const prev = latestEval(data.evaluaciones, ent.coder_id, c.id, todayOf(data))
                  return (
                    <li key={c.id} className="rounded-lg bg-mist/60 px-3 py-2">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-sm font-medium">
                          <span className="font-mono text-xs text-muted">{c.codigo}</span> {c.nombre}
                        </span>
                        <select
                          aria-label={`Nivel de ${c.nombre}`}
                          className={`${inputCls} w-28 py-1 text-xs`}
                          value={over[c.id] === undefined ? 'auto' : String(over[c.id] ?? '')}
                          onChange={(e) => {
                            const v = e.target.value
                            const n = { ...over }
                            if (v === 'auto') delete n[c.id]
                            else n[c.id] = v ? (Number(v) as Level) : null
                            setOver(n)
                          }}
                        >
                          <option value="auto">Auto ({auto(c.id) ? `N${auto(c.id)}` : '—'})</option>
                          <option value="1">N1</option>
                          <option value="2">N2</option>
                          <option value="3">N3</option>
                          <option value="">No evaluar</option>
                        </select>
                      </div>
                      <p className="mt-1 text-[11px] text-muted">Actual publicado: {prev ? `N${prev.nivel} (${fmtDay(prev.fecha)})` : 'sin datos'}</p>
                    </li>
                  )
                })}
              </ul>
            </section>
            <Field label="Feedback para el coder" htmlFor="rv-fb" hint="Solo será visible para el coder cuando publiques la evaluación.">
              <textarea id="rv-fb" className={`${inputCls} min-h-28`} value={feedback} onChange={(e) => setFeedback(e.target.value)} />
            </Field>
            {revs.length > 0 && (
              <section>
                <h3 className="mb-2 text-sm font-semibold">Historial de revisiones</h3>
                <ol className="grid gap-1.5 text-xs">
                  {revs.map((r) => (
                    <li key={r.id} className="flex items-center justify-between gap-2 rounded-lg border border-line px-3 py-2">
                      <span>
                        {fmtDay(r.publicada_en ?? r.creada_en)} · rúbrica v{r.rubrica_version}
                        {r.origen && r.origen !== 'demo' && <span className="ml-1 text-muted">({r.origen === 'heredado_v1' ? 'heredado' : 'sintético'})</span>}
                      </span>
                      <Status s={r.estado} />
                    </li>
                  ))}
                </ol>
              </section>
            )}
            {missing.length > 0 && <p className="text-xs text-amber-700">Para publicar, valora los {missing.length} criterios pendientes.</p>}
          </div>
        </div>
      )}
    </Modal>
  )
}
