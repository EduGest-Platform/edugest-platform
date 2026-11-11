/** Pure state transitions (mutate a draft). Used by the UI through `update()` and directly by tests. */
import { applyAbsenceRule, nextCode, nextSeq, todayOf, uid } from './domain'
import type { AsistEstado, Competencia, Criterio, GistarData, Level, Revision, Rubrica } from './types'

export interface ReviewInput {
  entregaId: string
  rubricaId: string
  criterios: Record<string, { nivel: Level | null; evidencia: string; comentario: string }>
  competencias: { competencia_id: string; nivel: Level | null }[]
  feedback: string
  publish: boolean
  evaluador?: string
}
export function applyReview(d: GistarData, inp: ReviewInput) {
  const today = todayOf(d)
  const e = d.entregas.find((x) => x.id === inp.entregaId)!
  const rubric = d.rubricas.find((r) => r.id === inp.rubricaId)!
  const evaluador = inp.evaluador ?? 'USR-DOC'
  let rev: Revision | undefined = d.revisiones.find((r) => r.entrega_id === e.id && r.estado === 'borrador')
  if (!rev) {
    rev = { id: uid('REV'), entrega_id: e.id, rubrica_id: rubric.id, rubrica_version: rubric.version, evaluador, estado: 'borrador', creada_en: today, publicada_en: null, criterios: [], competencias: [], feedback: '', origen: 'demo' }
    d.revisiones.push(rev)
  }
  rev.criterios = rubric.criterios.map((k) => ({ criterio_id: k.id, ...(inp.criterios[k.id] ?? { nivel: null, evidencia: '', comentario: '' }) }))
  rev.competencias = inp.competencias
  rev.feedback = inp.feedback
  // Replace this revision's evaluation rows; drafts are stored but never counted in metrics.
  d.evaluaciones = d.evaluaciones.filter((x) => x.revision_id !== rev!.id)
  let seq = nextSeq(d)
  for (const c of inp.competencias) {
    if (!c.nivel) continue
    const linked = rubric.criterios.filter((k) => k.competencias.includes(c.competencia_id))
    d.evaluaciones.push({
      id: uid('EVA'), coder_id: e.coder_id, competencia_id: c.competencia_id, tarea_id: e.tarea_id, entrega_id: e.id, revision_id: rev.id,
      rubrica_id: rubric.id, rubrica_version: rubric.version, evaluador, nivel: c.nivel,
      evidencia: linked.map((k) => inp.criterios[k.id]?.evidencia).filter(Boolean).join(' · ') || 'Entrega revisada con rúbrica',
      comentario: linked.map((k) => inp.criterios[k.id]?.comentario).filter(Boolean).join(' · '),
      estado: inp.publish ? 'publicada' : 'borrador', fecha: today, origen: 'demo', seq: seq++,
    })
  }
  if (inp.publish) {
    rev.estado = 'publicada'
    rev.publicada_en = today
    e.feedback_publicado = inp.feedback
    e.feedback_borrador = null
  } else e.feedback_borrador = inp.feedback
  return rev.id
}

export function applyAttendance(d: GistarData, sessionId: string, rows: Record<string, { estado: AsistEstado; comentario: string }>, actor = 'USR-DOC') {
  const at = todayOf(d)
  const changed: string[] = []
  for (const [coderId, v] of Object.entries(rows)) {
    const rec = d.asistencia.find((x) => x.evento_id === sessionId && x.coder_id === coderId)
    if (rec && rec.estado === v.estado && rec.comentario === v.comentario) continue
    if (!rec && v.estado === 'pendiente' && !v.comentario) continue
    const entry = { en: at, estado: v.estado, actor, comentario: v.comentario }
    if (rec) {
      rec.estado = v.estado
      rec.comentario = v.comentario
      rec.actualizado_en = at
      rec.historial.push(entry)
    } else d.asistencia.push({ id: `ATT-${sessionId}-${coderId}`, evento_id: sessionId, coder_id: coderId, estado: v.estado, comentario: v.comentario, actualizado_en: at, historial: [entry], origen: 'demo' })
    changed.push(coderId)
  }
  for (const c of changed) applyAbsenceRule(d, c)
  return changed
}

// ---------- Competency catalog ----------
export interface CompInput {
  nombre: string
  descripcion: string
  niveles: Record<'1' | '2' | '3', string>
}
export function competencyNameTaken(d: GistarData, programId: string, cohortId: string | null, nombre: string, exceptId?: string) {
  const n = nombre.trim().toLowerCase()
  return d.competencias.some(
    (c) => c.id !== exceptId && c.programa_id === programId && (c.cohorte_id === null || cohortId === null || c.cohorte_id === cohortId) && c.nombre.trim().toLowerCase() === n,
  )
}
export function addCompetency(d: GistarData, programId: string, cohortId: string | null, inp: CompInput): Competencia {
  if (!inp.nombre.trim()) throw new Error('El nombre es obligatorio')
  if (competencyNameTaken(d, programId, cohortId, inp.nombre)) throw new Error('Ya existe una competencia con ese nombre en este ámbito')
  const codigo = nextCode(d, programId)
  const prefix = programId.replace(/^P-/, '')
  let id = `${prefix}-${codigo.slice(1).padStart(2, '0')}`
  while (d.competencias.some((c) => c.id === id)) id = `${id}x`
  const orden = Math.max(0, ...d.competencias.filter((c) => c.programa_id === programId).map((c) => c.orden)) + 1
  const comp: Competencia = { id, programa_id: programId, cohorte_id: cohortId, codigo, nombre: inp.nombre.trim(), descripcion: inp.descripcion, niveles: inp.niveles, activo: true, orden }
  d.competencias.push(comp)
  return comp
}
export function editCompetency(d: GistarData, id: string, inp: CompInput) {
  const c = d.competencias.find((x) => x.id === id)!
  if (competencyNameTaken(d, c.programa_id, c.cohorte_id, inp.nombre, id)) throw new Error('Ya existe una competencia con ese nombre en este ámbito')
  Object.assign(c, { nombre: inp.nombre.trim(), descripcion: inp.descripcion, niveles: inp.niveles })
}
export function moveCompetency(d: GistarData, ids: string[], id: string, dir: -1 | 1) {
  const i = ids.indexOf(id)
  const j = i + dir
  if (i < 0 || j < 0 || j >= ids.length) return
  const order = [...ids]
  ;[order[i], order[j]] = [order[j], order[i]]
  order.forEach((cid, k) => (d.competencias.find((c) => c.id === cid)!.orden = k + 1))
}

// ---------- Rubrics ----------
export function validateRubric(criterios: Criterio[]): string | null {
  if (!criterios.length) return 'Añade al menos un criterio'
  if (criterios.some((k) => !k.nombre.trim())) return 'Todos los criterios necesitan nombre'
  const weighted = criterios.filter((k) => k.peso != null)
  if (weighted.length && weighted.length !== criterios.length) return 'Si usas pesos, todos los criterios deben tenerlo'
  if (weighted.length) {
    const sum = weighted.reduce((a, k) => a + (k.peso ?? 0), 0)
    if (Math.abs(sum - 100) > 0.001) return `Los pesos suman ${sum}%: deben sumar 100%`
  }
  return null
}
export function saveRubricDraft(
  d: GistarData,
  r: { id?: string; familia_id?: string; tarea_id: string; nombre: string; criterios: Criterio[]; basada_en: string | null },
) {
  const existing = r.id ? d.rubricas.find((x) => x.id === r.id) : undefined
  if (existing) {
    if (existing.estado !== 'borrador') throw new Error('Solo se pueden editar borradores; crea una nueva versión')
    Object.assign(existing, { nombre: r.nombre, criterios: r.criterios, tarea_id: r.tarea_id })
    return existing
  }
  const sameTask = d.rubricas.filter((x) => x.tarea_id === r.tarea_id)
  const familia_id = r.familia_id && sameTask.some((x) => x.familia_id === r.familia_id) ? r.familia_id : sameTask[0]?.familia_id ?? uid('RF')
  const version = Math.max(0, ...d.rubricas.filter((x) => x.familia_id === familia_id).map((x) => x.version)) + 1
  const rub: Rubrica = { id: uid('RUB'), familia_id, tarea_id: r.tarea_id, nombre: r.nombre, version, estado: 'borrador', criterios: r.criterios, creada_en: todayOf(d), publicada_en: null, basada_en: r.basada_en }
  d.rubricas.push(rub)
  return rub
}
export function publishRubric(d: GistarData, id: string) {
  const r = d.rubricas.find((x) => x.id === id)!
  const err = validateRubric(r.criterios)
  if (err) throw new Error(err)
  // Previous published version is archived but kept: published evaluations keep their reference.
  for (const o of d.rubricas) if (o.tarea_id === r.tarea_id && o.id !== id && o.estado === 'publicada') o.estado = 'archivada'
  r.estado = 'publicada'
  r.publicada_en = todayOf(d)
  d.tareas.find((t) => t.id === r.tarea_id)!.rubrica_id = id
}
export function archiveRubric(d: GistarData, id: string) {
  const r = d.rubricas.find((x) => x.id === id)!
  r.estado = 'archivada'
  const t = d.tareas.find((x) => x.id === r.tarea_id)
  if (t?.rubrica_id === id) t.rubrica_id = null
}
